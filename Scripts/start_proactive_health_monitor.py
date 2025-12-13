#!/usr/bin/env python3
"""Start proactive health monitor as background service."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
sys.path.insert(0, str(ROOT.parent))

from tools.proactive_health_monitor import ProactiveHealthMonitor

def main():
    monitor = ProactiveHealthMonitor()
    
    print("[Proactive Health Monitor] Starting continuous monitoring...")
    print("Interval: 60 seconds")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            monitor.run_health_check()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[Proactive Health Monitor] Stopped")

if __name__ == "__main__":
    main()

