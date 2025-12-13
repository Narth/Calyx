#!/usr/bin/env python3
"""
CP19 Resource Sentinel - Phase 2
Monitor and enforce resource quotas for sandbox execution
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASES_DIR = ROOT / "outgoing" / "leases"
STAGING_RUNS_DIR = ROOT / "outgoing" / "staging_runs"
ALERTS_DIR = ROOT / "logs" / "resource_monitoring"


def check_lease_resources(lease_id: str) -> dict:
    """
    Check resource usage for lease
    
    Returns:
        Resource status dictionary
    """
    lease_file = LEASES_DIR / f"{lease_id}.json"
    if not lease_file.exists():
        return {"status": "lease_not_found"}
    
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    
    # Get run artifacts
    run_dir = STAGING_RUNS_DIR / lease_id
    if not run_dir.exists():
        return {"status": "not_started"}
    
    meta_file = run_dir / "meta.json"
    if not meta_file.exists():
        return {"status": "in_progress"}
    
    meta = json.loads(meta_file.read_text())
    
    # Check against limits
    limits = lease["limits"]
    duration = meta.get("duration_s", 0)
    
    status = {
        "lease_id": lease_id,
        "duration_s": duration,
        "duration_limit_s": limits["wallclock_timeout_s"],
        "exit_code": meta.get("exit_code", "unknown"),
        "status": "within_limits"
    }
    
    # Check timeout
    if duration > limits["wallclock_timeout_s"]:
        status["status"] = "timeout_exceeded"
        status["violation"] = "wallclock_timeout"
    
    return status


def monitor_active_leases() -> list:
    """Monitor all active leases"""
    results = []
    
    if not LEASES_DIR.exists():
        return results
    
    for lease_file in LEASES_DIR.glob("LEASE-*.json"):
        lease_id = lease_file.stem
        status = check_lease_resources(lease_id)
        results.append(status)
    
    return results


def log_alert(lease_id: str, violation_type: str, details: dict):
    """Log resource violation alert"""
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    
    alert = {
        "timestamp": time.time(),
        "lease_id": lease_id,
        "violation_type": violation_type,
        "details": details
    }
    
    alert_file = ALERTS_DIR / f"{lease_id}_{violation_type}.json"
    alert_file.write_text(json.dumps(alert, indent=2))


def main():
    parser = argparse.ArgumentParser(description="CP19 Resource Sentinel")
    parser.add_argument("--lease-id", help="Check specific lease")
    parser.add_argument("--monitor", action="store_true", help="Monitor all active leases")
    
    args = parser.parse_args()
    
    if args.lease_id:
        status = check_lease_resources(args.lease_id)
        print(json.dumps(status, indent=2))
    elif args.monitor:
        results = monitor_active_leases()
        print(f"Monitoring {len(results)} leases")
        for result in results:
            print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

