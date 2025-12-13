#!/usr/bin/env python3
"""
Dashboard API: Approvals Module
Phase A - Backend Skeleton
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[3]


def list_pending_approvals() -> List[Dict[str, Any]]:
    """
    List pending approvals
    
    Returns:
        Pending approval list from CP14 and pending_approvals.json
    """
    approvals = []
    
    # Check for active leases needing human cosignature
    leases_dir = ROOT / "outgoing" / "leases"
    if leases_dir.exists():
        for lease_file in sorted(leases_dir.glob("LEASE-*.json"), reverse=True):
            try:
                lease_data = json.loads(lease_file.read_text(encoding="utf-8"))
                cosigners = lease_data.get("cosigners", [])
                
                # Check if human cosignature needed
                human_signed = any(c.get("role") == "human" for c in cosigners)
                agent_signed = any(c.get("role") == "agent" for c in cosigners)
                
                # Only show if missing human OR missing agent cosignature
                # AND check if hasn't been approved already (check for user1 signature)
                user1_signed = any(c.get("id") == "user1" for c in cosigners)
                
                if not user1_signed and (not human_signed or not agent_signed):
                    approvals.append({
                        "approval_id": f"APP-{lease_data.get('lease_id', 'UNKNOWN')}",
                        "lease_id": lease_data.get("lease_id", "unknown"),
                        "intent_id": lease_data.get("intent_id", "unknown"),
                        "type": "cosignature",
                        "status": "pending",
                        "requested_at": lease_data.get("issued_at", datetime.now(timezone.utc).isoformat()),
                        "expires_at": lease_data.get("expires_at", ""),
                        "priority": "medium",
                        "details": {
                            "reason": "Two-key governance requires human approval",
                            "risk_level": "low",
                            "canary_plan": "5% → 25% → 100%",
                            "agent_approval": "CP14" if agent_signed else "pending"
                        }
                    })
            except Exception:
                continue
    
    return approvals


def approve_request(approval_id: str) -> bool:
    """
    Approve a request
    
    Args:
        approval_id: Approval identifier
        
    Returns:
        True if successful
    """
    try:
        # Extract lease_id from approval_id (format: APP-LEASE-YYYYMMDD-HHMMSS)
        lease_id = approval_id.replace('APP-', '')
        lease_file = ROOT / "outgoing" / "leases" / f"{lease_id}.json"
        
        if not lease_file.exists():
            return False
        
        # Read lease data
        lease_data = json.loads(lease_file.read_text(encoding="utf-8"))
        
        # Add human cosignature
        cosigners = lease_data.get("cosigners", [])
        human_cosigner = {
            "role": "human",
            "id": "user1",
            "sig": "human_approval_signature",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        cosigners.append(human_cosigner)
        lease_data["cosigners"] = cosigners
        
        # Write back
        lease_file.write_text(json.dumps(lease_data, indent=2), encoding="utf-8")
        
        return True
    except Exception as e:
        print(f"Error approving request: {e}")
        return False


def reject_request(approval_id: str, reason: str) -> bool:
    """
    Reject a request
    
    Args:
        approval_id: Approval identifier
        reason: Rejection reason
        
    Returns:
        True if successful
    """
    try:
        # Log rejection
        rejection_file = ROOT / "outgoing" / "approvals" / f"{approval_id}.rejected.json"
        rejection_file.parent.mkdir(parents=True, exist_ok=True)
        
        rejection_data = {
            "approval_id": approval_id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": "user1",
            "reason": reason
        }
        
        rejection_file.write_text(json.dumps(rejection_data, indent=2), encoding="utf-8")
        
        return True
    except Exception as e:
        print(f"Error rejecting request: {e}")
        return False

