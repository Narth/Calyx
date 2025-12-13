#!/usr/bin/env python3
"""
Heartbeat Auto-Refresh Service
Regenerates the live heartbeat monitor every 3 seconds
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT_SCRIPT = ROOT / "tools" / "live_heartbeat_monitor.py"

def regenerate_heartbeat():
    """Run the heartbeat monitor generation script"""
    try:
        result = subprocess.run(
            [sys.executable, str(HEARTBEAT_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Heartbeat updated")
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Heartbeat Auto-Refresh Service")
    print("=" * 60)
    print(f"Regenerating heartbeat monitor every 3 seconds...")
    print(f"Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        while True:
            regenerate_heartbeat()
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[INFO] Heartbeat service stopped by user")
        return 0

if __name__ == "__main__":
    sys.exit(main())

