#!/usr/bin/env python3
"""Rollback helper for coordinator autonomy state.

Restores the most recent backup of `state/coordinator_state.json` (files matching
`state/coordinator_state.json.bak*`) into `state/coordinator_state.json`, writes an
audit JSON into `outgoing/bridge/` and appends a short line to
`outgoing/bridge/dialog.log`.

Usage:
  python tools\rollback_autonomy.py --dry-run   # show what would be done
  python tools\rollback_autonomy.py --apply     # perform restore and write audit

On Windows, if a runner PID is present in `outgoing/autonomy_runner.lock`, the
script will attempt to stop it using `taskkill` when `--apply` is provided.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
OUT_BRIDGE = ROOT / "outgoing" / "bridge"
OUT_BRIDGE.mkdir(parents=True, exist_ok=True)

def find_latest_backup() -> Path | None:
    pattern = "coordinator_state.json.bak*"
    matches = list(STATE_DIR.glob(pattern))
    if not matches:
        return None
    # choose by modified time
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]

def read_runner_pid(lock_path: Path) -> int | None:
    try:
        txt = lock_path.read_text(encoding='utf-8')
        import json as _j
        data = _j.loads(txt)
        return int(data.get('pid'))
    except Exception:
        return None

def stop_process(pid: int) -> tuple[bool,str]:
    # Try a cross-platform best-effort stop
    try:
        if sys.platform.startswith('win'):
            cmd = ["taskkill", "/PID", str(pid), "/F"]
        else:
            cmd = ["kill", "-TERM", str(pid)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ok = proc.returncode == 0
        return ok, proc.stdout + proc.stderr
    except Exception as e:
        return False, str(e)

def write_audit(old_path: Path, restored_from: Path, actor: str = "operator") -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    audit = {
        "action": "rollback_autonomy",
        "actor": actor,
        "timestamp": ts,
        "restored_from": str(restored_from),
        "restored_to": str(old_path),
    }
    out_path = OUT_BRIDGE / f"autonomy_rollback_{ts}.json"
    out_path.write_text(json.dumps(audit, indent=2), encoding='utf-8')
    # append a short human line to dialog.log
    dlg = OUT_BRIDGE / "dialog.log"
    dlg_line = f"{ts} ROLLBACK> restored {restored_from.name} by {actor}\n"
    with dlg.open('a', encoding='utf-8') as fh:
        fh.write(dlg_line)
    return out_path

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--apply', action='store_true', help='Perform restore and write audit')
    parser.add_argument('--stop-runner', action='store_true', help='Attempt to stop autonomy runner if lock present (requires --apply)')
    args = parser.parse_args(argv)

    latest = find_latest_backup()
    if latest is None:
        print('No coordinator_state.json backups found in', STATE_DIR)
        return 2

    target = STATE_DIR / 'coordinator_state.json'
    print('Latest backup:', latest)
    print('Target state file:', target)

    if args.dry_run:
        return 0

    # perform restore
    try:
        shutil.copy2(latest, target)
    except Exception as e:
        print('Failed to restore:', e)
        return 3

    audit_path = write_audit(target, latest)
    print('Restored. Audit written to', audit_path)

    # optionally stop runner
    if args.stop_runner:
        lock = ROOT / 'outgoing' / 'autonomy_runner.lock'
        if lock.exists():
            pid = read_runner_pid(lock)
            if pid:
                ok, txt = stop_process(pid)
                print('Attempted to stop runner pid', pid, 'ok=', ok)
                if txt:
                    print(txt)
            else:
                print('Runner lock present but pid not readable')
        else:
            print('No autonomy_runner.lock present')

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
