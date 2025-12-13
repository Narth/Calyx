#!/usr/bin/env python3
"""Archive agent_run directories older than N days.

This script archives agent_run directories to free disk space while preserving
historical data. It compresses directories and maintains full audit trail.

Usage:
    python tools/archive_agent_runs.py --days 7 --dry-run
    python tools/archive_agent_runs.py --days 7
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import tarfile
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTGOING = ROOT / "outgoing"
ARCHIVE_DIR = ROOT / "logs" / "archive" / "agent_runs"


def parse_timestamp(directory_name: str) -> int | None:
    """Extract timestamp from agent_run_<timestamp> directory name."""
    if not directory_name.startswith("agent_run_"):
        return None
    try:
        return int(directory_name.split("_")[-1])
    except (ValueError, IndexError):
        return None


def get_old_directories(days: int) -> list[Path]:
    """Find agent_run directories older than N days."""
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    cutoff_ts = int(cutoff_time)
    
    old_dirs = []
    for path in OUTGOING.glob("agent_run_*"):
        if not path.is_dir():
            continue
        ts = parse_timestamp(path.name)
        if ts and ts < cutoff_ts:
            old_dirs.append(path)
    
    return sorted(old_dirs, key=lambda p: p.name)


def archive_directory(source: Path, dry_run: bool = False) -> dict:
    """Archive a single agent_run directory to compressed tar.gz."""
    ts = parse_timestamp(source.name)
    if not ts:
        return {"status": "error", "reason": "Invalid timestamp"}
    
    dt = datetime.fromtimestamp(ts)
    archive_name = f"agent_run_{ts}_{dt.strftime('%Y%m%d')}.tar.gz"
    archive_path = ARCHIVE_DIR / archive_name
    
    if dry_run:
        return {
            "status": "dry_run",
            "source": str(source.relative_to(ROOT)),
            "archive": str(archive_path.relative_to(ROOT)),
            "size": sum(f.stat().st_size for f in source.rglob('*') if f.is_file()),
        }
    
    # Create archive
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(source, arcname=source.name)
        
        # Get size before removal
        source_size = sum(f.stat().st_size for f in source.rglob('*') if f.is_file())
        archive_size = archive_path.stat().st_size
        
        # Remove original directory
        shutil.rmtree(source)
        
        return {
            "status": "archived",
            "source": str(source.relative_to(ROOT)),
            "archive": str(archive_path.relative_to(ROOT)),
            "source_size": source_size,
            "archive_size": archive_size,
            "saved_bytes": source_size - archive_size,
        }
    except Exception as e:
        return {
            "status": "error",
            "source": str(source.relative_to(ROOT)),
            "error": str(e),
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Archive old agent_run directories")
    ap.add_argument("--days", type=int, default=7, help="Archive directories older than N days")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be archived without doing it")
    ap.add_argument("--max-count", type=int, help="Limit number of directories to archive")
    args = ap.parse_args(argv)
    
    print(f"[SSA] Archiving agent_run directories older than {args.days} days")
    if args.dry_run:
        print("[SSA] DRY RUN MODE - No changes will be made")
    
    old_dirs = get_old_directories(args.days)
    
    if not old_dirs:
        print("[SSA] No directories found to archive")
        return 0
    
    if args.max_count:
        old_dirs = old_dirs[:args.max_count]
    
    print(f"[SSA] Found {len(old_dirs)} directories to archive")
    
    results = []
    total_saved = 0
    
    for directory in old_dirs:
        result = archive_directory(directory, dry_run=args.dry_run)
        results.append(result)
        
        if result["status"] == "archived":
            saved = result.get("saved_bytes", 0)
            total_saved += saved
            print(f"[SSA] Archived: {result['source']} ({saved / 1024 / 1024:.2f} MB saved)")
        elif result["status"] == "dry_run":
            size = result.get("size", 0)
            print(f"[SSA] Would archive: {result['source']} ({size / 1024 / 1024:.2f} MB)")
        else:
            print(f"[SSA] Error: {result.get('reason', result.get('error', 'unknown'))}")
    
    # Summary
    archived_count = sum(1 for r in results if r["status"] == "archived")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    print(f"\n[SSA] Summary:")
    print(f"  - Processed: {len(results)}")
    print(f"  - Archived: {archived_count}")
    print(f"  - Errors: {error_count}")
    if total_saved > 0:
        print(f"  - Total space saved: {total_saved / 1024 / 1024:.2f} MB")
    
    # Write results to file
    results_file = ARCHIVE_DIR / f"archive_report_{int(time.time())}.json"
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "days": args.days,
            "dry_run": args.dry_run,
            "results": results,
            "summary": {
                "total": len(results),
                "archived": archived_count,
                "errors": error_count,
                "total_saved_bytes": total_saved,
            }
        }, f, indent=2)
    
    print(f"[SSA] Report saved: {results_file.relative_to(ROOT)}")
    
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

