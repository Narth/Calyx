#!/usr/bin/env python3
"""Alerts cron runner

Runs tools/alert_cleanup.py on a schedule. Designed to be started as a background
process or as a Windows scheduled task. Safe defaults: daily, dry-run optional.

Usage examples:
  # Dry-run once now
  python -u tools\alerts_cron.py --run-once --dry-run

  # Run every 24h and actually archive old alerts
  python -u tools\alerts_cron.py --interval 86400 --keep 100 --max-age-days 90

"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run_cleanup_once(root: Path, keep: int, max_age_days: int, delete: bool, dry_run: bool) -> int:
    cmd = [sys.executable, str(root / "tools" / "alert_cleanup.py"), "--keep", str(keep), "--max-age-days", str(max_age_days)]
    if delete:
        cmd.append("--delete")
    if dry_run:
        cmd.append("--dry-run")
    print(f"{datetime.now(timezone.utc).isoformat()} alerts_cron: running: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except Exception as e:
        print("alerts_cron: cleanup command failed:", e)
        return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=86400.0, help="Interval seconds between runs (default 86400 = 24h)")
    ap.add_argument("--run-once", action="store_true", help="Run once and exit")
    ap.add_argument("--keep", type=int, default=100, help="Keep newest N alerts")
    ap.add_argument("--max-age-days", type=int, default=90, help="Max age days to archive/delete")
    ap.add_argument("--delete", action="store_true", help="Permanently delete instead of moving to archive")
    ap.add_argument("--dry-run", action="store_true", help="Pass dry-run to alert_cleanup")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]

    if args.run_once:
        return run_cleanup_once(root, args.keep, args.max_age_days, args.delete, args.dry_run)

    try:
        while True:
            rc = run_cleanup_once(root, args.keep, args.max_age_days, args.delete, args.dry_run)
            # Sleep interval
            sleep_for = max(1.0, float(args.interval))
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("alerts_cron: stopped by user")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
