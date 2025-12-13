#!/usr/bin/env python3
"""
Dashboard API: Health Module
Phase A - Backend Skeleton
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[3]


def get_current_health() -> Dict[str, Any]:
    """
    Get current system health metrics
    
    Returns:
        Current health data from CP19 and CBO lock
    """
    import psutil
    import csv
    
    # Get real CPU and RAM from system
    cpu_pct = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get TES from agent metrics
    tes_current = 97.0
    tes_delta_24h = 0.0
    tes_delta_7d = 0.0
    
    try:
        tes_csv = ROOT / "logs" / "agent_metrics.csv"
        if tes_csv.exists():
            with open(tes_csv, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    tes_values = [float(r['tes']) for r in rows[-50:]]
                    tes_current = tes_values[-1] if tes_values else 97.0
                    if len(tes_values) >= 24:
                        tes_delta_24h = tes_current - tes_values[-24]
                    if len(tes_values) >= 168:
                        tes_delta_7d = tes_current - tes_values[-168]
    except Exception:
        pass
    
    # Get phases from capability matrix
    phases = {"phase0": "idle", "phase1": "idle", "phase2": "idle", "phase3": "idle"}
    try:
        cap_matrix = ROOT / "outgoing" / "policies" / "capability_matrix.yaml"
        if cap_matrix.exists():
            import yaml
            with open(cap_matrix, 'r') as f:
                matrix = yaml.safe_load(f)
                for phase in ["phase0", "phase1", "phase2", "phase3"]:
                    if phase in matrix.get("phases", {}):
                        status = matrix["phases"][phase].get("status", "idle")
                        phases[phase] = "active" if status == "implemented" else "idle"
    except Exception:
        pass
    
    # Determine pressure levels
    def get_pressure(pct):
        if pct >= 85:
            return "high"
        elif pct >= 70:
            return "medium"
        return "low"
    
    tes_pressure = get_pressure(100 - tes_current)  # Invert for TES
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {
            "usage_pct": round(cpu_pct, 1),
            "throttling": cpu_pct > 90,
            "cores": psutil.cpu_count()
        },
        "ram": {
            "usage_pct": round(mem.percent, 1),
            "used_mb": round(mem.used / (1024**2), 0),
            "available_mb": round(mem.available / (1024**2), 0),
            "total_mb": round(mem.total / (1024**2), 0)
        },
        "disk": {
            "usage_pct": round(disk.percent, 1),
            "free_pct": round(100 - disk.percent, 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "total_gb": round(disk.total / (1024**3), 1)
        },
        "tes": {
            "current": round(tes_current, 1),
            "delta_24h": round(tes_delta_24h, 1),
            "delta_7d": round(tes_delta_7d, 1),
            "trend": "rising" if tes_delta_24h > 0 else "stable" if tes_delta_24h == 0 else "declining"
        },
        "network": {
            "status": "closed",
            "last_check": datetime.now(timezone.utc).isoformat()
        },
        "phases": phases,
        "pressure_heatmap": {
            "cpu": get_pressure(cpu_pct),
            "ram": get_pressure(mem.percent),
            "disk": get_pressure(disk.percent),
            "network": "low",
            "tes": tes_pressure
        }
    }


def get_health_history(range_param: str) -> list[Dict[str, Any]]:
    """
    Get historical health data
    
    Args:
        range_param: Time range (1h, 24h, 7d)
        
    Returns:
        Historical data array
    """
    # TODO: Implement actual historical data retrieval
    return []


def get_pressure_heatmap() -> Dict[str, str]:
    """
    Get resource pressure heatmap
    
    Returns:
        Pressure data
    """
    # TODO: Implement actual CP19 integration
    return {
        "cpu": "high",
        "ram": "medium",
        "disk": "low",
        "network": "low",
        "tes": "low"
    }

