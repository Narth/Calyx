#!/usr/bin/env python3
"""
Uptime Tracker

Continuously records system snapshots to logs/system_snapshots.jsonl
for uptime calculation and system health monitoring.

Usage:
  python tools/uptime_tracker.py [--interval 60] [--max-iters 0]
"""

from __future__ import annotations
import argparse
import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS_FILE = ROOT / "logs" / "system_snapshots.jsonl"
OUTGOING = ROOT / "outgoing"
LOCK_PATH = OUTGOING / "uptime_tracker.lock"


def get_system_snapshot() -> dict:
    """Collect current system snapshot"""
    now = time.time()
    snapshot = {
        'ts': now,
        'iso_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
        'timestamp': datetime.now().isoformat(),
        'cpu_pct': 0.0,
        'ram_pct': 0.0,
        'python_processes': [],
        'count': 0,
        'phase': 'monitoring'
    }
    
    try:
        import psutil
        
        # CPU and memory
        snapshot['cpu_pct'] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        snapshot['ram_pct'] = mem.percent
        
        # Python processes
        python_procs = []
        agent_patterns = ['agent', 'triage', 'cp', 'svf', 'bridge', 'scheduler', 'navigator', 'sysint']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                info = proc.info
                name = (info.get('name') or '').lower()
                if name not in ('python.exe', 'python'):
                    continue
                
                cmdline = info.get('cmdline') or []
                cmd_str = ' '.join(cmdline).lower()
                should_track = False
                
                # Check if it's a Calyx process
                if cmd_str and any(pattern in cmd_str for pattern in agent_patterns):
                    should_track = True
                elif not cmd_str:
                    # Fallback: if cmdline is unavailable (permission issues), still treat
                    # python processes as Calyx-managed since we rarely run other Python apps
                    should_track = True
                
                if should_track:
                    python_procs.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cmdline': cmdline
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        snapshot['python_processes'] = python_procs
        snapshot['count'] = len(python_procs)
        
    except ImportError:
        snapshot['ram_pct'] = 0.0
    
    return snapshot


def write_snapshot(snapshot: dict) -> None:
    """Write snapshot to JSONL file"""
    SNAPSHOTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTGOING.mkdir(parents=True, exist_ok=True)
    
    try:
        with SNAPSHOTS_FILE.open('a', encoding='utf-8') as f:
            f.write(json.dumps(snapshot) + '\n')
        # Write/update lock heartbeat for supervision.
        try:
            LOCK_PATH.write_text(
                json.dumps(
                    {
                        "ts": snapshot.get("ts") or time.time(),
                        "iso": snapshot.get("iso_utc") or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        "ok": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass
    except Exception as e:
        print(f"[ERROR] Failed to write snapshot: {e}")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Uptime Tracker")
    ap.add_argument("--interval", type=int, default=60,
                    help="Snapshot interval in seconds (default: 60)")
    ap.add_argument("--max-iters", type=int, default=0,
                    help="Optional: stop after N snapshots (0 = run forever)")
    
    args = ap.parse_args(argv)
    
    # Setup signal handlers
    stopping = False
    
    def signal_handler(signum, frame):
        nonlocal stopping
        stopping = True
        print("\n[INFO] Uptime Tracker stopping...")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print(f"[INFO] Uptime Tracker started")
    print(f"[INFO] Snapshot interval: {args.interval} seconds")
    print(f"[INFO] Output: {SNAPSHOTS_FILE}")
    
    iter_count = 0
    
    try:
        while not stopping:
            snapshot = get_system_snapshot()
            write_snapshot(snapshot)
            
            print(f"[SNAPSHOT] {snapshot['timestamp']} - {snapshot['count']} processes, "
                  f"CPU: {snapshot['cpu_pct']:.1f}%, RAM: {snapshot['ram_pct']:.1f}%")
            
            iter_count += 1
            if args.max_iters and iter_count >= args.max_iters:
                print(f"[INFO] Reached max iterations ({args.max_iters})")
                break
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        pass
    
    print(f"[INFO] Uptime Tracker stopped")
    print(f"[INFO] Total snapshots recorded: {iter_count}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

