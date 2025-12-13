#!/usr/bin/env python3
"""CBO Review helper

List alerts and allow marking as retained or archived via CLI flags. Designed for interactive CBO workflows, but supports scripted calls.

Usage:
    python -u tools/cbo_review.py --list
    python -u tools/cbo_review.py --retain alert_file.json
    python -u tools/cbo_review.py --archive alert_file.json
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import json
import sys


def list_alerts(root: Path):
    alerts_dir = root / "outgoing" / "alerts"
    if not alerts_dir.exists():
        print("No alerts directory")
        return 0
    for p in sorted(alerts_dir.glob("alert_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        print(p.name)
    return 0


def retain_alert(root: Path, name: str):
    alerts_dir = root / "outgoing" / "alerts"
    retained = alerts_dir / "retained"
    retained.mkdir(parents=True, exist_ok=True)
    src = alerts_dir / name
    if not src.exists():
        print("Not found:", name)
        return 2
    dst = retained / name
    shutil.move(str(src), str(dst))
    print("retained:", name)
    return 0


def archive_alert(root: Path, name: str):
    alerts_dir = root / "outgoing" / "alerts"
    archive = alerts_dir / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    src = alerts_dir / name
    if not src.exists():
        print("Not found:", name)
        return 2
    dst = archive / name
    shutil.move(str(src), str(dst))
    print("archived:", name)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--retain", help="Alert filename to retain")
    parser.add_argument("--archive", help="Alert filename to archive")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.list:
        return list_alerts(root)
    if args.retain:
        return retain_alert(root, args.retain)
    if args.archive:
        return archive_alert(root, args.archive)
    parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
