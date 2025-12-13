#!/usr/bin/env python3
"""Autonomy runner (5-hour)

Runs the existing `tools/autonomy_monitor.py` loop for a bounded duration (default 5 hours).
This is a safe harness that writes a runner lock and terminates early on errors.

Usage:
  python tools/autonomy_runner_5h.py --duration 18000 --interval 60
  python tools/autonomy_runner_5h.py --once
"""
from __future__ import annotations
import argparse
import time
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK = OUT / "autonomy_runner.lock"
LOG = OUT / "autonomy_runner.log"


def _write_lock(status: str, extra: dict | None = None) -> None:
    payload = {
        "name": "autonomy_runner",
        "pid": os.getpid(),
        "ts": time.time(),
        "iso": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    if extra:
        payload.update(extra)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(str(payload), encoding="utf-8")
    except Exception:
        pass


def _log(msg: str) -> None:
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")
    except Exception:
        pass


def run_once(timeout: float = 30.0) -> int:
    """Run one monitor pulse via the existing CLI wrapper.

    Uses the same subprocess-based monitor so behavior matches operators' usage.
    """
    import subprocess

    _write_lock("running")
    _log("Running one-shot pulse via tools/autonomy_monitor.py")
    cmd = [sys.executable, "-u", "tools/autonomy_monitor.py", "--once"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        _log(f"rc={proc.returncode} stdout_len={len(proc.stdout)} stderr_len={len(proc.stderr)}")
        if proc.returncode != 0:
            _write_lock("error", {"rc": proc.returncode})
            _log(f"ERROR: non-zero rc {proc.returncode}")
            return proc.returncode
        _write_lock("ok", {"last_ok": time.time()})
        return 0
    except subprocess.TimeoutExpired:
        _write_lock("error", {"reason": "timeout"})
        _log("ERROR: timeout")
        return 2


def run_loop(duration_sec: int = 5 * 3600, interval: int = 60) -> int:
    """Run the monitor loop for up to duration_sec, polling every `interval` seconds."""
    deadline = time.time() + duration_sec
    _write_lock("running", {"deadline_iso": datetime.fromtimestamp(deadline, timezone.utc).isoformat()})
    _log(f"Starting loop: duration_sec={duration_sec} interval={interval}")
    try:
        while time.time() < deadline:
            rc = run_once(timeout=30.0)
            if rc != 0:
                _log(f"Stopping early due to rc={rc}")
                return rc
            # Sleep but remain responsive to early termination
            sleep_left = int(min(interval, max(1, deadline - time.time())))
            time.sleep(sleep_left)
        _write_lock("finished")
        _log("Finished scheduled run")
        return 0
    except KeyboardInterrupt:
        _write_lock("stopped")
        _log("Interrupted by KeyboardInterrupt")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="autonomy_runner_5h")
    ap.add_argument("--duration", type=int, default=5 * 3600, help="Total duration seconds (default 5h)")
    ap.add_argument("--interval", type=int, default=60, help="Poll interval in seconds")
    ap.add_argument("--once", action="store_true", help="Run one pulse and exit")
    args = ap.parse_args(argv)

    if args.once:
        return run_once()
    return run_loop(duration_sec=args.duration, interval=args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
