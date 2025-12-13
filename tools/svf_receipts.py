"""
SVF Receipts utility
- Single CSV log to minimize file count: logs/svf_receipts.csv
- Supports receipt types: sent, delivered, read
- Auto-archives to logs/receipts_archive/svf_receipts_YYYY-MM.csv.gz when size exceeds 5 MiB or month rolls over
- CLI usage:
    python -m tools.svf_receipts write --message-id MID --type delivered --agent CP7 --artifact outgoing/shared_logs/... --meta "key=value"
    python -m tools.svf_receipts rollup
"""
from __future__ import annotations
import argparse
import csv
import gzip
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = ROOT / 'logs'
RECEIPTS_CSV = LOGS_DIR / 'svf_receipts.csv'
ARCHIVE_DIR = LOGS_DIR / 'receipts_archive'
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB

VALID_TYPES = {'sent', 'delivered', 'read'}


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_header():
    if not RECEIPTS_CSV.exists():
        with RECEIPTS_CSV.open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['ts', 'message_id', 'type', 'agent', 'artifact', 'meta'])


def _current_month_tag() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


def _archive_if_needed():
    # Roll on size
    if RECEIPTS_CSV.exists() and RECEIPTS_CSV.stat().st_size >= MAX_SIZE_BYTES:
        _archive_current()


def _archive_current():
    if not RECEIPTS_CSV.exists():
        return
    month = _current_month_tag()
    archive_path = ARCHIVE_DIR / f'svf_receipts_{month}.csv.gz'
    # Append current CSV to gzip archive
    with RECEIPTS_CSV.open('rb') as src, gzip.open(archive_path, 'ab') as gz:
        gz.write(src.read())
    # Reset CSV with header only
    _ensure_header()


def _dedup_exists(message_id: str, rtype: str, agent: str) -> bool:
    try:
        if not RECEIPTS_CSV.exists():
            return False
        # If very large, skip dedup to avoid heavy I/O
        if RECEIPTS_CSV.stat().st_size > 10 * 1024 * 1024:
            return False
        with RECEIPTS_CSV.open('r', newline='', encoding='utf-8') as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get('message_id') == message_id and row.get('type') == rtype and row.get('agent') == agent:
                    return True
        return False
    except Exception:
        return False


def write_receipt(message_id: str, rtype: str, agent: str, artifact: str = '', meta: str = '') -> Path:
    if rtype not in VALID_TYPES:
        raise ValueError(f'Invalid receipt type: {rtype}. Must be one of {sorted(VALID_TYPES)}')
    _ensure_dirs()
    _ensure_header()
    if _dedup_exists(message_id, rtype, agent):
        return RECEIPTS_CSV
    ts = _timestamp()
    with RECEIPTS_CSV.open('a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow([ts, message_id, rtype, agent, artifact, meta])
    _archive_if_needed()
    return RECEIPTS_CSV


def _cmd_write(args: argparse.Namespace) -> int:
    write_receipt(args.message_id, args.type, args.agent, args.artifact or '', args.meta or '')
    print(f"ok: wrote receipt type={args.type} message_id={args.message_id} agent={args.agent}")
    return 0


def _cmd_rollup(args: argparse.Namespace) -> int:
    _ensure_dirs()
    _ensure_header()
    _archive_current()
    print("ok: archive rollup executed")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog='svf_receipts', description='SVF receipts writer')
    sub = p.add_subparsers(dest='cmd', required=True)

    pw = sub.add_parser('write', help='Write a receipt row')
    pw.add_argument('--message-id', required=True)
    pw.add_argument('--type', required=True, choices=sorted(VALID_TYPES))
    pw.add_argument('--agent', required=True)
    pw.add_argument('--artifact', required=False)
    pw.add_argument('--meta', required=False)
    pw.set_defaults(func=_cmd_write)

    pr = sub.add_parser('rollup', help='Force archive rollup of current CSV')
    pr.set_defaults(func=_cmd_rollup)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
