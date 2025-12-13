#!/usr/bin/env python3
"""
Station Calyx Start Script
==========================

Validates environment and starts the Station Calyx service.

Usage:
    python scripts/calyx_start.py [--background]
    python scripts/calyx_start.py --help

CONSTRAINTS:
- No auto-start on boot
- User-invoked only
- Explicit start command required
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from station_calyx.core.service import start_service, get_service_status
from station_calyx.core.doctor import run_all_checks, format_doctor_report
from station_calyx.core.onboarding import is_first_run, present_onboarding


def main():
    parser = argparse.ArgumentParser(
        description="Start Station Calyx service",
        epilog="Station Calyx: Advisory-only. Does not execute. Does not initiate actions.",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Run in background mode",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8420,
        help="Port to listen on (default: 8420)",
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip health checks before starting",
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("  STATION CALYX")
    print("  Advisory-only system monitor")
    print("=" * 50 + "\n")
    
    # First-run onboarding
    if is_first_run():
        print("[First Run] Generating onboarding documentation...")
        content = present_onboarding()
        print("[First Run] See: station_calyx/data/onboarding.md")
        print()
    
    # Check current status
    status = get_service_status()
    if status["running"]:
        print(f"[Status] Service already running (PID {status['pid']})")
        print(f"[Status] Stop with: python scripts/calyx_stop.py")
        return 0
    
    # Run health checks
    if not args.skip_checks:
        print("[Doctor] Running health checks...")
        results = run_all_checks()
        
        if not results["healthy"]:
            print(format_doctor_report(results))
            print("[Doctor] Fix issues before starting, or use --skip-checks")
            return 1
        
        print(f"[Doctor] All {results['total']} checks passed")
        print()
    
    # Start service
    mode = "background" if args.background else "foreground"
    print(f"[Start] Starting service in {mode} mode...")
    print(f"[Start] Host: {args.host}")
    print(f"[Start] Port: {args.port}")
    print()
    
    result = start_service(
        host=args.host,
        port=args.port,
        background=args.background,
    )
    
    if result["success"]:
        if args.background:
            print(f"[Start] {result['message']}")
            print(f"[Start] API: {result.get('url', 'http://' + args.host + ':' + str(args.port))}")
            print(f"[Start] Stop with: python scripts/calyx_stop.py")
        # Foreground mode runs until interrupted
        return 0
    else:
        print(f"[Error] {result['message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
