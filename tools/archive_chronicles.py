#!/usr/bin/env python3
"""Archive old chronicles to recover disk space."""
import argparse
import tarfile
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHRONICLES = ROOT / "outgoing" / "chronicles"
ARCHIVE_DIR = ROOT / "logs" / "archive" / "chronicles"

def archive_old_chronicles(days: int, dry_run: bool = False):
    """Archive chronicles older than N days."""
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()
    
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    
    files_to_archive = []
    for item in CHRONICLES.rglob('*'):
        if item.is_file() and item.stat().st_mtime < cutoff_ts:
            files_to_archive.append(item)
    
    if not files_to_archive:
        print(f"[SSA] No chronicles older than {days} days found")
        return
    
    print(f"[SSA] Found {len(files_to_archive)} files to archive")
    
    month_key = cutoff.strftime('%Y-%m')
    archive_path = ARCHIVE_DIR / f"chronicles_{month_key}.tar.gz"
    
    if dry_run:
        total_size = sum(f.stat().st_size for f in files_to_archive)
        print(f"[SSA] Would archive {len(files_to_archive)} files ({total_size / 1024 / 1024:.2f} MB)")
        print(f"[SSA] Archive would be: {archive_path.relative_to(ROOT)}")
        return
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        for file in files_to_archive:
            rel_path = file.relative_to(CHRONICLES)
            tar.add(file, arcname=str(rel_path))
            file.unlink()
    
    print(f"[SSA] Archived {len(files_to_archive)} files to {archive_path.relative_to(ROOT)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    archive_old_chronicles(args.days, args.dry_run)

