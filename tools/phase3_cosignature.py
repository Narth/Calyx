#!/usr/bin/env python3
"""
Phase 3: Two-Key Cosignature Handler
CGPT Blueprint Implementation
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

ROOT = Path(__file__).resolve().parents[1]


def add_cosignature(lease_path: str, role: str, cosigner_id: str, signature: str) -> bool:
    """
    Add a cosignature to a lease
    
    Args:
        lease_path: Path to lease JSON file
        role: "human" or "agent"
        cosigner_id: Cosigner identifier
        signature: Base64 Ed25519 signature
        
    Returns:
        True if successful
    """
    lease_file = Path(lease_path)
    if not lease_file.exists():
        print(f"ERROR: Lease file not found: {lease_path}")
        return False
    
    # Load lease
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    
    # Initialize cosigners array if needed
    if "cosigners" not in lease:
        lease["cosigners"] = []
    
    # Add cosignature
    cosig = {
        "role": role,
        "id": cosigner_id,
        "sig": signature,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    lease["cosigners"].append(cosig)
    
    # Save updated lease
    lease_file.write_text(json.dumps(lease, indent=2), encoding="utf-8")
    
    # Log to SVF
    try:
        from tools.svf_audit import log_deployment_event
        log_deployment_event(
            event_type="COSIGNED",
            lease_id=lease.get("lease_id", "unknown"),
            intent_id=lease.get("intent_id", "unknown"),
            agent=cosigner_id,
            metadata={"role": role}
        )
    except ImportError:
        pass
    
    print(f"Cosignature added: {role} ({cosigner_id})")
    return True


def validate_cosignatures(lease_path: str) -> tuple[bool, str]:
    """
    Validate that lease has required cosignatures
    
    Args:
        lease_path: Path to lease JSON file
        
    Returns:
        (is_valid, reason)
    """
    lease_file = Path(lease_path)
    if not lease_file.exists():
        return False, "Lease file not found"
    
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    
    # Check if cosigners exist
    if "cosigners" not in lease or not lease["cosigners"]:
        return False, "No cosigners found"
    
    cosigners = lease["cosigners"]
    
    # Check count
    if len(cosigners) < 2:
        return False, f"Only {len(cosigners)} cosigner(s), need 2"
    
    # Check roles
    roles = [c.get("role") for c in cosigners]
    if "human" not in roles:
        return False, "Missing human cosigner"
    if "agent" not in roles:
        return False, "Missing agent cosigner"
    
    # Check signatures exist
    for cosig in cosigners:
        if not cosig.get("sig"):
            return False, f"Missing signature for {cosig.get('id')}"
    
    return True, "Valid"


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Cosignature Handler")
    parser.add_argument("--lease", required=True, help="Path to lease JSON file")
    parser.add_argument("--add", action="store_true", help="Add cosignature")
    parser.add_argument("--role", choices=["human", "agent"], help="Cosigner role")
    parser.add_argument("--id", help="Cosigner ID")
    parser.add_argument("--sig", help="Base64 signature")
    parser.add_argument("--validate", action="store_true", help="Validate cosignatures")
    
    args = parser.parse_args()
    
    if args.add:
        if not all([args.role, args.id, args.sig]):
            print("ERROR: --add requires --role, --id, and --sig")
            return 1
        success = add_cosignature(args.lease, args.role, args.id, args.sig)
        return 0 if success else 1
    
    elif args.validate:
        is_valid, reason = validate_cosignatures(args.lease)
        print(f"Validation: {'VALID' if is_valid else 'INVALID'}")
        print(f"Reason: {reason}")
        return 0 if is_valid else 1
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

