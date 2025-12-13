#!/usr/bin/env python3
"""Stop existing autonomy_runner (if running) and start a new 4-hour runner.

This script uses taskkill to stop existing runner pid read from
outgoing/autonomy_runner.lock and launches a detached new runner process
using subprocess on Windows.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'outgoing' / 'autonomy_runner.lock'

def stop_existing():
    try:
        if not LOCK.exists():
            print('No existing runner lock found')
            return
        data = json.loads(LOCK.read_text(encoding='utf-8'))
        pid = data.get('pid')
        if not pid:
            print('No pid in lock')
            return
        print('Stopping existing runner pid', pid)
        proc = subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, text=True)
        print('taskkill rc=', proc.returncode)
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
    except Exception as e:
        print('Error stopping existing runner:', e)

def start_new():
    try:
        cmd = [sys.executable, '-u', str(ROOT / 'tools' / 'autonomy_runner_5h.py'), '--duration', '14400', '--interval', '60']
        # DETACHED_PROCESS flag so it keeps running
        DETACHED_PROCESS = 0x00000008
        proc = subprocess.Popen(cmd, creationflags=DETACHED_PROCESS)
        print('Started new runner pid', proc.pid)
    except Exception as e:
        print('Error starting new runner:', e)

if __name__ == '__main__':
    stop_existing()
    start_new()
