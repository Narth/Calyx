#!/usr/bin/env python3
"""
TES Tracker Scheduler - Automatically run granular TES tracking
Runs every 6 hours to generate performance reports without user intervention
"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    """Run TES tracker scheduler"""
    interval_hours = 6
    interval_seconds = interval_hours * 3600
    
    tracker_script = ROOT / "tools" / "granular_tes_tracker.py"
    
    print(f"[INFO] TES Tracker Scheduler started")
    print(f"[INFO] Running tracker every {interval_hours} hours")
    print(f"[INFO] First run in 5 minutes...")
    
    time.sleep(300)  # Wait 5 minutes for initial data collection
    
    while True:
        try:
            print(f"\n[TRACKER] Running granular TES tracker...")
            result = subprocess.run(
                [sys.executable, str(tracker_script)],
                cwd=str(ROOT),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[TRACKER] Success")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"[TRACKER] Warning: Exit code {result.returncode}")
                if result.stderr:
                    print(result.stderr)
            
            print(f"[TRACKER] Next run in {interval_hours} hours")
            
        except KeyboardInterrupt:
            print("\n[INFO] Scheduler stopped by user")
            break
        except Exception as e:
            print(f"[ERROR] Tracker failed: {e}")
        
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()

