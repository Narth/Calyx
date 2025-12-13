#!/usr/bin/env python3
"""
Generate a lightweight observability status report for Station Calyx.

Reads logs/agent_metrics.csv and emits aggregated reliability, TES, and latency
metrics to reports/autonomy_observability_status.md. This acts as the Phase 1
promotion artifact for the readiness-based rollout.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"
REPORT_PATH = ROOT / "reports" / "autonomy_observability_status.md"


def _read_metrics() -> List[Dict[str, str]]:
    if not METRICS_CSV.exists():
        return []
    with METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def _safe_float(value: str | None) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _percentile(values: List[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = ratio * (len(ordered) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(ordered) - 1)
    weight = idx - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _aggregate(rows: List[Dict[str, str]]) -> Dict[str, float]:
    successes = sum(1 for r in rows if (r.get("status") or "").lower() == "done")
    failures = len(rows) - successes
    durations = [_safe_float(r.get("duration_s")) for r in rows if r.get("duration_s")]
    tes_values = [_safe_float(r.get("tes")) for r in rows if r.get("tes")]
    recent = rows[-20:] if rows else []
    recent_successes = sum(1 for r in recent if (r.get("status") or "").lower() == "done")
    recent_tes = [_safe_float(r.get("tes")) for r in recent if r.get("tes")]
    last_tes = tes_values[-1] if tes_values else 0.0
    prev_tes = tes_values[-2] if len(tes_values) >= 2 else last_tes
    return {
        "runs_total": float(len(rows)),
        "success_total": float(successes),
        "failure_total": float(failures),
        "success_rate": (successes / len(rows) * 100.0) if rows else 0.0,
        "recent_success_rate": (recent_successes / len(recent) * 100.0) if recent else 0.0,
        "tes_average": (sum(tes_values) / len(tes_values)) if tes_values else 0.0,
        "tes_min": min(tes_values) if tes_values else 0.0,
        "tes_max": max(tes_values) if tes_values else 0.0,
        "tes_recent_average": (sum(recent_tes) / len(recent_tes)) if recent_tes else 0.0,
        "tes_last": last_tes,
        "tes_delta": last_tes - prev_tes if tes_values else 0.0,
        "duration_p50": _percentile(durations, 0.5),
        "duration_p95": _percentile(durations, 0.95),
    }


def write_report(stats: Dict[str, float]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    report = f"""# Autonomy Observability Status
**Generated:** {now}

## Reliability
- Total runs: {int(stats['runs_total'])}
- Successes: {int(stats['success_total'])}
- Failures: {int(stats['failure_total'])}
- Success rate (lifetime): {stats['success_rate']:.2f}%
- Success rate (last 20): {stats['recent_success_rate']:.2f}%

## Task Execution Score (TES)
- Latest TES: {stats['tes_last']:.2f}
- Delta TES vs previous run: {stats['tes_delta']:+.2f}
- TES average (lifetime): {stats['tes_average']:.2f}
- TES min / max: {stats['tes_min']:.2f} / {stats['tes_max']:.2f}
- TES average (last 20): {stats['tes_recent_average']:.2f}

## Latency
- Duration p50: {stats['duration_p50']:.2f}s
- Duration p95: {stats['duration_p95']:.2f}s

---
*Source: logs/agent_metrics.csv (entries {int(max(stats['runs_total'], 0))})*
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> None:
    rows = _read_metrics()
    stats = _aggregate(rows)
    write_report(stats)


if __name__ == "__main__":
    main()
