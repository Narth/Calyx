#!/usr/bin/env python3
"""
CP14 Two-Key Verification - Phase 3
Extends CP14 lease verification with two-key governance
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]


def verify_two_key(lease_path: str) -> Tuple[bool, str]:
    """
    Verify two-key signatures on a lease
    
    Args:
        lease_path: Path to lease JSON file
        
    Returns:
        (is_valid, reason)
    """
    lease_file = Path(lease_path)
    if not lease_file.exists():
        return False, "Lease file not found"
    
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    
    # Check cosigners exist
    if "cosigners" not in lease or not lease["cosigners"]:
        return False, "No cosigners found"
    
    cosigners = lease["cosigners"]
    
    # Validate structure
    if len(cosigners) != 2:
        return False, f"Expected 2 cosigners, found {len(cosigners)}"
    
    # Check roles
    roles = [c.get("role") for c in cosigners]
    if "human" not in roles:
        return False, "Missing human cosigner"
    if "agent" not in roles:
        return False, "Missing agent cosigner"
    
    # Validate agent cosigner is CP14 or CP18
    agent_cosig = next((c for c in cosigners if c.get("role") == "agent"), None)
    if agent_cosig:
        agent_id = agent_cosig.get("id", "").lower()
        if agent_id not in ["cp14", "cp18"]:
            return False, f"Agent cosigner must be CP14 or CP18, found {agent_id}"
    
    # In a real implementation, verify cryptographic signatures here
    # For now, we'll check they exist
    for cosig in cosigners:
        if not cosig.get("sig"):
            return False, f"Missing signature for {cosig.get('id')}"
    
    return True, "Two-key verification passed"


def main():
    parser = argparse.ArgumentParser(description="CP14 Two-Key Verifier")
    parser.add_argument("--lease", required=True, help="Path to lease JSON file")
    
    args = parser.parse_args()
    
    is_valid, reason = verify_two_key(args.lease)
    
    if is_valid:
        print(f"Two-key verification: PASS")
        print(f"Reason: {reason}")
        return 0
    else:
        print(f"Two-key verification: FAIL")
        print(f"Reason: {reason}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

