#!/usr/bin/env python3
"""
Research Station Continuous Operation Launcher
Ensures autonomous agents stay operational 24/7
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def start_service(command, name):
    """Start a service and verify it's running"""
    try:
        # Check if already running
        result = subprocess.run(
            ["wsl", "bash", "-c", f"pgrep -af '{name}' || echo 'not_running'"],
            capture_output=True,
            text=True
        )
        if "not_running" not in result.stdout:
            print(f"[OK] {name} already running")
            return True
        
        # Start the service
        print(f"[START] Launching {name}...")
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", f"wsl bash -lc '{command}'"],
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Verify started
        time.sleep(3)
        result = subprocess.run(
            ["wsl", "bash", "-c", f"pgrep -af '{name}' || echo 'not_running'"],
            capture_output=True,
            text=True
        )
        
        if "not_running" not in result.stdout:
            print(f"[OK] {name} started successfully")
            return True
        else:
            print(f"[FAIL] {name} failed to start")
            return False
            
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False

def main():
    print("=" * 70)
    print("Research Station — Continuous Operation Startup")
    print("=" * 70)
    
    services = [
        (
            "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && "
            "python tools/agent_scheduler.py --interval 180 --auto-promote --promote-after 5 --cooldown-mins 30",
            "agent_scheduler"
        ),
        (
            "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && "
            "python tools/sys_integrator.py --interval 30",
            "sys_integrator"
        ),
        (
            "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && "
            "python tools/svf_probe.py --interval 5",
            "svf_probe"
        ),
        (
            "source ~/.calyx-venv/bin/activate && cd /mnt/c/Calyx_Terminal && "
            "python tools/triage_probe.py --interval 2 --probe-every 15",
            "triage_probe"
        ),
    ]
    
    started = 0
    for cmd, name in services:
        if start_service(cmd, name):
            started += 1
    
    print("=" * 70)
    print(f"Services started: {started}/{len(services)}")
    print("=" * 70)
    print("\nResearch Station is now operational.")
    print("Agents will receive continuous tasks for autonomous learning.")
    print("\nMonitor via:")
    print("  - live_heartbeat.html (live pulse monitoring)")
    print("  - system_dashboard.html (system overview)")
    print("\nPress Ctrl+C to keep services running and exit.")

if __name__ == "__main__":
    main()

