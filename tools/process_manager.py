#!/usr/bin/env python3
"""
Process Manager for Station Calyx

Manages process lifecycle, prevents duplicates, and cleans up stale processes.

Usage:
  python tools/process_manager.py --status
  python tools/process_manager.py --cleanup
  python tools/process_manager.py --kill-duplicates
"""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "state" / "process_manager_state.json"


def get_python_processes() -> List[Dict]:
    """Get all Python processes with command line"""
    processes = []
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-CimInstance Win32_Process | Where-Object {$_.Name -eq "python.exe"} | Select-Object ProcessId, CommandLine | ConvertTo-Json'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            if isinstance(data, list):
                processes = data
            else:
                processes = [data]
    except Exception as e:
        print(f"[ERROR] Failed to get processes: {e}")
    
    return processes


def get_unique_process_signatures() -> Dict[str, List[Dict]]:
    """Group processes by signature (script being run)"""
    processes = get_python_processes()
    signatures = {}
    
    for proc in processes:
        cmdline = proc.get('CommandLine', '')
        if not cmdline:
            continue
        
        # Extract the main script/command being run
        signature = None
        if 'cbo_overseer.py' in cmdline:
            signature = 'cbo_overseer'
        elif 'bridge_pulse_scheduler.py' in cmdline:
            signature = 'bridge_pulse_scheduler'
        elif 'uptime_tracker.py' in cmdline:
            signature = 'uptime_tracker'
        elif 'production_monitor.py' in cmdline:
            signature = 'production_monitor'
        elif 'ai4all_teaching.py' in cmdline:
            signature = 'ai4all_teaching'
        elif 'svc_supervisor' in cmdline:
            signature = 'svc_supervisor'
        elif 'svf_probe.py' in cmdline:
            signature = 'svf_probe'
        elif 'triage_probe.py' in cmdline:
            signature = 'triage_probe'
        elif 'sys_integrator.py' in cmdline:
            signature = 'sys_integrator'
        elif 'cp6_sociologist.py' in cmdline:
            signature = 'cp6'
        elif 'cp7_chronicler.py' in cmdline:
            signature = 'cp7'
        elif 'agent_cp8.py' in cmdline:
            signature = 'cp8'
        elif 'agent_cp9.py' in cmdline:
            signature = 'cp9'
        elif 'agent_cp10.py' in cmdline:
            signature = 'cp10'
        
        if signature:
            if signature not in signatures:
                signatures[signature] = []
            signatures[signature].append(proc)
    
    return signatures


def kill_process(pid: int) -> bool:
    """Kill a process by PID"""
    try:
        subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                      capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def should_be_singleton(signature: str) -> bool:
    """Check if a process type should only have one instance"""
    singletons = [
        'cbo_overseer',
        'bridge_pulse_scheduler',
        'uptime_tracker',
        'production_monitor',
        'ai4all_teaching',
        'svc_supervisor'
    ]
    return signature in singletons


def cleanup_duplicates() -> int:
    """Kill duplicate singleton processes"""
    signatures = get_unique_process_signatures()
    killed = 0
    
    for signature, procs in signatures.items():
        if should_be_singleton(signature) and len(procs) > 1:
            print(f"[WARN] Found {len(procs)} instances of {signature}")
            
            # Keep the first one, kill the rest
            for proc in procs[1:]:
                pid = proc.get('ProcessId')
                if pid:
                    print(f"[INFO] Killing duplicate {signature} PID {pid}")
                    if kill_process(pid):
                        killed += 1
                        time.sleep(0.5)
    
    return killed


def show_status():
    """Show current process status"""
    signatures = get_unique_process_signatures()
    
    print("\n[PROCESS STATUS]")
    print("=" * 60)
    
    for signature, procs in sorted(signatures.items()):
        count = len(procs)
        status = "[OK]" if count == 1 else "[WARN] MULTIPLE" if should_be_singleton(signature) else "[OK]"
        
        print(f"{status} {signature}: {count} instance(s)")
        
        for proc in procs:
            pid = proc.get('ProcessId', 'unknown')
            cmdline = proc.get('CommandLine', '')
            # Truncate long command lines
            if len(cmdline) > 80:
                cmdline = cmdline[:77] + "..."
            print(f"   PID {pid}: {cmdline}")
    
    print("=" * 60)
    
    # Check for duplicates
    duplicates = sum(1 for sig, procs in signatures.items() 
                    if should_be_singleton(sig) and len(procs) > 1)
    
    if duplicates > 0:
        print(f"\n[WARN] Found {duplicates} process type(s) with duplicates")
        print("[INFO] Run --kill-duplicates to clean up")
    else:
        print("\n[OK] No duplicate singleton processes detected")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Process Manager")
    ap.add_argument("--status", action="store_true", help="Show process status")
    ap.add_argument("--cleanup", action="store_true", help="Clean up stale processes")
    ap.add_argument("--kill-duplicates", action="store_true", help="Kill duplicate singleton processes")
    
    args = ap.parse_args(argv)
    
    if args.status:
        show_status()
        return 0
    
    if args.kill_duplicates:
        killed = cleanup_duplicates()
        print(f"\n[INFO] Killed {killed} duplicate process(es)")
        if killed > 0:
            time.sleep(2)
            show_status()
        return 0
    
    if args.cleanup:
        # TODO: Implement stale process cleanup
        print("[INFO] Cleanup not yet implemented")
        return 0
    
    # Default to status
    show_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

