#!/usr/bin/env python3
"""
Micro-fix guardrail monitor.

Watches agent_scheduler activity to enforce:
  * Maximum number of micro-fix runs per unattended block.
  * CPU/RAM guardrails (default 70% / 75%).
  * Optional max-runtime window.

If any limit is hit, the script terminates agent_scheduler.py, writes
status to outgoing/micro_fix_guard.lock, and exits with non-zero code.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

try:
    import psutil  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"[ERROR] psutil required: {exc}", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = ROOT / "logs" / "agent_metrics.csv"
LOCK_PATH = ROOT / "outgoing" / "micro_fix_guard.lock"
LOAD_MODE_FILE = ROOT / "state" / "load_mode.json"
SCHEDULER_NAME = "tools/agent_scheduler.py"


def count_metrics_rows() -> int:
    if not METRICS_CSV.exists():
        return 0
    try:
        with METRICS_CSV.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            return sum(1 for _ in reader) - 1  # minus header
    except Exception:
        return 0


def find_scheduler_pids() -> Dict[int, psutil.Process]:
    procs: Dict[int, psutil.Process] = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name.startswith("python"):
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if SCHEDULER_NAME in cmdline.replace("\\", "/"):
                procs[proc.pid] = proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procs


def _load_mode() -> str:
    try:
        data = json.loads(LOAD_MODE_FILE.read_text(encoding="utf-8"))
        mode = str(data.get("mode", "normal")).strip().lower()
        return mode if mode in {"normal", "high_load"} else "normal"
    except Exception:
        return "normal"


def write_lock(status: Dict[str, any]) -> None:
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
    except Exception:
        pass


def build_status(
    state: str,
    message: str,
    runs_completed: int,
    target_runs: int,
    elapsed_min: float,
    reason: Optional[str] = None,
    load_mode: str = "normal",
) -> Dict[str, any]:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    status = {
        "name": "micro_fix_guard",
        "state": state,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runs_completed": runs_completed,
        "target_runs": target_runs,
        "elapsed_minutes": round(elapsed_min, 2),
        "load_mode": load_mode,
        "metrics": {
            "cpu_pct": cpu,
            "ram_pct": vm.percent,
            "available_gb": round(vm.available / (1024 ** 3), 2),
        },
    }
    if reason:
        status["reason"] = reason
    return status


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Guardrail monitor for micro-fix discipline mode")
    ap.add_argument("--target-runs", type=int, default=10, help="Stop after N micro-fix runs (default 10)")
    ap.add_argument("--max-minutes", type=int, default=60, help="Maximum unattended minutes (default 60)")
    ap.add_argument("--cpu-limit", type=float, default=70.0, help="CPU percentage guardrail")
    ap.add_argument("--mem-limit", type=float, default=75.0, help="RAM percentage guardrail")
    ap.add_argument("--interval", type=int, default=60, help="Monitoring interval seconds")
    args = ap.parse_args(argv)

    baseline_runs = count_metrics_rows()
    start_ts = datetime.now(timezone.utc)
    write_lock(
        build_status(
            "monitoring",
            "Guardrail monitor started",
            0,
            args.target_runs,
            0.0,
        )
    )

    paused_for_resources = False

    while True:
        load_mode = _load_mode()
        cpu_limit = float(args.cpu_limit)
        mem_limit = float(args.mem_limit)
        if load_mode == "high_load":
            cpu_limit = min(cpu_limit + 5.0, 85.0)
            mem_limit = min(mem_limit + 3.0, 80.0)

        total_runs = max(0, count_metrics_rows() - baseline_runs)
        elapsed = datetime.now(timezone.utc) - start_ts
        elapsed_min = elapsed.total_seconds() / 60.0
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        if cpu >= cpu_limit or vm.percent >= mem_limit:
            paused_for_resources = True
            reason = f"resource_guardrail cpu={cpu:.1f}% mem={vm.percent:.1f}%"
            write_lock(
                build_status(
                    "paused",
                    "High load detected; holding micro-fix runs",
                    total_runs,
                    args.target_runs,
                    elapsed_min,
                    reason=reason,
                    load_mode=load_mode,
                )
            )
            time.sleep(max(10, args.interval))
            continue
        else:
            if paused_for_resources:
                paused_for_resources = False

        if total_runs >= args.target_runs:
            reason = f"target_runs_reached ({total_runs})"
            write_lock(
                build_status(
                    "completed",
                    "Target micro-fix run count reached; scheduler paused",
                    total_runs,
                    args.target_runs,
                    elapsed_min,
                    reason=reason,
                    load_mode=load_mode,
                )
            )
            return 0

        if elapsed >= timedelta(minutes=args.max_minutes):
            reason = "max_minutes_exceeded"
            write_lock(
                build_status(
                    "timeout",
                    "Max unattended window reached; scheduler paused",
                    total_runs,
                    args.target_runs,
                    elapsed_min,
                    reason=reason,
                    load_mode=load_mode,
                )
            )
            return 0

        write_lock(
            build_status(
                "monitoring",
                "Guardrail monitor active",
                total_runs,
                args.target_runs,
                elapsed_min,
                load_mode=load_mode,
            )
        )
        time.sleep(max(10, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
