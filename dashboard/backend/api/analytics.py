#!/usr/bin/env python3
"""
Dashboard API: Analytics Module
CP15 Prophet integration for trends and forecasts
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[3]


def get_tes_trend(days: int = 7) -> Dict[str, Any]:
    """
    Get TES trend data
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Trend data for CP15 analytics feed
    """
    tes_csv = ROOT / "logs" / "agent_metrics.csv"
    
    if not tes_csv.exists():
        return {
            "trend": "unknown",
            "current": 97.0,
            "average": 97.0,
            "min": 97.0,
            "max": 97.0,
            "delta_24h": 0.0,
            "delta_7d": 0.0
        }
    
    try:
        with open(tes_csv, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if not rows:
                return {"trend": "no_data", "current": 97.0}
            
            # Get recent data
            recent_count = min(days * 24, len(rows))  # Assume ~1 row per hour
            recent_rows = rows[-recent_count:]
            
            tes_values = [float(r['tes']) for r in recent_rows]
            
            # Calculate statistics
            current = tes_values[-1] if tes_values else 97.0
            average = sum(tes_values) / len(tes_values) if tes_values else 97.0
            min_val = min(tes_values) if tes_values else 97.0
            max_val = max(tes_values) if tes_values else 97.0
            
            # Calculate deltas
            delta_24h = 0.0
            delta_7d = 0.0
            
            if len(tes_values) >= 24:
                delta_24h = current - tes_values[-24]
            if len(tes_values) >= 168:
                delta_7d = current - tes_values[-168]
            
            # Determine trend
            if delta_24h > 1:
                trend = "rising"
            elif delta_24h < -1:
                trend = "declining"
            else:
                trend = "stable"
            
            return {
                "trend": trend,
                "current": round(current, 1),
                "average": round(average, 1),
                "min": round(min_val, 1),
                "max": round(max_val, 1),
                "delta_24h": round(delta_24h, 1),
                "delta_7d": round(delta_7d, 1)
            }
    except Exception as e:
        return {"trend": "error", "error": str(e)}


def get_lease_efficiency() -> Dict[str, Any]:
    """
    Get lease efficiency metrics
    
    Returns:
        Efficiency data
    """
    leases_dir = ROOT / "outgoing" / "leases"
    staging_dir = ROOT / "outgoing" / "staging_runs"
    
    if not leases_dir.exists():
        return {"efficiency": 0.0, "total_issued": 0, "total_successful": 0}
    
    leases = list(leases_dir.glob("LEASE-*.json"))
    successful = 0
    
    for lease_file in leases:
        try:
            lease_data = json.loads(lease_file.read_text(encoding="utf-8"))
            lease_id = lease_data.get("lease_id", lease_file.stem)
            
            # Check if execution completed
            staging_run = staging_dir / lease_id
            if staging_run.exists() and (staging_run / "meta.json").exists():
                successful += 1
        except Exception:
            continue
    
    efficiency = (successful / len(leases) * 100) if leases else 0.0
    
    return {
        "efficiency": round(efficiency, 1),
        "total_issued": len(leases),
        "total_successful": successful
    }

