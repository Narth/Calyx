"""
Log Housekeeper
- Archives older SVF logs/reports to reduce file count/size over time.
- Targets (under outgoing/): shared_logs/, overseer_reports/, reports/
- Strategy: keep last N days (default 14) of *.md files; older files for a month are packed into logs/archive/YYYY-MM/<category>_YYYY-MM.tar.gz
- Safe: creates archives if needed; skips if no files; uses tarfile + gzip; Windows-friendly paths.
- CLI:
    python -m tools.log_housekeeper run --keep-days 14
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
LOGS = ROOT / 'logs'
ARCHIVE_ROOT = LOGS / 'archive'
CATEGORIES = {
    'shared_logs': OUT / 'shared_logs',
    'overseer_reports': OUT / 'overseer_reports',
    'reports': OUT / 'reports',
}


def _month_key(dt: datetime) -> str:
    return dt.strftime('%Y-%m')


def _iter_md_files(folder: Path):
    if not folder.exists():
        return
    for p in folder.glob('*.md'):
        if p.is_file():
            yield p


def _mtime_utc(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)


def _archive_paths_for(category: str, month_key: str) -> Path:
    cat_dir = ARCHIVE_ROOT / month_key
    cat_dir.mkdir(parents=True, exist_ok=True)
    return cat_dir / f'{category}_{month_key}.tar.gz'


def _archive_files(category: str, files: list[Path], month_key: str):
    if not files:
        return
    archive_path = _archive_paths_for(category, month_key)
    mode = 'a:gz' if archive_path.exists() else 'w:gz'
    with tarfile.open(archive_path, mode) as tar:
        for f in files:
            tar.add(f, arcname=f.name)
            try:
                f.unlink()
            except Exception:
                pass


def run(keep_days: int = 14) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    for category, folder in CATEGORIES.items():
        if not folder.exists():
            continue
        # Group old files by month
        buckets: dict[str, list[Path]] = {}
        for p in _iter_md_files(folder):
            ts = _mtime_utc(p)
            if ts > cutoff:
                continue
            key = _month_key(ts)
            buckets.setdefault(key, []).append(p)
        # Archive per month
        for key, files in buckets.items():
            _archive_files(category, files, key)


def _cmd_run(args: argparse.Namespace) -> int:
    run(args.keep_days)
    print('ok: housekeeping complete')
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='log_housekeeper', description='Archive older SVF logs/reports')
    ap.add_argument('cmd', choices=['run'])
    ap.add_argument('--keep-days', type=int, default=14)
    args = ap.parse_args(argv)
    if args.cmd == 'run':
        return _cmd_run(args)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
