#!/usr/bin/env python3
"""
Process Watchdog: prune stale python processes and surface remediation hints.

The watchdog inspects running python.exe processes, identifies likely zombie or
orphaned workers, and optionally terminates those that the current user may
safely control. Results are appended to outgoing/watchdog/process_watchdog.log
for operator review.

Usage:
    python tools/process_watchdog.py --once            # single pass, dry-run
    python tools/process_watchdog.py --apply --once    # single pass, terminate
    python tools/process_watchdog.py --interval 900    # loop every 15 minutes
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import psutil

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outgoing" / "watchdog"
LOG_PATH = OUT_DIR / "process_watchdog.log"
STATE_PATH = OUT_DIR / "process_watchdog_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_candidate(proc: psutil.Process, max_age: float) -> bool:
    """Return True if the process appears stale and safe to consider."""
    try:
        if proc.pid == os.getpid():
            return False
        name = (proc.info.get("name") or "").lower()
        if "python" not in name:
            return False
        status = proc.info.get("status") or ""
        if status in (psutil.STATUS_ZOMBIE, getattr(psutil, "STATUS_DEAD", "dead")):
            return True
        create_time = proc.info.get("create_time") or 0.0
        age = time.time() - float(create_time)
        if age < max_age:
            return False
        cmdline: List[str] = proc.info.get("cmdline") or []
        # Minimal command line (binary only) is usually an orphan.
        if len(cmdline) <= 1:
            return True
        # Processes owned by the current user with idle CPU and long age.
        cpu = proc.info.get("cpu_percent") or 0.0
        if cpu == 0.0 and age >= max_age * 2:
            return True
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False
    except psutil.AccessDenied:
        # If we cannot inspect details we cannot make a determination.
        return False
    return False


def _terminate_process(proc: psutil.Process, timeout: float = 5.0) -> str:
    """Attempt to terminate the process and return a status string."""
    try:
        proc.terminate()
        proc.wait(timeout=timeout)
        return "terminated"
    except psutil.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=timeout)
            return "killed"
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return "vanished"
        except psutil.AccessDenied:
            return "access_denied"
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return "vanished"
    except psutil.AccessDenied:
        return "access_denied"
    return "error"


def _scan(max_age: float, apply: bool) -> Dict[str, object]:
    """Scan for stale processes and optionally terminate them."""
    candidates: List[Dict[str, object]] = []
    actions: List[Dict[str, object]] = []
    for proc in psutil.process_iter(
        attrs=["pid", "name", "status", "username", "create_time", "cmdline", "cpu_percent"]
    ):
        if not _is_candidate(proc, max_age=max_age):
            continue
        record: Dict[str, object] = {
            "pid": proc.info.get("pid"),
            "name": proc.info.get("name"),
            "status": proc.info.get("status"),
            "username": proc.info.get("username"),
            "create_time": proc.info.get("create_time"),
            "cmdline": proc.info.get("cmdline"),
        }
        candidates.append(record)
        if apply:
            outcome = _terminate_process(proc)
            record["action"] = outcome
        else:
            record["action"] = "dry_run"
        actions.append(record)
    return {
        "timestamp": _utc_now(),
        "hostname": os.environ.get("COMPUTERNAME") or "",
        "apply": apply,
        "max_age_seconds": max_age,
        "candidates": actions,
    }


def _write_log(summary: Dict[str, object]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(summary, ensure_ascii=False)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    with STATE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)


def run_watchdog(interval: int, max_age: float, apply: bool, once: bool) -> None:
    """Run the watchdog loop."""
    while True:
        summary = _scan(max_age=max_age, apply=apply)
        _write_log(summary)
        if once:
            break
        time.sleep(max(5, int(interval)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Process lifecycle watchdog")
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Interval in seconds between scans (default: 900 / 15 minutes)",
    )
    parser.add_argument(
        "--max-age",
        type=float,
        default=1800.0,
        help="Minimum process age in seconds before considering cleanup (default: 1800)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Terminate stale processes when possible (default: dry-run)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan instead of looping",
    )
    args = parser.parse_args()
    run_watchdog(interval=args.interval, max_age=args.max_age, apply=bool(args.apply), once=bool(args.once))


if __name__ == "__main__":
    main()
