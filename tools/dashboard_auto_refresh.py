#!/usr/bin/env python3
"""
Dashboard Auto-Refresh Service
Continuously regenerates the dashboard HTML every 30 seconds
Run this in the background to keep the dashboard up-to-date
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_SCRIPT = ROOT / "tools" / "create_dashboard.py"

def regenerate_dashboard():
    """Run the dashboard generation script"""
    try:
        result = subprocess.run(
            [sys.executable, str(DASHBOARD_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Dashboard regenerated successfully")
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Dashboard generation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error regenerating dashboard: {e}")
        return False

def main():
    print("=" * 60)
    print("Dashboard Auto-Refresh Service")
    print("=" * 60)
    print(f"Regenerating dashboard every 30 seconds...")
    print(f"Press Ctrl+C to stop")
    print("=" * 60)
    
    cycle = 0
    try:
        while True:
            cycle += 1
            regenerate_dashboard()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n[INFO] Auto-refresh service stopped by user")
        return 0

if __name__ == "__main__":
    sys.exit(main())

