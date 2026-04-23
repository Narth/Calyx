from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from staging.work.runtime_capture_adapter.capture import capture_live_runtime_state
from staging.work.runtime_capture_adapter.models import CapturedPort, CapturedProcessRow, RuntimeCaptureInput


CORE_LISTENER_PORTS = {
    7777: "dev_harness",
    7778: "cbo_core",
    7780: "avatar_web",
    7781: "telemetry_gateway",
}
RUNTIME_TOPOLOGY_FRESHNESS_WINDOW_SEC = 120
TOPLOGY_SNAPSHOT_SCHEMA = "station.runtime_topology_snapshot.v2"

SERVICE_DISPLAY_NAMES = {
    "dev_harness": "Dev Harness",
    "cbo_core": "CBO Core",
    "avatar_web": "Avatar Web",
    "telemetry_gateway": "Telemetry Gateway",
    "station_health_loop": "Station health loop",
    "service_failure_watch": "Service failure watch",
    "navigator_triage_loop": "Navigator/Triage loop",
    "energy_churn_cp9_loop": "Energy churn CP9 loop",
    "cp6_cp7_loop": "CP6/CP7 loop",
    "bridge_overseer": "Bridge Overseer",
    "cli_avatar": "CLI Avatar",
    "discord_gateway": "Discord gateway",
}

IDENTITY_CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


@dataclass(frozen=True)
class ServiceDeclaration:
    service_name: str
    topology_kind: str
    multiplicity_posture: str
    allowed_instances: int
    match_tokens: tuple[str, ...]
    declared_ports: tuple[int, ...] = ()
    supervisor: bool = False


@dataclass(frozen=True)
class AuxiliaryDeclaration:
    family_name: str
    match_tokens: tuple[str, ...]
    category: str
    notes: str


@dataclass(frozen=True)
class IdentityCandidate:
    matched_identity: str
    identity_status: str
    identity_confidence: str
    identity_basis: tuple[str, ...]
    score: int
    authority_posture_hint: str | None = None


def build_service_declarations() -> dict[str, ServiceDeclaration]:
    return {
        "dev_harness": ServiceDeclaration(
            service_name="dev_harness",
            topology_kind="listener_wrapper_child_pair",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("cbo_hub.dev_harness.app:app",),
            declared_ports=(7777,),
        ),
        "cbo_core": ServiceDeclaration(
            service_name="cbo_core",
            topology_kind="listener_wrapper_child_pair",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("cbo_hub.cbo_core.app:app",),
            declared_ports=(7778,),
        ),
        "avatar_web": ServiceDeclaration(
            service_name="avatar_web",
            topology_kind="listener_wrapper_child_pair",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("cbo_hub.avatar_web.app:app",),
            declared_ports=(7780,),
        ),
        "telemetry_gateway": ServiceDeclaration(
            service_name="telemetry_gateway",
            topology_kind="listener_wrapper_child_pair",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("cbo_hub.telemetry_gateway.app:app",),
            declared_ports=(7781,),
        ),
        "station_health_loop": ServiceDeclaration(
            service_name="station_health_loop",
            topology_kind="single_process",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("station_health_loop.ps1",),
        ),
        "service_failure_watch": ServiceDeclaration(
            service_name="service_failure_watch",
            topology_kind="single_process",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("service_failure_watch.ps1",),
            supervisor=True,
        ),
        "navigator_triage_loop": ServiceDeclaration(
            service_name="navigator_triage_loop",
            topology_kind="single_process",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("navigator_triage_loop.ps1",),
        ),
        "energy_churn_cp9_loop": ServiceDeclaration(
            service_name="energy_churn_cp9_loop",
            topology_kind="single_process",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("energy_churn_cp9_loop.ps1",),
        ),
        "cp6_cp7_loop": ServiceDeclaration(
            service_name="cp6_cp7_loop",
            topology_kind="single_process",
            multiplicity_posture="singleton_expected",
            allowed_instances=1,
            match_tokens=("cp6_cp7_loop.ps1",),
        ),
        "bridge_overseer": ServiceDeclaration(
            service_name="bridge_overseer",
            topology_kind="wrapper_child_pair",
            multiplicity_posture="wrapper_child_expected",
            allowed_instances=1,
            match_tokens=("calyx.cbo.bridge_overseer",),
        ),
        "cli_avatar": ServiceDeclaration(
            service_name="cli_avatar",
            topology_kind="wrapper_child_pair",
            multiplicity_posture="wrapper_child_expected",
            allowed_instances=1,
            match_tokens=("cbo_hub.cli_avatar.main",),
        ),
        "discord_gateway": ServiceDeclaration(
            service_name="discord_gateway",
            topology_kind="wrapper_child_pair",
            multiplicity_posture="wrapper_child_expected",
            allowed_instances=1,
            match_tokens=("calyx.cbo.discord_gateway",),
        ),
    }


def build_auxiliary_declarations() -> dict[str, AuxiliaryDeclaration]:
    return {
        "station_patch_window": AuxiliaryDeclaration(
            family_name="station_patch_window",
            match_tokens=(
                "station_patch_sunrise.ps1",
                "calyx_sunset_sunrise.ps1",
                "sunrise_calyx.ps1",
                "sunset_calyx.ps1",
                "patch_readiness.ps1",
            ),
            category="governed_maintenance",
            notes="Governed patch and sunrise orchestration is station-adjacent but not a resident service family.",
        ),
        "runtime_truth_observer": AuxiliaryDeclaration(
            family_name="runtime_truth_observer",
            match_tokens=(
                "runtime_topology_snapshot.py",
                "update_state_checks.ps1",
            ),
            category="observation_auxiliary",
            notes="Runtime truth and topology observation helpers are expected during governed inspection and refresh.",
        ),
    }


def build_runtime_topology_snapshot(
    *,
    repo_root: Path,
    capture: RuntimeCaptureInput | None = None,
    emitted_at_utc: datetime | None = None,
    force_stale: bool = False,
    stale_reason: str = "",
) -> dict[str, Any]:
    now_utc = (emitted_at_utc or datetime.now(UTC)).astimezone(UTC)
    declarations = build_service_declarations()
    auxiliary_declarations = build_auxiliary_declarations()
    capture = capture or capture_live_runtime_state(
        repo_root=repo_root,
        capture_id=f"runtime_topology.live.{now_utc.strftime('%Y%m%dT%H%M%SZ').lower()}",
        corr_id=f"runtime_topology.live.{now_utc.strftime('%Y%m%dT%H%M%SZ').lower()}",
    )
    process_rows = [row for row in capture.process_rows if row.pid > 0]
    by_pid = {row.pid: row for row in process_rows}
    ports_by_pid = {row.pid: list(row.ports) for row in process_rows}

    direct_matches: dict[str, set[int]] = {name: set() for name in declarations}
    service_by_pid: dict[int, str] = {}
    auxiliary_by_pid: dict[int, str] = {}
    auxiliary_matches: dict[str, set[int]] = {name: set() for name in auxiliary_declarations}
    station_related_pids: set[int] = set()
    classification_gaps: list[dict[str, Any]] = []

    for row in process_rows:
        matched_service = _match_declared_service(row, declarations)
        if matched_service is not None:
            direct_matches[matched_service].add(row.pid)
            service_by_pid[row.pid] = matched_service
            station_related_pids.add(row.pid)
            continue
        auxiliary_family = _match_auxiliary_family(row, auxiliary_declarations)
        if auxiliary_family is not None:
            auxiliary_matches[auxiliary_family].add(row.pid)
            auxiliary_by_pid[row.pid] = auxiliary_family
            station_related_pids.add(row.pid)
            continue
        if _is_station_related_candidate(row, repo_root):
            station_related_pids.add(row.pid)

    # Fold in console hosts and child helpers when their parent is already attributable.
    unresolved_station_related: list[int] = []
    for row in process_rows:
        if row.pid in service_by_pid:
            continue
        if row.pid in auxiliary_by_pid:
            continue
        parent_service = service_by_pid.get(row.parent_pid) if row.parent_pid else None
        if parent_service and row.process_name.lower() in {"conhost.exe", "python.exe", "powershell.exe"}:
            direct_matches[parent_service].add(row.pid)
            service_by_pid[row.pid] = parent_service
            station_related_pids.add(row.pid)
        elif row.parent_pid and row.parent_pid in auxiliary_by_pid:
            family_name = auxiliary_by_pid[row.parent_pid]
            auxiliary_matches[family_name].add(row.pid)
            auxiliary_by_pid[row.pid] = family_name
            station_related_pids.add(row.pid)
        elif row.pid in station_related_pids:
            unresolved_station_related.append(row.pid)
            classification_gaps.append(
                {
                    "type": "undeclared_station_runtime",
                    "pid": row.pid,
                    "notes": "Station-related command or path was observed without a declared runtime match.",
                }
            )

    service_results: dict[str, Any] = {}
    highest_risk_rank = 0
    highest_risk_level = "LOW"
    flagged_services: list[str] = []
    duplicate_services: list[str] = []
    ambiguous_services: list[str] = []
    process_runtime_class: dict[int, str] = {}

    for service_name, declaration in declarations.items():
        matched = [by_pid[pid] for pid in sorted(direct_matches[service_name]) if pid in by_pid]
        instances = _build_service_instances(service_name, declaration, matched, by_pid)
        for instance in instances:
            for member in instance["members"]:
                process_runtime_class[member.pid] = _classify_runtime_member(
                    service_name=service_name,
                    declaration=declaration,
                    member=member,
                    authoritative_pid=instance["authoritative_pid"],
                    root_pid=instance["root_pid"],
                    ports_by_pid=ports_by_pid,
                    member_pids={item.pid for item in instance["members"]},
                )

        service_result = _build_service_result(
            service_name=service_name,
            declaration=declaration,
            instances=instances,
            process_runtime_class=process_runtime_class,
            ports_by_pid=ports_by_pid,
        )
        service_results[service_name] = service_result
        if service_result["risk_level"] != "LOW":
            flagged_services.append(service_name)
        if service_result["multiplicity_state"] in {"undeclared_multiplicity", "duplicate_concerning"}:
            duplicate_services.append(service_name)
        if service_result["topology_ambiguous"]:
            ambiguous_services.append(service_name)
        rank = _risk_rank(service_result["risk_level"])
        if rank > highest_risk_rank:
            highest_risk_rank = rank
            highest_risk_level = service_result["risk_level"]

    observed_runtime: list[dict[str, Any]] = []
    operator_runtime_table: list[dict[str, Any]] = []
    named_identity_counts: dict[str, int] = defaultdict(int)
    uncertain_runtime_pids: list[int] = []
    unknown_runtime_pids: list[int] = []
    named_external_identities: dict[str, int] = defaultdict(int)
    for row in sorted(process_rows, key=lambda item: item.pid):
        service_name = service_by_pid.get(row.pid)
        auxiliary_family = auxiliary_by_pid.get(row.pid)
        runtime_class = process_runtime_class.get(row.pid, "unknown_runtime")
        governance = _baseline_runtime_governance(
            row=row,
            service_name=service_name,
            auxiliary_family=auxiliary_family,
            runtime_class=runtime_class,
            service_results=service_results,
            station_related=row.pid in station_related_pids,
        )
        identity = _resolve_identity(
            row=row,
            service_name=service_name,
            auxiliary_family=auxiliary_family,
            runtime_class=governance["runtime_class"],
            governance=governance,
        )
        if governance["declared_status"] == "not_declared" and identity["identity_status"] == "named":
            governance["authority_posture"] = "external_non_authoritative"
        row_risk = governance["risk_level"]
        if identity["matched_identity"].startswith("OpenClaw"):
            row_risk = "RISK"
        if _risk_rank(row_risk) > highest_risk_rank:
            highest_risk_rank = _risk_rank(row_risk)
            highest_risk_level = row_risk

        port_records = [_port_record(port) for port in ports_by_pid.get(row.pid, [])]
        row_record = {
            "pid": row.pid,
            "parent_pid": row.parent_pid,
            "process_name": row.process_name,
            "executable_path": row.executable_path,
            "command_line": row.command_line,
            "start_time": _iso(row.started_at_utc),
            "start_ts": _iso(row.started_at_utc),
            "bound_ports": port_records,
            "ports": port_records,
            "service_family": governance["service_family"],
            "declared_service": service_name,
            "auxiliary_family": auxiliary_family,
            "runtime_class": governance["runtime_class"],
            "authority_posture": governance["authority_posture"],
            "declared_status": governance["declared_status"],
            "multiplicity_state": governance["multiplicity_state"],
            "risk_level": row_risk,
            "matched_identity": identity["matched_identity"],
            "identity_confidence": identity["identity_confidence"],
            "identity_basis": identity["identity_basis"],
            "identity_status": identity["identity_status"],
            "identity_candidates": identity["identity_candidates"],
            "station_related": row.pid in station_related_pids,
        }
        observed_runtime.append(row_record)
        operator_runtime_table.append(
            {
                "pid": row.pid,
                "process_name": row.process_name,
                "executable_path": row.executable_path,
                "command_line": row.command_line,
                "parent_pid": row.parent_pid,
                "ports": port_records,
                "matched_identity": identity["matched_identity"],
                "identity_status": identity["identity_status"],
                "identity_confidence": identity["identity_confidence"],
                "service_family": governance["service_family"],
                "authority_posture": governance["authority_posture"],
                "declared_status": governance["declared_status"],
                "risk_level": row_risk,
            }
        )
        if identity["identity_status"] == "named":
            named_identity_counts[identity["matched_identity"]] += 1
            if governance["declared_status"] == "not_declared":
                named_external_identities[identity["matched_identity"]] += 1
        elif identity["identity_status"] == "uncertain":
            uncertain_runtime_pids.append(row.pid)
        else:
            unknown_runtime_pids.append(row.pid)

    auxiliary_runtime_families = {}
    for family_name, declaration in auxiliary_declarations.items():
        member_ids = sorted(auxiliary_matches[family_name])
        if not member_ids:
            continue
        auxiliary_runtime_families[family_name] = {
            "category": declaration.category,
            "notes": declaration.notes,
            "observed_process_ids": member_ids,
            "observed_process_count": len(member_ids),
        }

    active_service_counts = {
        name: result["observed_instance_count"] for name, result in service_results.items() if result["observed_instance_count"] > 0
    }
    state_summary = {
        "runtime_topology_ts": _iso(now_utc),
        "runtime_topology_truth_state": "stale" if force_stale else "fresh",
        "runtime_topology_risk": highest_risk_level,
        "runtime_topology_active_services": ",".join(f"{name}({count})" for name, count in sorted(active_service_counts.items())) or "none",
        "runtime_topology_duplicates": ",".join(
            f"{name}({service_results[name]['observed_instance_count']})" for name in sorted(duplicate_services)
        )
        or "none",
        "runtime_topology_authority_ambiguous": ",".join(sorted(ambiguous_services)) or "none",
        "runtime_topology_flagged_services": ",".join(sorted(flagged_services)) or "none",
    }

    snapshot = {
        "schema": TOPLOGY_SNAPSHOT_SCHEMA,
        "wo_id": "WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1",
        "dependent_wo_ids": [
            "WO_RUNTIME_MULTIPLICITY_VISIBILITY_AND_RECONCILIATION_V1",
            "WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1",
        ],
        "capture_id": capture.capture_id,
        "corr_id": capture.corr_id,
        "emitted_ts_utc": _iso(now_utc),
        "truth_state": "stale" if force_stale else "fresh",
        "stale_reason": stale_reason if force_stale else "",
        "freshness_window_sec": RUNTIME_TOPOLOGY_FRESHNESS_WINDOW_SEC,
        "expires_ts_utc": _iso(now_utc if force_stale else now_utc + timedelta(seconds=RUNTIME_TOPOLOGY_FRESHNESS_WINDOW_SEC)),
        "authoritative_for_liveness": False,
        "capture_mode": capture.capture_mode,
        "classification_status": "partial" if classification_gaps else "complete",
        "identity_disclosure_status": "partial" if uncertain_runtime_pids or unknown_runtime_pids else "complete",
        "observed_runtime_count": len(observed_runtime),
        "declared_service_count": len(declarations),
        "auxiliary_runtime_family_count": len(auxiliary_runtime_families),
        "station_related_runtime_count": sum(1 for row in observed_runtime if row["station_related"]),
        "named_runtime_count": sum(named_identity_counts.values()),
        "uncertain_runtime_count": len(uncertain_runtime_pids),
        "unknown_runtime_count": len(unknown_runtime_pids),
        "highest_risk_level": highest_risk_level,
        "flagged_services": sorted(flagged_services),
        "duplicate_services": sorted(duplicate_services),
        "ambiguous_services": sorted(ambiguous_services),
        "auxiliary_runtime_families": auxiliary_runtime_families,
        "named_identities": dict(sorted(named_identity_counts.items())),
        "named_external_identities": dict(sorted(named_external_identities.items())),
        "uncertain_runtime_pids": sorted(uncertain_runtime_pids),
        "unknown_runtime_pids": sorted(unknown_runtime_pids),
        "classification_gaps": classification_gaps,
        "unresolved_station_related_pids": sorted(unresolved_station_related),
        "operator_runtime_table": operator_runtime_table,
        "observed_runtime": observed_runtime,
        "services": service_results,
        "state_summary": state_summary,
    }
    return snapshot


def write_runtime_topology_artifacts(
    *,
    repo_root: Path,
    capture: RuntimeCaptureInput | None = None,
    emitted_at_utc: datetime | None = None,
    force_stale: bool = False,
    stale_reason: str = "",
) -> dict[str, Any]:
    snapshot = build_runtime_topology_snapshot(
        repo_root=repo_root,
        capture=capture,
        emitted_at_utc=emitted_at_utc,
        force_stale=force_stale,
        stale_reason=stale_reason,
    )
    runtime_dir = repo_root / "runtime"
    receipt_dir = runtime_dir / "receipts" / "audit"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = runtime_dir / "runtime_topology_snapshot.json"
    stamp = datetime.fromisoformat(snapshot["emitted_ts_utc"].replace("Z", "+00:00")).strftime("%Y%m%d_%H%M%S")
    receipt_path = receipt_dir / f"runtime_topology_snapshot__{stamp}.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return {
        "snapshot_path": str(snapshot_path),
        "receipt_path": str(receipt_path),
        "state_summary": snapshot["state_summary"],
        "highest_risk_level": snapshot["highest_risk_level"],
        "classification_status": snapshot["classification_status"],
        "identity_disclosure_status": snapshot["identity_disclosure_status"],
        "flagged_services": snapshot["flagged_services"],
        "duplicate_services": snapshot["duplicate_services"],
        "ambiguous_services": snapshot["ambiguous_services"],
        "observed_runtime_count": snapshot["observed_runtime_count"],
        "named_runtime_count": snapshot["named_runtime_count"],
        "uncertain_runtime_count": snapshot["uncertain_runtime_count"],
        "unknown_runtime_count": snapshot["unknown_runtime_count"],
    }


def _service_display_name(service_name: str) -> str:
    return SERVICE_DISPLAY_NAMES.get(service_name, service_name.replace("_", " ").title())


def _service_identity_label(service_name: str, runtime_class: str, process_name: str) -> str:
    display_name = _service_display_name(service_name)
    process_lower = process_name.lower()
    if runtime_class == "launcher_wrapper":
        if process_lower == "powershell.exe":
            return f"{display_name} PowerShell wrapper"
        if process_lower == "python.exe":
            return f"{display_name} Python service wrapper"
        return f"{display_name} launcher wrapper"
    if runtime_class == "runtime_supervisor":
        return display_name
    if runtime_class == "active_network_child":
        return display_name
    if runtime_class == "inert_resident_wrapper":
        return f"Console host for {display_name}" if process_lower == "conhost.exe" else f"{display_name} resident wrapper"
    if process_lower == "powershell.exe" and service_name.endswith("_loop"):
        return f"PowerShell {display_name.lower()}"
    return display_name


def _auxiliary_identity_label(family_name: str, row: CapturedProcessRow) -> str:
    command = (row.command_line or "").lower()
    if family_name == "station_patch_window":
        if "station_patch_sunrise.ps1" in command:
            return "PowerShell patch sunrise script"
        if "calyx_sunset_sunrise.ps1" in command:
            return "PowerShell sunset/sunrise script"
        if "sunrise_calyx.ps1" in command:
            return "PowerShell sunrise script"
        if "sunset_calyx.ps1" in command:
            return "PowerShell sunset script"
        if "patch_readiness.ps1" in command:
            return "Patch readiness check"
        return "Station patch window helper"
    if family_name == "runtime_truth_observer":
        if "runtime_topology_snapshot.py" in command:
            return "Runtime topology snapshot observer"
        if "update_state_checks.ps1" in command:
            return "STATE refresh observer"
        return "Runtime truth observer"
    return family_name.replace("_", " ")


def _service_member_authority_posture(pid: int, service_result: dict[str, Any], runtime_class: str) -> str:
    authoritative = service_result.get("authoritative_runtime") or {}
    authoritative_pid = authoritative.get("pid")
    if pid == authoritative_pid:
        return "authoritative"
    if runtime_class == "runtime_supervisor":
        return "declared_supervisory_non_authoritative"
    if runtime_class == "launcher_wrapper":
        return "declared_wrapper_non_authoritative"
    if runtime_class == "inert_resident_wrapper":
        return "declared_support_non_authoritative"
    return "declared_non_authoritative"


def _auxiliary_authority_posture() -> str:
    return "auxiliary_non_authoritative"


def _baseline_runtime_governance(
    *,
    row: CapturedProcessRow,
    service_name: str | None,
    auxiliary_family: str | None,
    runtime_class: str,
    service_results: dict[str, Any],
    station_related: bool,
) -> dict[str, Any]:
    if service_name is not None:
        service_result = service_results[service_name]
        return {
            "service_family": service_name,
            "runtime_class": runtime_class,
            "authority_posture": _service_member_authority_posture(row.pid, service_result, runtime_class),
            "declared_status": "declared_service",
            "multiplicity_state": service_result["multiplicity_state"],
            "risk_level": service_result["risk_level"],
        }
    if auxiliary_family is not None:
        return {
            "service_family": auxiliary_family,
            "runtime_class": "auxiliary_runtime",
            "authority_posture": _auxiliary_authority_posture(),
            "declared_status": "declared_auxiliary",
            "multiplicity_state": "auxiliary_observed",
            "risk_level": "LOW",
        }
    if station_related:
        return {
            "service_family": "",
            "runtime_class": runtime_class,
            "authority_posture": "indeterminate",
            "declared_status": "undeclared_station_related",
            "multiplicity_state": "undeclared_multiplicity",
            "risk_level": "RISK",
        }
    return {
        "service_family": "",
        "runtime_class": runtime_class,
        "authority_posture": "external_non_authoritative",
        "declared_status": "not_declared",
        "multiplicity_state": "not_assessed",
        "risk_level": "LOW",
    }


def _named_identity_candidate(
    matched_identity: str,
    score: int,
    confidence: str,
    *basis: str,
    authority_posture_hint: str | None = None,
) -> IdentityCandidate:
    return IdentityCandidate(
        matched_identity=matched_identity,
        identity_status="named",
        identity_confidence=confidence,
        identity_basis=tuple(item for item in basis if item),
        score=score,
        authority_posture_hint=authority_posture_hint,
    )


def _generic_runtime_candidate(row: CapturedProcessRow) -> IdentityCandidate | None:
    process_lower = row.process_name.lower()
    exe_lower = (row.executable_path or "").lower()
    if process_lower == "python.exe" or exe_lower.endswith("\\python.exe"):
        return _named_identity_candidate("Python runtime", 20, "low", "process name", "executable path")
    if process_lower == "powershell.exe" or "powershell.exe" in exe_lower:
        return _named_identity_candidate("PowerShell runtime", 20, "low", "process name", "executable path")
    if process_lower == "node.exe" or exe_lower.endswith("\\node.exe"):
        return _named_identity_candidate("Node.js runtime", 20, "low", "process name", "executable path")
    if process_lower == "conhost.exe":
        return _named_identity_candidate("Console host", 10, "low", "process name")
    if process_lower == "cmd.exe":
        return _named_identity_candidate("Command shell", 10, "low", "process name")
    return None


def _collect_identity_candidates(
    *,
    row: CapturedProcessRow,
    service_name: str | None,
    auxiliary_family: str | None,
    runtime_class: str,
    governance: dict[str, Any],
) -> list[IdentityCandidate]:
    candidates: list[IdentityCandidate] = []
    command = (row.command_line or "").lower()
    executable = (row.executable_path or "").lower()
    process_lower = row.process_name.lower()
    ports = row.ports

    if service_name is not None:
        label = _service_identity_label(service_name, runtime_class, row.process_name)
        basis = ["launch provenance", f"declared service: {service_name}"]
        if row.command_line:
            basis.append("command line")
        if row.executable_path:
            basis.append("executable path")
        if any(port.local_port in CORE_LISTENER_PORTS for port in ports):
            basis.append("port ownership")
        candidates.append(
            _named_identity_candidate(
                label,
                100,
                "high",
                *basis,
                authority_posture_hint=governance["authority_posture"],
            )
        )

    if auxiliary_family is not None:
        label = _auxiliary_identity_label(auxiliary_family, row)
        basis = ["launch provenance", f"auxiliary family: {auxiliary_family}"]
        if row.command_line:
            basis.append("command line")
        candidates.append(
            _named_identity_candidate(
                label,
                95,
                "high",
                *basis,
                authority_posture_hint="auxiliary_non_authoritative",
            )
        )

    if "openclaw" in executable or "openclaw" in command:
        label = "OpenClaw node runtime" if process_lower == "node.exe" else "OpenClaw"
        candidates.append(
            _named_identity_candidate(
                label,
                92,
                "high",
                "command line" if "openclaw" in command else "",
                "executable path" if "openclaw" in executable else "",
                authority_posture_hint="external_non_authoritative",
            )
        )
    if any(port.local_port == 18789 and _is_listener_state(port.state) for port in ports):
        candidates.append(
            _named_identity_candidate(
                "OpenClaw gateway",
                88,
                "medium",
                "port ownership",
                authority_posture_hint="external_non_authoritative",
            )
        )

    if "ollama\\ollama.exe" in executable or process_lower == "ollama.exe":
        label = "Ollama"
        confidence = "high" if "serve" in command or any(port.local_port == 11434 for port in ports) else "medium"
        basis = ["executable path"]
        if "serve" in command:
            basis.append("command line")
        if any(port.local_port == 11434 for port in ports):
            basis.append("port ownership")
        candidates.append(
            _named_identity_candidate(
                label,
                90,
                confidence,
                *basis,
                authority_posture_hint="external_non_authoritative",
            )
        )
    if process_lower != "cmd.exe" and ("ollama app.exe" in executable or "ollama app.exe" in command or process_lower == "ollama app.exe"):
        candidates.append(
            _named_identity_candidate(
                "Ollama app",
                85,
                "high" if "ollama app.exe" in executable else "medium",
                "executable path" if "ollama app.exe" in executable else "",
                "command line" if "ollama app.exe" in command else "",
                authority_posture_hint="external_non_authoritative",
            )
        )
    if process_lower == "cmd.exe" and "ollama app.exe" in command:
        candidates.append(
            _named_identity_candidate(
                "Ollama app launcher",
                82,
                "medium",
                "command line",
                authority_posture_hint="external_non_authoritative",
            )
        )

    generic = _generic_runtime_candidate(row)
    if generic is not None:
        candidates.append(generic)
    return candidates


def _resolve_identity(
    *,
    row: CapturedProcessRow,
    service_name: str | None,
    auxiliary_family: str | None,
    runtime_class: str,
    governance: dict[str, Any],
) -> dict[str, Any]:
    candidates = _collect_identity_candidates(
        row=row,
        service_name=service_name,
        auxiliary_family=auxiliary_family,
        runtime_class=runtime_class,
        governance=governance,
    )
    if not candidates:
        status = "uncertain" if governance["declared_status"] == "undeclared_station_related" else "unknown"
        basis = ["station-related command or path"] if status == "uncertain" else []
        return {
            "matched_identity": status,
            "identity_status": status,
            "identity_confidence": "low",
            "identity_basis": basis,
            "identity_candidates": [],
        }

    candidates = sorted(
        candidates,
        key=lambda item: (item.score, IDENTITY_CONFIDENCE_RANK.get(item.identity_confidence, 0), item.matched_identity),
        reverse=True,
    )
    if governance["declared_status"] == "undeclared_station_related" and candidates[0].score < 80:
        return {
            "matched_identity": "uncertain",
            "identity_status": "uncertain",
            "identity_confidence": "low",
            "identity_basis": ["station-related command or path", "insufficient identity evidence"],
            "identity_candidates": [candidate.matched_identity for candidate in candidates[:2]],
        }
    top = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    if second is not None and top.matched_identity != second.matched_identity and abs(top.score - second.score) <= 12:
        combined_basis = list(dict.fromkeys(list(top.identity_basis) + list(second.identity_basis) + ["competing identity signals"]))
        return {
            "matched_identity": "uncertain",
            "identity_status": "uncertain",
            "identity_confidence": "medium" if top.score >= 80 else "low",
            "identity_basis": combined_basis,
            "identity_candidates": [top.matched_identity, second.matched_identity],
        }

    return {
        "matched_identity": top.matched_identity,
        "identity_status": top.identity_status,
        "identity_confidence": top.identity_confidence,
        "identity_basis": list(dict.fromkeys(top.identity_basis)),
        "identity_candidates": [top.matched_identity],
    }


def _build_service_instances(
    service_name: str,
    declaration: ServiceDeclaration,
    matched: list[CapturedProcessRow],
    by_pid: dict[int, CapturedProcessRow],
) -> list[dict[str, Any]]:
    if not matched:
        return []
    matched_by_pid = {row.pid: row for row in matched}
    descendant_map: dict[int, list[int]] = defaultdict(list)
    for row in matched:
        if row.parent_pid and row.parent_pid in matched_by_pid:
            descendant_map[row.parent_pid].append(row.pid)
    roots = [
        row for row in matched
        if row.process_name.lower() != "conhost.exe" and (row.parent_pid is None or row.parent_pid not in matched_by_pid)
    ]
    if not roots:
        roots = [row for row in matched if row.process_name.lower() != "conhost.exe"] or matched
    instances: list[dict[str, Any]] = []
    assigned: set[int] = set()
    for root in sorted(roots, key=lambda item: (item.started_at_utc or datetime.min.replace(tzinfo=UTC), item.pid)):
        if root.pid in assigned:
            continue
        member_ids = _collect_instance_members(root.pid, matched_by_pid, descendant_map)
        members = [matched_by_pid[pid] for pid in member_ids]
        assigned.update(member_ids)
        authoritative_pid = _choose_authoritative_pid(service_name, declaration, root.pid, members)
        instances.append(
            {
                "instance_id": f"{service_name}:{root.pid}",
                "root_pid": root.pid,
                "authoritative_pid": authoritative_pid,
                "members": members,
            }
        )
    leftovers = [row for row in matched if row.pid not in assigned]
    for row in leftovers:
        instances.append(
            {
                "instance_id": f"{service_name}:{row.pid}",
                "root_pid": row.pid,
                "authoritative_pid": _choose_authoritative_pid(service_name, declaration, row.pid, [row]),
                "members": [row],
            }
        )
    return instances


def _collect_instance_members(
    root_pid: int,
    matched_by_pid: dict[int, CapturedProcessRow],
    descendant_map: dict[int, list[int]],
) -> list[int]:
    stack = [root_pid]
    collected: set[int] = set()
    while stack:
        pid = stack.pop()
        if pid in collected:
            continue
        collected.add(pid)
        stack.extend(descendant_map.get(pid, []))
    return sorted(collected)


def _choose_authoritative_pid(
    service_name: str,
    declaration: ServiceDeclaration,
    root_pid: int,
    members: list[CapturedProcessRow],
) -> int | None:
    non_console = [row for row in members if row.process_name.lower() != "conhost.exe"]
    listener_owner = next(
        (
            row.pid
            for row in non_console
            if any(port.local_port in declaration.declared_ports and _is_listener_state(port.state) for port in row.ports)
        ),
        None,
    )
    if listener_owner is not None:
        return listener_owner
    if declaration.supervisor:
        return root_pid
    if declaration.topology_kind == "wrapper_child_pair":
        child = next((row.pid for row in non_console if row.parent_pid == root_pid and row.pid != root_pid), None)
        return child if child is not None else root_pid
    if declaration.topology_kind == "listener_wrapper_child_pair":
        child = next((row.pid for row in non_console if row.parent_pid == root_pid and row.pid != root_pid), None)
        return child if child is not None else root_pid
    return next((row.pid for row in non_console), root_pid)


def _classify_runtime_member(
    *,
    service_name: str,
    declaration: ServiceDeclaration,
    member: CapturedProcessRow,
    authoritative_pid: int | None,
    root_pid: int,
    ports_by_pid: dict[int, list[CapturedPort]],
    member_pids: set[int],
) -> str:
    if member.process_name.lower() == "conhost.exe":
        return "inert_resident_wrapper"
    ports = ports_by_pid.get(member.pid, [])
    if declaration.supervisor and member.pid == authoritative_pid:
        return "runtime_supervisor"
    if authoritative_pid is not None and member.pid == authoritative_pid:
        if any(_is_listener_state(port.state) for port in ports):
            return "effective_service_runtime"
        if any(port.remote_port for port in ports):
            return "active_network_child"
        return "effective_service_runtime"
    if member.pid == root_pid and declaration.topology_kind in {"wrapper_child_pair", "listener_wrapper_child_pair"}:
        return "launcher_wrapper"
    if member.parent_pid in member_pids:
        if any(port.remote_port for port in ports):
            return "active_network_child"
        return "active_network_child" if service_name == "discord_gateway" else "effective_service_runtime"
    return "unknown_runtime"


def _build_service_result(
    *,
    service_name: str,
    declaration: ServiceDeclaration,
    instances: list[dict[str, Any]],
    process_runtime_class: dict[int, str],
    ports_by_pid: dict[int, list[CapturedPort]],
) -> dict[str, Any]:
    instance_records: list[dict[str, Any]] = []
    authoritative_candidates: list[int] = []
    listener_authorities: list[int] = []
    anomaly_flags: list[str] = []
    non_console_member_counts: list[int] = []
    for instance in instances:
        authoritative_pid = instance["authoritative_pid"]
        authoritative_candidates.append(authoritative_pid) if authoritative_pid is not None else None
        if authoritative_pid is not None and any(
            _is_listener_state(port.state) for port in ports_by_pid.get(authoritative_pid, [])
        ):
            listener_authorities.append(authoritative_pid)
        members = []
        non_console_count = 0
        for member in sorted(instance["members"], key=lambda row: row.pid):
            runtime_class = process_runtime_class.get(member.pid, "unknown_runtime")
            if member.process_name.lower() != "conhost.exe":
                non_console_count += 1
            members.append(
                {
                    "pid": member.pid,
                    "parent_pid": member.parent_pid,
                    "process_name": member.process_name,
                    "runtime_class": runtime_class,
                    "command_line": member.command_line,
                    "start_ts": _iso(member.started_at_utc),
                }
            )
        non_console_member_counts.append(non_console_count)
        instance_records.append(
            {
                "instance_id": instance["instance_id"],
                "root_pid": instance["root_pid"],
                "authoritative_pid": authoritative_pid,
                "member_count": len(instance["members"]),
                "members": members,
            }
        )

    observed_count = len(instances)
    topology_ambiguous = False
    risk_level = "LOW"
    multiplicity_state = "singleton_expected"
    if observed_count == 0:
        risk_level = "ELEVATED"
        anomaly_flags.append("not_observed")
        authoritative_runtime = None
    else:
        authoritative_unique = sorted({pid for pid in authoritative_candidates if pid is not None})
        if len(authoritative_unique) == 0:
            topology_ambiguous = True
            risk_level = "RISK"
            multiplicity_state = "duplicate_concerning"
            anomaly_flags.append("missing_authoritative_runtime")
        elif len(authoritative_unique) > 1:
            topology_ambiguous = True
            risk_level = "CRITICAL"
            multiplicity_state = "duplicate_concerning"
            anomaly_flags.append("multiple_authoritative_candidates")
        elif len(listener_authorities) > 1:
            topology_ambiguous = True
            risk_level = "CRITICAL"
            multiplicity_state = "duplicate_concerning"
            anomaly_flags.append("duplicate_listener_conflict")
        elif declaration.topology_kind == "wrapper_child_pair" and observed_count == 1 and max(non_console_member_counts, default=0) >= 2:
            multiplicity_state = "duplicate_runtime_pair_non_listener"
            risk_level = "LOW"
        elif declaration.multiplicity_posture == "bounded_multiplicity_expected":
            multiplicity_state = "bounded_multiplicity_expected"
            risk_level = "LOW" if observed_count < declaration.allowed_instances else "ELEVATED"
        elif observed_count > declaration.allowed_instances:
            multiplicity_state = "undeclared_multiplicity"
            risk_level = "RISK"
            anomaly_flags.append("undeclared_multiplicity")
        else:
            multiplicity_state = "singleton_expected"
            risk_level = "LOW"
        authoritative_runtime = _authoritative_record(authoritative_unique[0], process_runtime_class) if len(authoritative_unique) == 1 else None

        if declaration.topology_kind in {"wrapper_child_pair", "listener_wrapper_child_pair"} and any(
            count < 2 for count in non_console_member_counts
        ):
            anomaly_flags.append("expected_wrapper_child_pair_incomplete")
            if risk_level == "LOW":
                risk_level = "ELEVATED"
        if any(member["runtime_class"] == "unknown_runtime" for instance in instance_records for member in instance["members"]):
            anomaly_flags.append("partial_runtime_classification")
            if risk_level == "LOW":
                risk_level = "ELEVATED"

    return {
        "declared_multiplicity_posture": declaration.multiplicity_posture,
        "declared_topology_kind": declaration.topology_kind,
        "declared_ports": list(declaration.declared_ports),
        "observed_instance_count": observed_count,
        "observed_instances": instance_records,
        "authoritative_runtime": authoritative_runtime,
        "multiplicity_state": multiplicity_state,
        "risk_level": risk_level,
        "topology_ambiguous": topology_ambiguous,
        "anomaly_flags": sorted(set(anomaly_flags)),
    }


def _authoritative_record(pid: int, process_runtime_class: dict[int, str]) -> dict[str, Any]:
    return {"pid": pid, "runtime_class": process_runtime_class.get(pid, "unknown_runtime")}


def _match_declared_service(
    row: CapturedProcessRow,
    declarations: dict[str, ServiceDeclaration],
) -> str | None:
    command = (row.command_line or "").lower()
    for port in row.ports:
        if port.local_port in CORE_LISTENER_PORTS and _is_listener_state(port.state):
            return CORE_LISTENER_PORTS[port.local_port]
    for name, declaration in declarations.items():
        if any(token.lower() in command for token in declaration.match_tokens):
            return name
    return None


def _match_auxiliary_family(
    row: CapturedProcessRow,
    declarations: dict[str, AuxiliaryDeclaration],
) -> str | None:
    command = (row.command_line or "").lower()
    for name, declaration in declarations.items():
        if any(token.lower() in command for token in declaration.match_tokens):
            return name
    return None


def _is_station_related_candidate(row: CapturedProcessRow, repo_root: Path) -> bool:
    text = " ".join(filter(None, [row.executable_path, row.command_line])).lower()
    repo_token = str(repo_root).lower()
    return any(
        token in text
        for token in (
            repo_token,
            "c:\\calyx_terminal",
            "cbo_hub.",
            "calyx.cbo.",
            "station_health_loop.ps1",
            "navigator_triage_loop.ps1",
            "energy_churn_cp9_loop.ps1",
            "cp6_cp7_loop.ps1",
            "service_failure_watch.ps1",
        )
    )


def _port_record(port: CapturedPort) -> dict[str, Any]:
    return {
        "local_address": port.local_address,
        "local_port": port.local_port,
        "remote_address": port.remote_address,
        "remote_port": port.remote_port,
        "state": port.state,
    }


def _is_listener_state(state: str | None) -> bool:
    if state is None:
        return False
    return str(state).upper() in {"LISTEN", "LISTENING", "2"}


def _risk_rank(level: str) -> int:
    return {"LOW": 1, "ELEVATED": 2, "RISK": 3, "CRITICAL": 4}.get(level, 0)


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
