#!/usr/bin/env python3
"""
CP19 Auto-Halt - Phase 3
Monitors deployment metrics and triggers automatic halt/rollback
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

ROOT = Path(__file__).resolve().parents[1]


# Thresholds from CGPT blueprint
THRESHOLDS = {
    "tes_delta": {"warning": -2.0, "critical": -5.0},
    "error_rate": {"warning": 1.0, "critical": 2.0},
    "cpu_load": {"warning": 110.0, "critical": 120.0},
    "memory": {"warning": 90.0, "critical": 95.0},
    "lease_expiry": {"warning": 60, "critical": 0}
}


def check_thresholds(lease_id: str, metrics: Dict[str, float]) -> Tuple[str, Optional[str]]:
    """
    Check metrics against thresholds
    
    Args:
        lease_id: Lease ID
        metrics: Current metrics
        
    Returns:
        (status, reason)
    """
    alerts = []
    
    # Check TES delta
    tes_delta = metrics.get("tes_delta", 0)
    if tes_delta < THRESHOLDS["tes_delta"]["critical"]:
        alerts.append("CRITICAL: TES drop > 5%")
    elif tes_delta < THRESHOLDS["tes_delta"]["warning"]:
        alerts.append("WARNING: TES drop > 2%")
    
    # Check error rate
    error_rate = metrics.get("error_rate", 0)
    if error_rate > THRESHOLDS["error_rate"]["critical"]:
        alerts.append("CRITICAL: Error rate > 2%")
    elif error_rate > THRESHOLDS["error_rate"]["warning"]:
        alerts.append("WARNING: Error rate > 1%")
    
    # Check CPU load
    cpu_load = metrics.get("cpu_load", 0)
    if cpu_load > THRESHOLDS["cpu_load"]["critical"]:
        alerts.append("CRITICAL: CPU load > 120%")
    elif cpu_load > THRESHOLDS["cpu_load"]["warning"]:
        alerts.append("WARNING: CPU load > 110%")
    
    # Check memory
    memory = metrics.get("memory", 0)
    if memory > THRESHOLDS["memory"]["critical"]:
        alerts.append("CRITICAL: Memory > 95%")
    elif memory > THRESHOLDS["memory"]["warning"]:
        alerts.append("WARNING: Memory > 90%")
    
    if alerts:
        critical_alerts = [a for a in alerts if "CRITICAL" in a]
        if critical_alerts:
            return "HALT", " / ".join(critical_alerts)
        else:
            return "WARNING", " / ".join(alerts)
    
    return "OK", None


def should_halt(lease_id: str, metrics: Dict[str, float]) -> bool:
    """
    Determine if deployment should halt
    
    Args:
        lease_id: Lease ID
        metrics: Current metrics
        
    Returns:
        True if should halt
    """
    status, reason = check_thresholds(lease_id, metrics)
    return status == "HALT"


def main():
    parser = argparse.ArgumentParser(description="CP19 Auto-Halt Monitor")
    parser.add_argument("--lease", required=True, help="Lease ID")
    parser.add_argument("--tes-delta", type=float, default=0, help="TES delta")
    parser.add_argument("--error-rate", type=float, default=0, help="Error rate percent")
    parser.add_argument("--cpu-load", type=float, default=0, help="CPU load percent")
    parser.add_argument("--memory", type=float, default=0, help="Memory percent")
    
    args = parser.parse_args()
    
    metrics = {
        "tes_delta": args.tes_delta,
        "error_rate": args.error_rate,
        "cpu_load": args.cpu_load,
        "memory": args.memory
    }
    
    status, reason = check_thresholds(args.lease, metrics)
    
    print(f"Status: {status}")
    if reason:
        print(f"Reason: {reason}")
    
    should_halt_deployment = should_halt(args.lease, metrics)
    
    if should_halt_deployment:
        print("\nRECOMMENDATION: HALT deployment and initiate rollback")
        return 1
    else:
        print("\nStatus: OK to continue")
        return 0


if __name__ == "__main__":
    sys.exit(main())

