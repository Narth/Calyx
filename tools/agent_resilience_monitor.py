#!/usr/bin/env python3
"""
Autonomous Resilience & Ethics Index (AREI) snapshot generator.

Reads recent agent metrics and emits resilience snapshots to
logs/agent_resilience.jsonl for downstream dashboards.

Environment overrides:
- CALYX_METRICS_CSV: alternate CSV path for synthetic or replay data
- CALYX_AREI_LOG: alternate output log path
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Deque, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = Path(os.environ.get("CALYX_METRICS_CSV", ROOT / "logs" / "agent_metrics.csv"))
AREI_LOG = Path(os.environ.get("CALYX_AREI_LOG", ROOT / "logs" / "agent_resilience.jsonl"))
DEFAULT_WINDOW = 50


@dataclass
class MetricRow:
    status: str
    duration_s: Optional[float]
    changed_files: Optional[float]
    compliance: Optional[float]
    coherence: Optional[float]
    ethics: Optional[float]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def parse_optional_float(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def normalize_linear(value: float, best: float, worst: float) -> float:
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    span = worst - best
    if span == 0:
        return 1.0
    return clamp(1.0 - ((value - best) / span))


def load_recent_metrics(limit: int) -> List[MetricRow]:
    if not METRICS_CSV.exists():
        return []

    buffer: Deque[dict] = deque(maxlen=limit)
    with METRICS_CSV.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            buffer.append(row)

    rows: List[MetricRow] = []
    for row in buffer:
        rows.append(
            MetricRow(
                status=row.get("status", "").strip() or "unknown",
                duration_s=parse_optional_float(row.get("duration_s", "")),
                changed_files=parse_optional_float(row.get("changed_files", "")),
                compliance=parse_optional_float(row.get("compliance", "")),
                coherence=parse_optional_float(row.get("coherence", "")),
                ethics=parse_optional_float(row.get("ethics", "")),
            )
        )
    return rows


def compute_integrity(rows: Iterable[MetricRow]) -> float:
    rows = list(rows)
    if not rows:
        return 1.0
    done = sum(1 for row in rows if row.status == "done")
    return round(done / len(rows), 3)


def compute_empathic_alignment(rows: Iterable[MetricRow]) -> float:
    ethics_values = [row.ethics for row in rows if row.ethics is not None]
    if ethics_values:
        return round(sum(ethics_values) / len(ethics_values), 3)

    compliance_values = [row.compliance for row in rows if row.compliance is not None]
    if compliance_values:
        return round(sum(compliance_values) / len(compliance_values), 3)

    return 1.0


def compute_sustainability(rows: Iterable[MetricRow]) -> float:
    duration_scores: List[float] = []
    footprint_scores: List[float] = []

    for row in rows:
        if row.duration_s is not None:
            duration_scores.append(normalize_linear(row.duration_s, best=90.0, worst=900.0))
        if row.changed_files is not None:
            footprint_scores.append(normalize_linear(row.changed_files, best=1.0, worst=10.0))

    if not duration_scores and not footprint_scores:
        return 1.0

    parts: List[float] = []
    if duration_scores:
        parts.append(sum(duration_scores) / len(duration_scores))
    if footprint_scores:
        parts.append(sum(footprint_scores) / len(footprint_scores))
    return round(sum(parts) / len(parts), 3)


def summarize_status(rows: Iterable[MetricRow]) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        counter[row.status] += 1
    return counter


def build_snapshot(rows: List[MetricRow]) -> Optional[dict]:
    if not rows:
        return None

    integrity = compute_integrity(rows)
    empathy = compute_empathic_alignment(rows)
    sustainability = compute_sustainability(rows)
    arei_score = round(100.0 * ((0.4 * integrity) + (0.35 * empathy) + (0.25 * sustainability)), 2)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "window": len(rows),
        "integrity_of_self": integrity,
        "empathic_alignment": empathy,
        "sustainability": sustainability,
        "arei": arei_score,
        "status_counts": summarize_status(rows),
    }


def append_snapshot(snapshot: dict, dry_run: bool) -> None:
    if dry_run:
        print(json.dumps(snapshot))
        return

    AREI_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AREI_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute an AREI snapshot from recent agent metrics.")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="Number of recent runs to sample.")
    parser.add_argument("--dry-run", action="store_true", help="Preview the snapshot without writing to disk.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_recent_metrics(args.window)
    snapshot = build_snapshot(rows)
    if snapshot is None:
        print("No agent metrics available; AREI snapshot skipped.")
        return
    append_snapshot(snapshot, args.dry_run)
    if args.dry_run:
        print(f"AREI snapshot preview (window={snapshot['window']}, score={snapshot['arei']}).")
    else:
        print(f"AREI snapshot recorded (window={snapshot['window']}, score={snapshot['arei']}).")


if __name__ == "__main__":
    main()
