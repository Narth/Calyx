#!/usr/bin/env python3
"""
Atomic intent writer: writes an intent file atomically into
`governance/intents/inbox/` by writing a staging file `<target>.pending`
and then using an atomic replace to finalize `<target>.json`.

Rules enforced:
 - target must be inside `governance/intents/inbox/`
 - target filename must end with `.json`
 - absolute paths or traversal segments are refused

Usage:
  python tools/atomic_intent_writer.py governance/intents/inbox/intent-0001.json
  (intent JSON must be provided on stdin)
"""
from pathlib import Path
import sys
import json
import os

ROOT = Path(__file__).resolve().parents[1]
INBOX_DIR = (ROOT / 'governance' / 'intents' / 'inbox').resolve()


def write_atomic(target_path: Path, data: dict):
    # Normalize paths
    try:
        target_parent = target_path.parent.resolve()
        target_resolved = (target_path).resolve()
    except Exception:
        raise RuntimeError('invalid_target_path')

    # Ensure target is inside governance/intents/inbox
    if not str(target_resolved).startswith(str(INBOX_DIR) + os.sep) and str(target_resolved) != str(INBOX_DIR):
        raise RuntimeError('target_not_in_inbox')

    # Only allow .json final names
    if not target_path.name.endswith('.json'):
        raise RuntimeError('target_must_end_with_json')

    # Reject traversal segments in provided parts
    if '..' in target_path.parts:
        raise RuntimeError('traversal_segments_disallowed')

    # Write to a staging file in the same directory and atomically replace using os.replace
    staging = target_path.with_name(target_path.name + '.pending')
    staging.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    # atomic rename/replace
    os.replace(str(staging), str(target_path))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: atomic_intent_writer.py <target.json>')
        sys.exit(1)
    tp = Path(sys.argv[1])
    j = sys.stdin.read()
    try:
        d = json.loads(j)
    except Exception:
        print('Invalid JSON on stdin')
        sys.exit(2)
    tp.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_atomic(tp, d)
        print('Wrote', tp)
    except Exception as e:
        print('Write failed:', e)
        sys.exit(3)
