#!/usr/bin/env python3
"""
Bridge Pulse Scheduler

Automatically generates Bridge Pulse Reports every 4-6 system pulses
(CBO pulses every 4 minutes, so this runs every 16-24 minutes).

Usage:
  python tools/bridge_pulse_scheduler.py [--pulse-interval 20] [--output reports/]
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
STATE_FILE = ROOT / "state" / "bridge_pulse_state.json"
REPORTS_DIR = ROOT / "reports"


def read_state() -> dict:
    """Read scheduler state"""
    try:
        with STATE_FILE.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'last_pulse_id': 0, 'next_pulse_due': time.time()}


def write_state(state: dict) -> None:
    """Write scheduler state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with STATE_FILE.open('w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def generate_pulse_report(pulse_id: int) -> bool:
    """Generate a bridge pulse report"""
    try:
        import subprocess
        cmd = [
            sys.executable,
            str(ROOT / "tools" / "bridge_pulse_generator.py"),
            "--report-id", f"bp-{pulse_id:04d}",
            "--output", str(REPORTS_DIR)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"[OK] Bridge Pulse Report bp-{pulse_id:04d} generated")
            return True
        else:
            print(f"[ERROR] Failed to generate report: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception generating report: {e}")
        return False


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Bridge Pulse Scheduler")
    ap.add_argument("--pulse-interval", type=int, default=20, 
                    help="Interval in minutes between pulse reports (default: 20)")
    ap.add_argument("--max-iters", type=int, default=0,
                    help="Optional: stop after N pulses (0 = run forever)")
    
    args = ap.parse_args(argv)
    
    # Setup signal handlers
    stopping = False
    
    def signal_handler(signum, frame):
        nonlocal stopping
        stopping = True
        print("\n[INFO] Bridge Pulse Scheduler stopping...")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    state = read_state()
    pulse_id = state.get('last_pulse_id', 0)
    interval_sec = args.pulse_interval * 60
    
    print(f"[INFO] Bridge Pulse Scheduler started")
    print(f"[INFO] Pulse interval: {args.pulse_interval} minutes")
    print(f"[INFO] Starting from pulse bp-{pulse_id+1:04d}")
    
    iter_count = 0
    
    try:
        while not stopping:
            now = time.time()
            next_due = state.get('next_pulse_due', now)
            
            if now >= next_due:
                pulse_id += 1
                print(f"\n[PULSE] Generating pulse report bp-{pulse_id:04d} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                success = generate_pulse_report(pulse_id)
                
                # Update state
                state['last_pulse_id'] = pulse_id
                state['next_pulse_due'] = now + interval_sec
                state['last_generated'] = datetime.now().isoformat()
                state['success'] = success
                write_state(state)
                
                iter_count += 1
                if args.max_iters and iter_count >= args.max_iters:
                    print(f"[INFO] Reached max iterations ({args.max_iters})")
                    break
            
            # Sleep for 30 seconds before checking again
            time.sleep(30)
            
    except KeyboardInterrupt:
        pass
    
    print(f"[INFO] Bridge Pulse Scheduler stopped")
    print(f"[INFO] Total pulses generated: {pulse_id}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

