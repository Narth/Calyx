import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def render_brief(baseline: list[dict], latest: list[dict], delta: dict, manifest: dict | None, correlation_id: str) -> str:
    status = delta.get("status", "unknown")
    details = delta.get("details", [])
    added = delta.get("added", [])
    removed = delta.get("removed", [])
    blind_spots = []
    for finding in latest:
        if finding.get("category") == "integrity":
            blind_spots.append(finding.get("what_we_dont_know", ""))

    lines = [
        "# Calyx Guardian Night Watch Brief",
        "",
        f"Correlation ID: `{correlation_id}`",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        f"- Status: {status}",
        f"- Baseline findings: {len(baseline)}",
        f"- Latest findings: {len(latest)}",
    ]

    if details:
        lines.append("- Details:")
        for item in details:
            lines.append(f"  - {item}")

    if added:
        lines.append("- Added findings:")
        for item in added:
            lines.append(f"  - {item.get('id')}: {item.get('added_due_to')}")

    if removed:
        lines.append("- Removed findings:")
        for item in removed:
            lines.append(f"  - {item.get('id')}: {item.get('removed_due_to')}")

    lines.append("")
    lines.append("## Blind Spots")
    if blind_spots:
        for item in blind_spots:
            if item:
                lines.append(f"- {item}")
    else:
        lines.append("- None reported.")

    lines.append("")
    lines.append("## Evidence Hashes")
    if manifest:
        for key, meta in manifest.get("artifacts", {}).items():
            lines.append(f"- {key}: {meta.get('sha256', '')}")
    else:
        lines.append("- Manifest not available")

    lines.append("")
    lines.append("## Human-only Recommendations")
    lines.append("- Review if drift_detected or observation_degraded is reported.")
    lines.append("- No remediation actions are performed in Night Watch mode.")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render night watch brief")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--latest", required=True)
    parser.add_argument("--delta", required=True)
    parser.add_argument("--manifest", required=False)
    parser.add_argument("--out", required=True)
    parser.add_argument("--correlation-id", required=True)
    args = parser.parse_args()

    baseline = load_json(Path(args.baseline))
    latest = load_json(Path(args.latest))
    delta = load_json(Path(args.delta))
    manifest = load_json(Path(args.manifest)) if args.manifest else None

    brief = render_brief(baseline, latest, delta, manifest, args.correlation_id)
    Path(args.out).write_text(brief, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
