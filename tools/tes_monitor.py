#!/usr/bin/env python3
"""
TES Monitor: watches logs/agent_metrics.csv and flags potential resource draw.

Heuristics:
- Long duration (>300s)
- High model compute (LLM time >20s or >5 calls), parsed from run_dir/audit.json
- Frequent runs (>1 every 3 minutes sustained)
- High autonomy (apply_tests) noted

Usage:
  python tools/tes_monitor.py --interval 10 --tail 5
  python tools/tes_monitor.py --once --tail 5
"""
from __future__ import annotations
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "logs" / "agent_metrics.csv"
OUT_DIR = ROOT / "outgoing"

DURATION_HIGH = 300.0
LLM_TIME_HIGH = 20.0
LLM_CALLS_HIGH = 5
FREQ_WINDOW = 5  # how many recent rows to consider for frequency
MIN_SPACING_SEC = 180.0  # 3 minutes target


@dataclass
class Row:
    iso_ts: str
    ts: float
    tes: float
    stability: float
    velocity: float
    footprint: float
    duration_s: float
    status: str
    applied: bool
    changed_files: int
    run_tests: bool
    autonomy_mode: str
    model_id: str
    run_dir: str


def _parse_ts(s: str) -> float:
    # datetime.fromisoformat handles timezone offsets
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return time.time()


def _read_rows() -> List[Row]:
    rows: List[Row] = []
    if not CSV_PATH.exists():
        return rows
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append(
                    Row(
                        iso_ts=r.get("iso_ts", ""),
                        ts=_parse_ts(r.get("iso_ts", "")),
                        tes=float(r.get("tes", "0")),
                        stability=float(r.get("stability", "0")),
                        velocity=float(r.get("velocity", "0")),
                        footprint=float(r.get("footprint", "0")),
                        duration_s=float(r.get("duration_s", "0")),
                        status=r.get("status", ""),
                        applied=bool(int(r.get("applied", "0"))),
                        changed_files=int(r.get("changed_files", "0")),
                        run_tests=bool(int(r.get("run_tests", "0"))),
                        autonomy_mode=r.get("autonomy_mode", ""),
                        model_id=r.get("model_id", ""),
                        run_dir=r.get("run_dir", ""),
                    )
                )
            except Exception:
                continue
    return rows


def _audit_llm_stats(run_dir_rel: str) -> tuple[float, int]:
    audit_path = (ROOT / run_dir_rel) / "audit.json"
    try:
        data = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception:
        return (0.0, 0)
    calls = data.get("llm_calls", []) if isinstance(data, dict) else []
    total = 0.0
    for c in calls:
        try:
            total += float(c.get("duration_s", 0.0))
        except Exception:
            pass
    return (total, len(calls))


def _print_summary(r: Row) -> None:
    print(f"TES {r.tes:.1f} | status={r.status} mode={r.autonomy_mode} dur={r.duration_s:.1f}s files={r.changed_files} tests={int(r.run_tests)} -> {r.run_dir}")


def _warn_on_resource_draw(r: Row) -> None:
    warned = False
    if r.duration_s > DURATION_HIGH:
        print(f"WARN: Long duration {r.duration_s:.1f}s (>{DURATION_HIGH}s)")
        warned = True
    llm_time, llm_calls = _audit_llm_stats(r.run_dir)
    if llm_time > LLM_TIME_HIGH or llm_calls > LLM_CALLS_HIGH:
        print(f"WARN: Model compute high: llm_time={llm_time:.1f}s calls={llm_calls}")
        warned = True
    if r.autonomy_mode == "apply_tests":
        print("NOTE: High-autonomy mode apply_tests increases compute and IO")
        warned = True
    if not warned:
        print("OK: No resource concerns detected for this run")


def _warn_on_frequency(rows: List[Row]) -> None:
    if len(rows) < 2:
        return
    recent = rows[-FREQ_WINDOW:]
    gaps = []
    for a, b in zip(recent[-FREQ_WINDOW:], recent[-FREQ_WINDOW+1:]):
        dt = b.ts - a.ts
        if dt > 0:
            gaps.append(dt)
    if gaps and (sum(gaps) / len(gaps)) < MIN_SPACING_SEC * 0.8:
        print(f"WARN: High run frequency (avg spacing {sum(gaps)/len(gaps):.1f}s; target ~{MIN_SPACING_SEC:.0f}s)")


def _warn_on_tes_surge(rows: List[Row]) -> None:
    if len(rows) < 5:
        return
    window = rows[-5:-1]  # exclude latest
    latest = rows[-1]
    avg = sum(r.tes for r in window) / len(window)
    if latest.tes >= avg + 3.0 and latest.tes >= 95.0:
        print(f"WARN: TES surge detected (latest {latest.tes:.1f} vs avg {avg:.1f} over last 4)")


def monitor(interval: int, tail: int, once: bool) -> int:
    last_count = 0
    # Initial dump
    rows = _read_rows()
    if rows:
        for r in rows[-tail:]:
            _print_summary(r)
        _warn_on_frequency(rows)
        _warn_on_tes_surge(rows)
        _warn_on_resource_draw(rows[-1])
        last_count = len(rows)
    else:
        print("No metrics yet. Waiting...")

    if once:
        return 0

    try:
        while True:
            time.sleep(interval)
            rows = _read_rows()
            if not rows or len(rows) == last_count:
                continue
            new = rows[last_count:]
            for r in new:
                _print_summary(r)
                _warn_on_resource_draw(r)
            _warn_on_frequency(rows)
            _warn_on_tes_surge(rows)
            last_count = len(rows)
    except KeyboardInterrupt:
        return 0


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Monitor TES and resource draw")
    p.add_argument("--interval", type=int, default=10)
    p.add_argument("--tail", type=int, default=5)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    return monitor(args.interval, args.tail, args.once)


if __name__ == "__main__":
    raise SystemExit(main())
