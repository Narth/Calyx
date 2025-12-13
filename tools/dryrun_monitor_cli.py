#!/usr/bin/env python3
"""Dry-run Monitor CLI

Simple CLI to watch dry-run/autonomy progress. It prints the `autonomy_monitor`
heartbeat, the `cbo` and `cp12` locks, the coordinator status, and the bridge
dispatch queue summary in a short loop so operators can watch progress.

Usage:
  python tools/dryrun_monitor_cli.py --interval 5
  python tools/dryrun_monitor_cli.py --once

This tool is read-only and intended for operators to monitor the dry-run.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOCK_MON = OUT / "autonomy_monitor.lock"
LOCK_CBO = OUT / "cbo.lock"
LOCK_CP12 = OUT / "cp12.lock"
DISPATCH_IN = OUT / "bridge" / "dispatch"


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _coord_status() -> str:
    try:
        out = subprocess.run(["python", "-u", "tools/coordinatorctl.py", "status"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception as e:
        return f"[error running coordinatorctl status: {e}]"


def _dispatch_summary() -> str:
    try:
        if not DISPATCH_IN.exists():
            return "dispatch: missing"
        files = list(DISPATCH_IN.glob("*.json"))
        proc = list((DISPATCH_IN / "processing").glob("*.json")) if (DISPATCH_IN / "processing").exists() else []
        done = list((DISPATCH_IN / "completed").glob("*.json")) if (DISPATCH_IN / "completed").exists() else []
        return f"dispatch: in={len(files)} proc={len(proc)} done={len(done)}"
    except Exception as e:
        return f"dispatch: error {e}"


def show_once() -> None:
    m = _read_json(LOCK_MON)
    cbo = _read_json(LOCK_CBO)
    cp12 = _read_json(LOCK_CP12)
    print("--- AUTONOMY MONITOR ---")
    print(json.dumps(m or {}, indent=2, ensure_ascii=False))
    print("--- CBO ---")
    print(json.dumps(cbo or {}, indent=2, ensure_ascii=False))
    print("--- CP12 ---")
    print(json.dumps(cp12 or {}, indent=2, ensure_ascii=False))
    print("--- COORDINATOR STATUS ---")
    print(_coord_status())
    print("--- DISPATCH SUMMARY ---")
    print(_dispatch_summary())


def loop(interval: float) -> None:
    try:
        while True:
            show_once()
            print("\n--- sleeping {}s ---\n".format(interval))
            time.sleep(max(1.0, float(interval)))
    except KeyboardInterrupt:
        print("stopped")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=0.0, help="Poll interval seconds (0 = run once)")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)
    if args.once or args.interval <= 0.0:
        show_once()
        return 0
    loop(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
