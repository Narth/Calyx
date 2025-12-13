#!/usr/bin/env python3
"""Alert cleanup utility

Usage:
    python -u tools/alert_cleanup.py --keep 50 --max-age-days 30 --dry-run

This moves old alerts to outgoing/alerts/archive by default (safe). Use --delete to permanently delete.
"""
from __future__ import annotations
import argparse
import shutil
import time
from pathlib import Path
import json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=100, help="Keep newest N alerts")
    parser.add_argument("--max-age-days", type=int, default=90, help="Delete alerts older than this many days")
    parser.add_argument("--delete", action="store_true", help="Permanently delete instead of moving to archive")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without applying")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    alerts_dir = root / "outgoing" / "alerts"
    archive_dir = alerts_dir / "archive"
    if not alerts_dir.exists():
        print("No alerts directory found.")
        return 0

    files = sorted([p for p in alerts_dir.glob("alert_*.json")], key=lambda p: p.stat().st_mtime, reverse=True)

    to_keep = files[: args.keep]
    to_check = files[args.keep :]

    now = time.time()
    max_age_sec = args.max_age_days * 24 * 3600

    actions = []
    for f in to_check:
        age = now - f.stat().st_mtime
        if age > max_age_sec:
            actions.append((f, "old"))
        else:
            actions.append((f, "prune"))

    if args.dry_run:
        print("Dry-run: would process the following alert files:")
        for f, reason in actions:
            print(f"  {f.name} -> {reason}")
        return 0

    archive_dir.mkdir(parents=True, exist_ok=True)
    for f, reason in actions:
        if args.delete:
            try:
                f.unlink()
                print(f"deleted {f.name}")
            except Exception as e:
                print("failed to delete", f, e)
        else:
            dest = archive_dir / f.name
            try:
                shutil.move(str(f), str(dest))
                print(f"moved {f.name} -> archive/")
            except Exception as e:
                print("failed to move", f, e)

    # Update latest_alert.json if needed
    latest = alerts_dir / "latest_alert.json"
    if latest.exists():
        try:
            data = json.loads(latest.read_text(encoding='utf-8'))
            latest_name = data.get("latest")
            if latest_name and not (alerts_dir / latest_name).exists():
                # pick newest remaining
                remain = sorted([p for p in alerts_dir.glob("alert_*.json")], key=lambda p: p.stat().st_mtime, reverse=True)
                if remain:
                    latest.write_text(json.dumps({"latest": remain[0].name, "ts": remain[0].stat().st_mtime}, indent=2), encoding='utf-8')
                else:
                    latest.unlink()
        except Exception:
            pass

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
