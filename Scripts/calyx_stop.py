#!/usr/bin/env python3
"""
Station Calyx Stop Script
=========================

Stops the Station Calyx service.

Usage:
    python scripts/calyx_stop.py

CONSTRAINTS:
- Does not force-kill unrelated processes
- Only stops Station Calyx service
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from station_calyx.core.service import stop_service, get_service_status


def main():
    print("\n" + "=" * 50)
    print("  STATION CALYX - STOP")
    print("=" * 50 + "\n")
    
    # Check current status
    status = get_service_status()
    
    if not status["running"]:
        print("[Status] Service is not running")
        return 0
    
    print(f"[Status] Service running (PID {status['pid']})")
    print("[Stop] Stopping service...")
    
    result = stop_service()
    
    if result["success"]:
        print(f"[Stop] {result['message']}")
        return 0
    else:
        print(f"[Error] {result['message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
