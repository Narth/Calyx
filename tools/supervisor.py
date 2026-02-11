"""Supervisor: restart failed processes and tail evidence for auditing

Usage: python tools/supervisor.py

Behavior:
 - Reads outgoing/shared_logs/processes.json for expected services
 - Checks each PID is alive; if not, attempts to restart the service script
 - Emits SERVICE_RESTARTED evidence events when it restarts a service
 - Tails station_calyx/data/evidence.jsonl and writes appended lines to outgoing/shared_logs/supervisor.log
 - Writes updated processes.json when it restarts processes

This is minimal, cross-platform, and avoids external dependencies.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / 'outgoing' / 'shared_logs' / 'processes.json'
EVIDENCE = ROOT / 'station_calyx' / 'data' / 'evidence.jsonl'
SUP_LOG = ROOT / 'outgoing' / 'shared_logs' / 'supervisor.log'

# helper to append to supervisor log
def slog(msg: str) -> None:
    ts = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    line = f"[{ts}] {msg}\n"
    try:
        SUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        SUP_LOG.write_text((SUP_LOG.read_text(encoding='utf-8') if SUP_LOG.exists() else '') + line, encoding='utf-8')
    except Exception:
        print(line, end='')

# check if pid is running (cross-platform)
def pid_is_running(pid: int) -> bool:
    try:
        if sys.platform == 'win32':
            # tasklist
            p = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True)
            out = p.stdout or ''
            return str(pid) in out
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

# start a python script; return new pid or None
def start_script(script: str) -> int | None:
    try:
        # Use same python executable
        cmd = [sys.executable or 'python', '-u', str(script)]
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.2)
        return p.pid
    except Exception as e:
        slog(f"Failed to start {script}: {e}")
        return None

# emit evidence event by calling station_calyx.core.evidence.create_event and append_event
def emit_service_restarted(name: str, pid: int | None, script: str) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from station_calyx.core.evidence import create_event, append_event
        evt = create_event(
            event_type='SERVICE_RESTARTED',
            node_role='supervisor',
            summary=f'Service restarted: {name}',
            payload={'service': name, 'pid': pid, 'script': script},
            tags=['supervisor','service'],
            session_id=None,
        )
        append_event(evt)
    except Exception as e:
        slog(f"Could not emit SERVICE_RESTARTED event: {e}")

# load process list
def load_processes() -> List[Dict[str, Any]]:
    if not STATUS_FILE.exists():
        return []
    try:
        return json.loads(STATUS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []

# save process list
def save_processes(data: List[Dict[str, Any]]) -> None:
    try:
        STATUS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
    except Exception as e:
        slog(f"Failed to write processes.json: {e}")

# tail evidence
def tail_evidence(pos: int) -> int:
    if not EVIDENCE.exists():
        return pos
    try:
        with EVIDENCE.open('r', encoding='utf-8') as f:
            f.seek(pos)
            data = f.read()
            if data:
                slog(f"[evidence-tail]\n{data}")
            return f.tell()
    except Exception as e:
        slog(f"Failed to tail evidence: {e}")
        return pos

def main_loop():
    slog('Supervisor starting')
    last_pos = 0
    if EVIDENCE.exists():
        last_pos = EVIDENCE.stat().st_size
    while True:
        procs = load_processes()
        changed = False
        for entry in procs:
            name = entry.get('service')
            pid = entry.get('pid')
            script = entry.get('script')
            running = False
            if pid:
                try:
                    running = pid_is_running(int(pid))
                except Exception:
                    running = False
            if not running:
                slog(f"Service {name} (pid={pid}) not running; attempting restart of script {script}")
                newpid = start_script(script)
                entry['pid'] = newpid
                changed = True
                emit_service_restarted(name, newpid, script)
            else:
                slog(f"Service {name} (pid={pid}) running")
        if changed:
            save_processes(procs)
        # tail evidence
        last_pos = tail_evidence(last_pos)
        time.sleep(5)

if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        slog('Supervisor exiting on keyboard interrupt')
