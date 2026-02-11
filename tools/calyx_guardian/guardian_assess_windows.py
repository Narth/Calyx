import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
CONFIDENCE_SCORE = {"low": 0.3, "medium": 0.6, "high": 0.85}


def load_policy() -> dict:
    policy_path = Path(__file__).resolve().parent / "policies" / "guardian_policy_windows_phase0.json"
    return json.loads(policy_path.read_text(encoding="utf-8"))


def parse_summary(value: str):
    if not value:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_evidence(outdir: Path, evidence_path: Path | None = None):
    evidence_path = evidence_path or (outdir / "evidence.jsonl")
    if not evidence_path.exists():
        raise FileNotFoundError(f"Missing evidence file: {evidence_path}")
    records = []
    with evidence_path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith("\ufeff"):
                line = line.lstrip("\ufeff")
            record = json.loads(line)
            record["parsed_summary"] = parse_summary(record.get("result_summary", ""))
            records.append(record)
    return records


def collector_error_finding(message: str, evidence_path: Path):
    return [
        {
            "id": "integrity.collector_error",
            "title": "Evidence parsing failed",
            "category": "integrity",
            "severity": "high",
            "confidence": "high",
            "evidence_refs": [],
            "what_we_know": f"{message} (path: {evidence_path}).",
            "what_we_dont_know": "Evidence records could not be parsed; Phase 0 checks are unavailable.",
            "recommendation": "Re-run the PowerShell collector and ensure evidence.jsonl is readable.",
            "do_nothing_impact": "Assessment results are incomplete until evidence parsing succeeds."
        }
    ]


def evidence_by_source(records):
    grouped = {}
    for record in records:
        grouped.setdefault(record.get("source", ""), []).append(record)
    return grouped


def add_finding(findings, **kwargs):
    confidence = kwargs.get("confidence", "low")
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    if confidence == "low":
        kwargs["recommendation"] = None
    kwargs.setdefault("confidence_score", CONFIDENCE_SCORE.get(confidence, 0.3))
    kwargs.setdefault("added_due_to", "new_observation")
    findings.append(kwargs)


def iso_to_datetime(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def generate_findings(records, policy):
    grouped = evidence_by_source(records)
    findings = []

    hotfix_records = grouped.get("powershell:Get-HotFix", [])
    if hotfix_records:
        hotfix_summary = hotfix_records[-1]["parsed_summary"]
        count = hotfix_summary.get("count", 0) if isinstance(hotfix_summary, dict) else 0
        latest_installed = iso_to_datetime(hotfix_summary.get("latest_installed_on", "")) if isinstance(hotfix_summary, dict) else None
        if count == 0:
            add_finding(
                findings,
                id="patching.no_hotfixes",
                title="No recent hotfixes detected in sample",
                category="patching",
                severity="high",
                confidence="medium",
                evidence_refs=[hotfix_records[-1]["raw_hash"]],
                what_we_know="No hotfix entries were returned in the sampled list.",
                what_we_dont_know="Full Windows Update history was not inspected.",
                recommendation="Run Windows Update and confirm recent patches are installed.",
                do_nothing_impact="Known vulnerabilities may remain unpatched."
            )
        elif latest_installed:
            stale_days = policy.get("patch_stale_days", 30)
            if latest_installed < datetime.now(timezone.utc) - timedelta(days=stale_days):
                add_finding(
                    findings,
                    id="patching.stale",
                    title="Hotfix sample appears stale",
                    category="patching",
                    severity="medium",
                    confidence="medium",
                    evidence_refs=[hotfix_records[-1]["raw_hash"]],
                    what_we_know=f"Latest sampled hotfix installed on {latest_installed.date().isoformat()}.",
                    what_we_dont_know="Full Windows Update history was not inspected.",
                    recommendation="Check Windows Update for pending security patches.",
                    do_nothing_impact="Patch delays can increase exposure to known issues."
                )

    update_event_records = grouped.get("powershell:WindowsUpdateClientEvents", [])
    if update_event_records:
        update_summary = update_event_records[-1]["parsed_summary"]
        if isinstance(update_summary, dict) and update_summary.get("count", 0) == 0:
            add_finding(
                findings,
                id="patching.no_update_events",
                title="Windows Update event log shows no recent entries",
                category="patching",
                severity="low",
                confidence="low",
                evidence_refs=[update_event_records[-1]["raw_hash"]],
                what_we_know="No update client events were returned in the sampled log window.",
                what_we_dont_know="This does not confirm update status; event log may be truncated.",
                recommendation=None,
                do_nothing_impact="Update activity may be unknown until verified manually."
            )

    defender_records = grouped.get("powershell:Get-MpComputerStatus", [])
    if defender_records:
        defender_summary = defender_records[-1]["parsed_summary"]
        if isinstance(defender_summary, dict):
            antivirus_enabled = defender_summary.get("AntivirusEnabled", True)
            realtime_enabled = defender_summary.get("RealTimeProtectionEnabled", True)
            if not antivirus_enabled or not realtime_enabled:
                add_finding(
                    findings,
                    id="defender.disabled",
                    title="Windows Defender protection appears disabled",
                    category="defender",
                    severity="high",
                    confidence="high",
                    evidence_refs=[defender_records[-1]["raw_hash"]],
                    what_we_know=f"AntivirusEnabled={antivirus_enabled}, RealTimeProtectionEnabled={realtime_enabled}.",
                    what_we_dont_know="Third-party AV status was not inspected.",
                    recommendation="Enable Defender real-time protection or confirm an alternative AV is active.",
                    do_nothing_impact="Reduced malware protection and delayed detection of threats."
                )
        else:
            add_finding(
                findings,
                id="defender.unknown",
                title="Defender status could not be parsed",
                category="defender",
                severity="low",
                confidence="low",
                evidence_refs=[defender_records[-1]["raw_hash"]],
                what_we_know="Defender status output was not parsed into structured data.",
                what_we_dont_know="Defender configuration and real-time status remain unverified.",
                recommendation=None,
                do_nothing_impact="Security baseline may be incomplete."
            )

    firewall_records = grouped.get("powershell:Get-NetFirewallProfile", [])
    if firewall_records:
        firewall_summary = firewall_records[-1]["parsed_summary"]
        if isinstance(firewall_summary, list):
            disabled = [p for p in firewall_summary if not p.get("Enabled", True)]
            if disabled:
                disabled_names = ", ".join(sorted(p.get("Name", "") for p in disabled))
                add_finding(
                    findings,
                    id="firewall.disabled",
                    title="One or more firewall profiles are disabled",
                    category="firewall",
                    severity="medium",
                    confidence="high",
                    evidence_refs=[firewall_records[-1]["raw_hash"]],
                    what_we_know=f"Disabled profiles: {disabled_names}.",
                    what_we_dont_know="Inbound/outbound rules were not inspected.",
                    recommendation="Enable Windows Firewall profiles unless intentionally managed elsewhere.",
                    do_nothing_impact="Reduced network protection and increased exposure to inbound threats."
                )

    bitlocker_records = grouped.get("powershell:Get-BitLockerVolume", [])
    if bitlocker_records:
        bitlocker_summary = bitlocker_records[-1]["parsed_summary"]
        if isinstance(bitlocker_summary, list) and bitlocker_summary:
            unprotected = [v for v in bitlocker_summary if str(v.get("ProtectionStatus", "")).lower() not in {"on", "1"}]
            if unprotected:
                mounts = ", ".join(sorted(v.get("MountPoint", "") for v in unprotected))
                add_finding(
                    findings,
                    id="disk.bitlocker_off",
                    title="BitLocker protection is not enabled on all volumes",
                    category="disk",
                    severity="medium",
                    confidence="medium",
                    evidence_refs=[bitlocker_records[-1]["raw_hash"]],
                    what_we_know=f"Unprotected volumes: {mounts}.",
                    what_we_dont_know="Removable media and TPM status were not evaluated.",
                    recommendation="Enable BitLocker on system and data volumes if required by policy.",
                    do_nothing_impact="Data at rest may be exposed if the device is lost or stolen."
                )

    drive_records = grouped.get("powershell:Get-PSDrive", [])
    if drive_records:
        drive_summary = drive_records[-1]["parsed_summary"]
        if isinstance(drive_summary, list):
            critical_threshold = policy.get("disk_free_pct_critical", 15)
            warn_threshold = policy.get("disk_free_pct_warn", 25)
            critical = [d for d in drive_summary if d.get("FreePct", 100) < critical_threshold]
            warn = [d for d in drive_summary if critical_threshold <= d.get("FreePct", 100) < warn_threshold]
            if critical or warn:
                impacted = critical if critical else warn
                severity = "high" if critical else "medium"
                drives_list = ", ".join(sorted(d.get("Name", "") for d in impacted))
                add_finding(
                    findings,
                    id="disk.low_space",
                    title="Low free disk space detected",
                    category="disk",
                    severity=severity,
                    confidence="high",
                    evidence_refs=[drive_records[-1]["raw_hash"]],
                    what_we_know=f"Low free space on drives: {drives_list}.",
                    what_we_dont_know="No file-level cleanup analysis was performed.",
                    recommendation="Free disk space or expand storage to maintain healthy margins.",
                    do_nothing_impact="Low disk space can cause update failures and stability issues."
                )

    physical_records = grouped.get("powershell:Get-PhysicalDisk", [])
    if physical_records:
        physical_summary = physical_records[-1]["parsed_summary"]
        if isinstance(physical_summary, list):
            unhealthy = [d for d in physical_summary if str(d.get("HealthStatus", "")).lower() not in {"healthy", "ok"}]
            if unhealthy:
                disks_list = ", ".join(sorted(d.get("FriendlyName", "") for d in unhealthy))
                add_finding(
                    findings,
                    id="disk.health_alert",
                    title="Physical disk health reports non-healthy status",
                    category="disk",
                    severity="high",
                    confidence="medium",
                    evidence_refs=[physical_records[-1]["raw_hash"]],
                    what_we_know=f"Disks with reported issues: {disks_list}.",
                    what_we_dont_know="SMART diagnostics were not collected.",
                    recommendation="Review disk health with vendor tooling and verify backups.",
                    do_nothing_impact="Disk degradation may lead to data loss or downtime."
                )

    file_history_records = grouped.get("powershell:FileHistory", [])
    onedrive_records = grouped.get("powershell:OneDrivePresence", [])
    if file_history_records or onedrive_records:
        file_history_summary = file_history_records[-1]["parsed_summary"] if file_history_records else {}
        onedrive_summary = onedrive_records[-1]["parsed_summary"] if onedrive_records else {}
        fh_configured = False
        od_present = False
        if isinstance(file_history_summary, dict):
            fh_configured = bool(file_history_summary.get("Configured"))
        if isinstance(onedrive_summary, dict):
            od_present = bool(onedrive_summary.get("Present"))
        if not fh_configured and not od_present:
            evidence_refs = []
            if file_history_records:
                evidence_refs.append(file_history_records[-1]["raw_hash"])
            if onedrive_records:
                evidence_refs.append(onedrive_records[-1]["raw_hash"])
            add_finding(
                findings,
                id="backup.signals_missing",
                title="Backup signals not detected",
                category="backup",
                severity="medium",
                confidence="low",
                evidence_refs=evidence_refs,
                what_we_know="File History not configured and OneDrive presence not detected.",
                what_we_dont_know="Third-party backup tools may be present but were not inspected.",
                recommendation=None,
                do_nothing_impact="Continuity status may be unknown without manual verification."
            )

    rdp_records = grouped.get("powershell:RDPEnabled", [])
    if rdp_records:
        rdp_summary = rdp_records[-1]["parsed_summary"]
        if isinstance(rdp_summary, dict) and rdp_summary.get("RdpEnabled") is True:
            add_finding(
                findings,
                id="services.rdp_enabled",
                title="RDP appears enabled",
                category="services",
                severity="medium",
                confidence="medium",
                evidence_refs=[rdp_records[-1]["raw_hash"]],
                what_we_know="Remote Desktop is enabled via registry flag.",
                what_we_dont_know="RDP exposure and network firewall rules were not verified.",
                recommendation="Confirm RDP access is restricted and monitored if required.",
                do_nothing_impact="Exposed RDP can increase remote access risk."
            )

    error_records = [r for r in records if r.get("severity_hint") == "error"]
    if error_records:
        sources = ", ".join(sorted({r.get("source", "") for r in error_records}))
        add_finding(
            findings,
            id="integrity.incomplete_checks",
            title="Some checks could not be completed",
            category="integrity",
            severity="low",
            confidence="medium",
            evidence_refs=[r.get("raw_hash", "") for r in error_records if r.get("raw_hash")],
            what_we_know=f"Checks failed for: {sources}.",
            what_we_dont_know="Results for those checks are unavailable without elevated access.",
            recommendation="Re-run Phase 0 with elevated privileges if policy permits.",
            do_nothing_impact="Assessment may miss risks tied to blocked checks."
        )

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["title"]))
    return findings


def main():
    parser = argparse.ArgumentParser(description="Calyx Guardian Phase 0 - Windows findings generator")
    parser.add_argument("--outdir", default="logs/calyx_guardian")
    parser.add_argument("--evidence", default=None)
    parser.add_argument("--findings", default=None)
    args = parser.parse_args()

    if sys.platform != "win32":
        print("This tool is intended to run on Windows.", file=sys.stderr)
        return 1

    outdir = Path(args.outdir)
    evidence_path = Path(args.evidence) if args.evidence else None
    policy = load_policy()
    default_evidence_path = evidence_path or (outdir / "evidence.jsonl")
    try:
        if not default_evidence_path.exists() or default_evidence_path.stat().st_size == 0:
            message = "Missing evidence.jsonl — run PowerShell collector first or check OutDir"
            print(message, file=sys.stderr)
            findings = collector_error_finding(message, default_evidence_path)
        else:
            records = load_evidence(outdir, default_evidence_path)
            if not records:
                message = "Evidence file is empty — run PowerShell collector first or check OutDir"
                print(message, file=sys.stderr)
                findings = collector_error_finding(message, default_evidence_path)
            else:
                findings = generate_findings(records, policy)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        message = f"Evidence parsing failed: {exc}"
        print(message, file=sys.stderr)
        findings = collector_error_finding(message, default_evidence_path)
    except FileNotFoundError as exc:
        message = "Missing evidence.jsonl — run PowerShell collector first or check OutDir"
        print(message, file=sys.stderr)
        findings = collector_error_finding(message, default_evidence_path)

    findings_path = Path(args.findings) if args.findings else (outdir / "findings.json")
    findings_path.write_text(json.dumps(findings, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
