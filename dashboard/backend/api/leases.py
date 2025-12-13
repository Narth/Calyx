#!/usr/bin/env python3
"""
Dashboard API: Leases Module
Phase A - Backend Skeleton
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[3]


def list_active_leases() -> List[Dict[str, Any]]:
    """
    List active leases
    
    Returns:
        Active lease list
    """
    leases = []
    leases_dir = ROOT / "outgoing" / "leases"
    
    if not leases_dir.exists():
        return leases
    
    for lease_file in sorted(leases_dir.glob("LEASE-*.json"), reverse=True):
        try:
            lease_data = json.loads(lease_file.read_text(encoding="utf-8"))
            
            # Check expiration
            expires_at = lease_data.get("expires_at", "")
            if expires_at:
                exp_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if exp_dt < datetime.now(timezone.utc):
                    continue
            
            # Get cosigners
            cosigners = lease_data.get("cosigners", [])
            human_signed = any(c.get("role") == "human" for c in cosigners)
            agent_signed = any(c.get("role") == "agent" for c in cosigners)
            
            leases.append({
                "lease_id": lease_data.get("lease_id", lease_file.stem),
                "intent_id": lease_data.get("intent_id", "unknown"),
                "status": "active",
                "issued_at": lease_data.get("issued_at", ""),
                "expires_at": expires_at,
                "time_remaining_s": int((exp_dt - datetime.now(timezone.utc)).total_seconds()) if expires_at else 0,
                "cosigners": {
                    "human": {
                        "id": next((c.get("id") for c in cosigners if c.get("role") == "human"), ""),
                        "signed": human_signed,
                        "signed_at": next((c.get("timestamp") for c in cosigners if c.get("role") == "human"), "")
                    },
                    "agent": {
                        "id": next((c.get("id") for c in cosigners if c.get("role") == "agent"), ""),
                        "signed": agent_signed,
                        "signed_at": next((c.get("timestamp") for c in cosigners if c.get("role") == "agent"), "")
                    }
                },
                "execution": {
                    "canary_tier": 5,
                    "health_status": "passing",
                    "metrics": {
                        "tes_delta": 0.0,
                        "error_rate": 0.0,
                        "duration_s": 0.0
                    }
                }
            })
        except Exception:
            continue
    
    return leases


def get_lease_status(lease_id: str) -> Dict[str, Any]:
    """
    Get detailed lease status
    
    Args:
        lease_id: Lease identifier
        
    Returns:
        Lease status details
    """
    # TODO: Implement actual lease status retrieval
    return {}


def approve_lease(lease_id: str, human_id: str, reason: str = "") -> bool:
    """
    Approve a lease
    
    Args:
        lease_id: Lease identifier
        human_id: Human identifier
        reason: Approval reason
        
    Returns:
        True if successful
    """
    # TODO: Implement actual approval logic
    return True

