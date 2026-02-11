import argparse
import json
import sys
from pathlib import Path

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SECTION_ORDER = [
    "Executive Summary",
    "Patch & Update Posture",
    "Security Baseline (Defender + Firewall)",
    "Storage & Disk Health",
    "Backup & Continuity Signals",
    "Observed Unknowns / Blind Spots",
    "Next Steps"
]

CATEGORY_TO_SECTION = {
    "patching": "Patch & Update Posture",
    "defender": "Security Baseline (Defender + Firewall)",
    "firewall": "Security Baseline (Defender + Firewall)",
    "disk": "Storage & Disk Health",
    "backup": "Backup & Continuity Signals",
    "services": "Security Baseline (Defender + Firewall)",
    "integrity": "Observed Unknowns / Blind Spots"
}


def load_findings(outdir: Path):
    findings_path = outdir / "findings.json"
    if not findings_path.exists():
        raise FileNotFoundError(f"Missing findings file: {findings_path}")
    return json.loads(findings_path.read_text(encoding="utf-8"))


def sort_findings(findings):
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["title"]))


def format_finding(finding):
    title = finding["title"]
    severity = finding["severity"]
    confidence = finding["confidence"]
    confidence_score = finding.get("confidence_score")
    added_due_to = finding.get("added_due_to")
    impact = finding.get("do_nothing_impact", "")
    confidence_bits = f"confidence: {confidence}"
    if confidence_score is not None:
        confidence_bits += f" ({confidence_score:.2f})"
    if added_due_to:
        confidence_bits += f", added: {added_due_to}"
    line = f"- **{title}** (severity: {severity}, {confidence_bits})"
    if impact:
        line += f" — {impact}"
    return line


def build_report(findings):
    ordered_findings = sort_findings(findings)
    sections = {name: [] for name in SECTION_ORDER}

    top_risks = ordered_findings[:5]
    sections["Executive Summary"].extend(format_finding(f) for f in top_risks)

    for finding in ordered_findings:
        section = CATEGORY_TO_SECTION.get(finding["category"], "Observed Unknowns / Blind Spots")
        if section == "Executive Summary":
            continue
        sections[section].append(format_finding(finding))

    unknowns = []
    for finding in ordered_findings:
        if finding["confidence"] == "low" or finding["category"] == "integrity":
            unknowns.append(f"- {finding['what_we_dont_know']}")
    sections["Observed Unknowns / Blind Spots"].extend(unknowns)

    next_steps = []
    for finding in ordered_findings:
        recommendation = finding.get("recommendation")
        if recommendation:
            next_steps.append(f"- {recommendation}")
    next_steps.append("- Consider Phase 1 local Guardian for scheduled, read-only checks if ongoing oversight is desired.")
    sections["Next Steps"] = list(dict.fromkeys(next_steps))

    lines = ["# Calyx Guardian Phase 0 Report", "", "Local-only, read-only assessment. No network calls were made.", ""]
    for section in SECTION_ORDER:
        lines.append(f"## {section}")
        entries = sections.get(section, [])
        if not entries:
            lines.append("- No findings in this section.")
        else:
            lines.extend(entries)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Render Calyx Guardian Phase 0 report")
    parser.add_argument("--outdir", default="logs/calyx_guardian")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("This tool is intended to run on Windows.", file=sys.stderr)
        return 1

    outdir = Path(args.outdir)
    findings = load_findings(outdir)
    report = build_report(findings)

    report_path = outdir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
