#!/usr/bin/env python3
"""
Phase 3: User Notification System
Alerts user when approvals are needed without blocking system
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
NOTIFICATIONS_FILE = ROOT / "outgoing" / "pending_approvals.json"


def create_approval_request(intent_id: str, lease_id: str, request_type: str, 
                           details: Dict[str, Any]) -> None:
    """
    Create a notification for user approval
    
    Args:
        intent_id: Intent ID
        lease_id: Lease ID
        request_type: Type of request (cosignature, promotion, etc.)
        details: Request details
    """
    notification = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intent_id": intent_id,
        "lease_id": lease_id,
        "request_type": request_type,
        "status": "pending",
        "details": details,
        "action_required": True
    }
    
    # Load existing notifications
    if NOTIFICATIONS_FILE.exists():
        notifications = json.loads(NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
    else:
        notifications = []
    
    # Add new notification
    notifications.append(notification)
    
    # Save
    NOTIFICATIONS_FILE.write_text(json.dumps(notifications, indent=2), encoding="utf-8")
    
    # Create alert file
    alert_file = ROOT / "outgoing" / "APPROVAL_NEEDED.flag"
    alert_file.write_text(json.dumps(notification, indent=2), encoding="utf-8")
    
    print(f"APPROVAL REQUEST CREATED: {request_type}")
    print(f"Intent: {intent_id}")
    print(f"Lease: {lease_id}")
    print(f"Check: outgoing/APPROVAL_NEEDED.flag")


def list_pending_approvals() -> List[Dict[str, Any]]:
    """List all pending approvals"""
    if not NOTIFICATIONS_FILE.exists():
        return []
    
    notifications = json.loads(NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
    return [n for n in notifications if n.get("status") == "pending"]


def approve_request(lease_id: str, human_id: str = "user1") -> bool:
    """
    Approve a pending request
    
    Args:
        lease_id: Lease ID to approve
        human_id: Human identifier
        
    Returns:
        True if successful
    """
    if not NOTIFICATIONS_FILE.exists():
        print("No pending approvals")
        return False
    
    notifications = json.loads(NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
    
    # Find matching request
    for notification in notifications:
        if notification.get("lease_id") == lease_id and notification.get("status") == "pending":
            # Execute approval based on type
            request_type = notification.get("request_type")
            
            if request_type == "cosignature":
                # Add human cosignature
                try:
                    import subprocess
                    result = subprocess.run(
                        ["python", "tools/phase3_cosignature.py", "--lease", 
                         f"outgoing/leases/{lease_id}.json", "--add", "--role", "human",
                         "--id", human_id, "--sig", f"approved_{datetime.now().isoformat()}"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        notification["status"] = "approved"
                        notification["approved_by"] = human_id
                        notification["approved_at"] = datetime.now(timezone.utc).isoformat()
                        print(f"Approved: {lease_id}")
                except Exception as e:
                    print(f"ERROR: Failed to approve: {e}")
                    return False
            
            elif request_type == "promotion":
                # Approve promotion to next tier
                notification["status"] = "approved"
                notification["approved_by"] = human_id
                notification["approved_at"] = datetime.now(timezone.utc).isoformat()
                print(f"Promotion approved: {lease_id}")
            
            # Save updated notifications
            NOTIFICATIONS_FILE.write_text(json.dumps(notifications, indent=2), encoding="utf-8")
            
            # Remove alert file if no pending approvals
            if not any(n.get("status") == "pending" for n in notifications):
                alert_file = ROOT / "outgoing" / "APPROVAL_NEEDED.flag"
                if alert_file.exists():
                    alert_file.unlink()
            
            return True
    
    print(f"No pending request found for {lease_id}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Phase 3 User Notifications")
    parser.add_argument("--list", action="store_true", help="List pending approvals")
    parser.add_argument("--approve", help="Approve a lease ID")
    parser.add_argument("--human-id", default="user1", help="Human identifier")
    
    args = parser.parse_args()
    
    if args.list:
        pending = list_pending_approvals()
        if pending:
            print(f"\n{'='*60}")
            print(f"PENDING APPROVALS: {len(pending)}")
            print(f"{'='*60}\n")
            for i, req in enumerate(pending, 1):
                print(f"{i}. Request Type: {req.get('request_type')}")
                print(f"   Intent: {req.get('intent_id')}")
                print(f"   Lease: {req.get('lease_id')}")
                print(f"   Details: {req.get('details')}")
                print()
        else:
            print("No pending approvals")
        return 0
    
    elif args.approve:
        success = approve_request(args.approve, args.human_id)
        return 0 if success else 1
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

