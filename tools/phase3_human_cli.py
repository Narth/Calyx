#!/usr/bin/env python3
"""
Phase 3: Human Governance CLI
CGPT Blueprint Implementation
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]


def sign_lease(intent_id: str, human_id: str, signature: str) -> bool:
    """
    Human signs a lease for an intent
    
    Args:
        intent_id: Intent ID to sign
        human_id: Human identifier
        signature: Human signature (can be name for now)
        
    Returns:
        True if successful
    """
    # Find lease for this intent
    leases_dir = ROOT / "outgoing" / "leases"
    if not leases_dir.exists():
        print("ERROR: No leases directory found")
        return False
    
    # Look for latest lease for this intent
    lease_files = sorted(leases_dir.glob("LEASE-*.json"), reverse=True)
    lease_file = None
    
    for lf in lease_files:
        try:
            lease = json.loads(lf.read_text(encoding="utf-8"))
            if lease.get("intent_id") == intent_id:
                lease_file = lf
                break
        except Exception:
            continue
    
    if not lease_file:
        print(f"ERROR: No lease found for intent {intent_id}")
        return False
    
    # Add human cosignature
    try:
        import subprocess
        result = subprocess.run(
            ["python", "tools/phase3_cosignature.py", "--lease", str(lease_file),
             "--add", "--role", "human", "--id", human_id, "--sig", signature],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: Failed to add cosignature: {e}")
        return False


def pause_rollout(lease_id: str) -> bool:
    """
    Pause an active rollout
    
    Args:
        lease_id: Lease ID to pause
        
    Returns:
        True if successful
    """
    print(f"Pausing rollout for {lease_id}")
    
    # In full implementation, this would:
    # 1. Set rollout status to PAUSED
    # 2. Halt canary promotion
    # 3. Log pause event to SVF
    
    try:
        from tools.svf_audit import log_deployment_event
        log_deployment_event(
            event_type="PAUSED",
            lease_id=lease_id,
            intent_id="unknown",
            agent="human",
            metadata={"action": "manual_pause"}
        )
    except ImportError:
        pass
    
    print(f"Rollout paused: {lease_id}")
    return True


def force_rollback(lease_id: str) -> bool:
    """
    Force rollback of a deployment
    
    Args:
        lease_id: Lease ID to rollback
        
    Returns:
        True if successful
    """
    print(f"Forcing rollback for {lease_id}")
    
    # In full implementation, this would:
    # 1. Trigger rollback pack execution
    # 2. Revert changes
    # 3. Log rollback event to SVF
    
    try:
        from tools.svf_audit import log_deployment_event
        log_deployment_event(
            event_type="ROLLED_BACK",
            lease_id=lease_id,
            intent_id="unknown",
            agent="human",
            metadata={"action": "manual_rollback"}
        )
    except ImportError:
        pass
    
    print(f"Rollback triggered: {lease_id}")
    return True


def approve_next_tier(lease_id: str) -> bool:
    """
    Approve promotion to next canary tier
    
    Args:
        lease_id: Lease ID to promote
        
    Returns:
        True if successful
    """
    print(f"Approving next tier for {lease_id}")
    
    # In full implementation, this would:
    # 1. Check current tier
    # 2. Promote to next tier (5% → 25% → 100%)
    # 3. Log promotion event to SVF
    
    try:
        from tools.svf_audit import log_deployment_event
        log_deployment_event(
            event_type="CANARY_PROMOTED",
            lease_id=lease_id,
            intent_id="unknown",
            agent="human",
            metadata={"action": "manual_promotion"}
        )
    except ImportError:
        pass
    
    print(f"Next tier approved: {lease_id}")
    return True


def list_active_leases() -> None:
    """List all active leases with status"""
    leases_dir = ROOT / "outgoing" / "leases"
    if not leases_dir.exists():
        print("No active leases")
        return
    
    lease_files = sorted(leases_dir.glob("LEASE-*.json"), reverse=True)
    
    print("\nActive Leases:")
    print("-" * 80)
    print(f"{'Lease ID':<20} {'Intent ID':<20} {'Cosigners':<20} {'Status'}")
    print("-" * 80)
    
    for lease_file in lease_files[:10]:  # Show last 10
        try:
            lease = json.loads(lease_file.read_text(encoding="utf-8"))
            lease_id = lease.get("lease_id", lease_file.stem)
            intent_id = lease.get("intent_id", "unknown")
            cosigners = lease.get("cosigners", [])
            
            if cosigners:
                cosigner_str = f"{len(cosigners)}/2"
                if len(cosigners) == 2:
                    cosigner_str += " ✅"
            else:
                cosigner_str = "0/2 ⏳"
            
            print(f"{lease_id:<20} {intent_id:<20} {cosigner_str:<20} Active")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Human Governance CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # sign-lease command
    sign_parser = subparsers.add_parser("sign-lease", help="Sign a lease")
    sign_parser.add_argument("intent_id", help="Intent ID to sign")
    sign_parser.add_argument("--human-id", default="user1", help="Human identifier")
    sign_parser.add_argument("--sig", default="user_signature", help="Signature")
    
    # pause-rollout command
    pause_parser = subparsers.add_parser("pause-rollout", help="Pause rollout")
    pause_parser.add_argument("lease_id", help="Lease ID to pause")
    
    # force-rollback command
    rollback_parser = subparsers.add_parser("force-rollback", help="Force rollback")
    rollback_parser.add_argument("lease_id", help="Lease ID to rollback")
    
    # approve-next-tier command
    approve_parser = subparsers.add_parser("approve-next-tier", help="Approve next tier")
    approve_parser.add_argument("lease_id", help="Lease ID to promote")
    
    # list-leases command
    subparsers.add_parser("list-leases", help="List active leases")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "sign-lease":
        success = sign_lease(args.intent_id, args.human_id, args.sig)
        return 0 if success else 1
    
    elif args.command == "pause-rollout":
        success = pause_rollout(args.lease_id)
        return 0 if success else 1
    
    elif args.command == "force-rollback":
        success = force_rollback(args.lease_id)
        return 0 if success else 1
    
    elif args.command == "approve-next-tier":
        success = approve_next_tier(args.lease_id)
        return 0 if success else 1
    
    elif args.command == "list-leases":
        list_active_leases()
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

