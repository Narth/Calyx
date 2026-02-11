import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.calyx_guardian.guardian_assess_windows import load_policy, load_evidence, generate_findings


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def extract_ids(findings: list[dict]) -> set[str]:
    return {finding.get("id", "") for finding in findings if finding.get("id")}


def build_reason_map(findings: list[dict]) -> dict[str, str]:
    return {finding.get("id", ""): finding.get("confidence", "low") for finding in findings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze night watch findings")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--watch-evidence", required=True)
    parser.add_argument("--watch-findings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--correlation-id", required=True)
    args = parser.parse_args()

    baseline = load_json(Path(args.baseline))
    policy = load_policy()
    watch_evidence_path = Path(args.watch_evidence)
    outdir = watch_evidence_path.parent
    watch_records = load_evidence(outdir, watch_evidence_path)
    latest = generate_findings(watch_records, policy)
    write_json(Path(args.watch_findings), latest)

    baseline_ids = extract_ids(baseline)
    latest_ids = extract_ids(latest)

    status = "no_change"
    details = []
    additions = []
    removals = []

    baseline_confidence = build_reason_map(baseline)
    latest_confidence = build_reason_map(latest)
    baseline_has_integrity = any(f.get("category") == "integrity" for f in baseline)
    latest_has_integrity = any(f.get("category") == "integrity" for f in latest)

    if "integrity.collector_error" in latest_ids:
        status = "observation_degraded"
        details.append("collector error present in latest findings")
    if baseline_ids != latest_ids:
        status = "drift_detected"
        added = sorted(latest_ids - baseline_ids)
        removed = sorted(baseline_ids - latest_ids)
        for item in added:
            reason = "new_observation"
            if baseline_has_integrity and not latest_has_integrity:
                reason = "elevated_visibility"
            additions.append({"id": item, "added_due_to": reason})
        for item in removed:
            reason = "confirmed_state_change"
            if latest_has_integrity:
                reason = "visibility_loss"
            elif baseline_confidence.get(item) == "low":
                reason = "confidence_loss"
            removals.append({"id": item, "removed_due_to": reason})
        if added:
            details.append(f"added findings: {', '.join(added)}")
        if removed:
            details.append(f"removed findings: {', '.join(removed)}")

    payload = {
        "correlation_id": args.correlation_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "details": details,
        "added": additions,
        "removed": removals,
        "baseline_count": len(baseline_ids),
        "latest_count": len(latest_ids),
    }

    write_json(Path(args.out), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
