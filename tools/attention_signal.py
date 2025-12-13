#!/usr/bin/env python3
"""
Console-based attention indicator for Station Calyx.

Displays a simple traffic-light style status based on core guardrails:
  - CBO heartbeat metrics (CPU/RAM/GPU guard bands)
  - Scheduler status / warnings
  - Micro-fix guardrail monitor (when active)

Usage:
  python tools/attention_signal.py          # live watch (default 10s interval)
  python tools/attention_signal.py --once   # single snapshot
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
CBO_LOCK = ROOT / "outgoing" / "cbo.lock"
SCHEDULER_LOCK = ROOT / "outgoing" / "scheduler.lock"
MICRO_GUARD_LOCK = ROOT / "outgoing" / "micro_fix_guard.lock"

CPU_LIMIT = 70.0
RAM_LIMIT = 75.0
GPU_LIMIT = 85.0


def read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def evaluate_status() -> Tuple[int, list[str]]:
    """
    Returns (severity, reasons)
        severity: 0 green, 1 yellow, 2 red
    """
    reasons: list[str] = []
    severity = 0

    hb = read_json(CBO_LOCK)
    metrics = hb.get("metrics") or {}
    cpu = float(metrics.get("cpu_pct") or 0.0)
    ram = float(metrics.get("mem_used_pct") or 0.0)
    gpu = float(
        ((metrics.get("gpu") or {}).get("gpus") or [{}])[0].get("util_pct") or 0.0
    )

    # Hard guardrail breaches -> red
    if cpu >= CPU_LIMIT or ram >= RAM_LIMIT or gpu >= GPU_LIMIT:
        severity = max(severity, 2)
        reasons.append(
            f"Resource guardrail hit (CPU {cpu:.1f}%, RAM {ram:.1f}%, GPU {gpu:.1f}%)"
        )
    elif cpu >= CPU_LIMIT - 5 or ram >= RAM_LIMIT - 3:
        severity = max(severity, 1)
        reasons.append(
            f"Resource pressure rising (CPU {cpu:.1f}%, RAM {ram:.1f}%)"
        )

    # Scheduler warnings
    sch = read_json(SCHEDULER_LOCK)
    status = (sch.get("status") or "").lower()
    if status in {"warn", "attention", "error"}:
        severity = max(severity, 2)
        reasons.append(
            f"Scheduler flagged status '{status}' ({sch.get('status_message', '').strip()})"
        )

    # Micro-fix guardrail monitor
    guard = read_json(MICRO_GUARD_LOCK)
    guard_state = (guard.get("state") or "").lower()
    if guard_state in {"stopped", "timeout"}:
        severity = max(severity, 2)
        reasons.append(
            f"Micro-fix guard halted runs ({guard.get('reason', 'unknown reason')})"
        )
    elif guard_state == "paused":
        severity = max(severity, 1)
        reasons.append(
            f"Micro-fix guard paused due to load ({guard.get('reason', 'resource pressure')})"
        )
    elif guard_state == "monitoring":
        runs = guard.get("runs_completed", 0)
        target = guard.get("target_runs", 0)
        severity = max(severity, 1)
        reasons.append(
            f"Micro-fix guard active ({runs}/{target} runs complete)"
        )

    return severity, reasons


def render(severity: int, reasons: list[str]) -> None:
    lights = [
        ["( )", "( )", "(O)"],   # severity 0 -> green
        ["( )", "(O)", "( )"],   # severity 1 -> yellow
        ["(O)", "( )", "( )"],   # severity 2 -> red
    ]
    labels = ["GREEN", "YELLOW", "RED"]
    level = min(severity, 2)
    art = lights[level]
    print("=" * 50)
    print("Station Calyx Attention Signal")
    print("=" * 50)
    print(f"    Red   : {art[0]}")
    print(f"    Yellow: {art[1]}")
    print(f"    Green : {art[2]}")
    print("-" * 50)
    if reasons:
        for idx, reason in enumerate(reasons, 1):
            print(f"{idx:02d}. {reason}")
    else:
        print("All systems within guardrails.")
    print("-" * 50)
    print(f"Overall: {labels[level]}")
    print("=" * 50)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ASCII traffic-light indicator for Station Calyx guardrails"
    )
    parser.add_argument("--interval", type=int, default=10, help="Polling interval seconds")
    parser.add_argument("--once", action="store_true", help="Print a single snapshot and exit")
    args = parser.parse_args(argv)

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            severity, reasons = evaluate_status()
            render(severity, reasons)
            if args.once:
                break
            time.sleep(max(2, args.interval))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
