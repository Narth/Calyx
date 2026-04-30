#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from calyx.governance.runtime_topology import write_runtime_topology_artifacts


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit Station Calyx runtime topology snapshot and receipt.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--emitted-at", default="")
    parser.add_argument("--force-stale", action="store_true")
    parser.add_argument("--stale-reason", default="")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    emitted_at = _parse_iso(args.emitted_at)
    try:
        result = write_runtime_topology_artifacts(
            repo_root=repo_root,
            emitted_at_utc=emitted_at,
            force_stale=args.force_stale,
            stale_reason=args.stale_reason,
        )
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as exc:  # pragma: no cover - fail-soft surface for ops wiring
        failure = {
            "snapshot_path": str(repo_root / "runtime" / "runtime_topology_snapshot.json"),
            "receipt_path": "",
            "state_summary": {
                "runtime_topology_ts": args.emitted_at or "",
                "runtime_topology_truth_state": "stale" if args.force_stale else "unknown",
                "runtime_topology_risk": "RISK",
                "runtime_topology_active_services": "none",
                "runtime_topology_authority_summary": "unknown(1)",
                "runtime_topology_duplicates": "none",
                "runtime_topology_authority_ambiguous": "runtime_topology_snapshot_error",
                "runtime_topology_flagged_services": "runtime_topology_snapshot_error",
            },
            "authority_status_vocabulary": [
                "canonical core",
                "canonical support",
                "quarantined noncanonical",
                "deprecated",
                "historical",
                "unknown",
            ],
            "authority_boundary_note": "Runtime topology is an observed truth surface, not sole liveness authority.",
            "highest_risk_level": "RISK",
            "classification_status": "partial",
            "identity_disclosure_status": "partial",
            "flagged_services": ["runtime_topology_snapshot_error"],
            "duplicate_services": [],
            "ambiguous_services": ["runtime_topology_snapshot_error"],
            "named_runtime_count": 0,
            "uncertain_runtime_count": 0,
            "unknown_runtime_count": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(failure, separators=(",", ":")))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
