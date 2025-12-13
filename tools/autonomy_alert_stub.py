#!/usr/bin/env python3
"""
Alert stub for Phase 1: reads the last 20 runs from logs/agent_metrics.csv and
prints WARN lines when success rate or TES deltas fall outside guardrails.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"


def _read_recent(limit: int = 20) -> List[Dict[str, str]]:
    if not METRICS_CSV.exists():
        return []
    with METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    return rows[-limit:]


def _safe_float(value: str | None) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def main() -> None:
    rows = _read_recent()
    if not rows:
        print("WARN no metrics rows available")
        return
    successes = sum(1 for r in rows if (r.get("status") or "").lower() == "done")
    success_rate = successes / len(rows) * 100.0
    tes_values = [_safe_float(r.get("tes")) for r in rows if r.get("tes")]
    if len(tes_values) >= 2:
        tes_delta = tes_values[-1] - tes_values[-2]
    else:
        tes_delta = 0.0
    if success_rate < 98.0:
        print(f"WARN success rate last {len(rows)} runs = {success_rate:.2f}% (<98.0)")
    else:
        print(f"OK   success rate last {len(rows)} runs = {success_rate:.2f}%")
    if tes_delta < -3.0:
        print(f"WARN TES drop detected: Δ {tes_delta:.2f}")
    else:
        print(f"OK   TES delta = {tes_delta:.2f}")


if __name__ == "__main__":
    main()
