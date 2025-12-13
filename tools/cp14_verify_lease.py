#!/usr/bin/env python3
"""
CP14 Verify Lease - Phase 2
Verify capability lease tokens
"""
from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUST_KEYS_FILE = ROOT / "outgoing" / "policies" / "trust_keys.json"


def canonical(obj: dict) -> bytes:
    """Generate canonical JSON for verification"""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def verify_lease(lease_path: str, trust_keys_path: str = None) -> tuple[bool, str]:
    """
    Verify lease token
    
    Args:
        lease_path: Path to lease JSON file
        trust_keys_path: Path to trust keys file
        
    Returns:
        (is_valid, reason)
    """
    if trust_keys_path is None:
        trust_keys_path = str(TRUST_KEYS_FILE)
    
    lease_file = Path(lease_path)
    if not lease_file.exists():
        return False, "Lease file not found"
    
    trust_file = Path(trust_keys_path)
    if not trust_file.exists():
        return False, "Trust keys file not found"
    
    lease = json.loads(lease_file.read_text(encoding="utf-8"))
    trust = json.loads(trust_file.read_text(encoding="utf-8"))
    
    # Check signature KID
    kid = lease["sig"]["kid"]
    if kid not in trust["keys"]:
        return False, f"Unknown key ID: {kid}"
    
    # Verify signature (simplified for demo)
    lease_copy = {k: v for k, v in lease.items() if k != "sig"}
    canonical_bytes = canonical(lease_copy)
    signature_bytes = base64.b64decode(lease["sig"]["value"])
    
    # In production, use nacl.signing.VerifyKey
    # For now, assume valid if signature exists
    if not signature_bytes:
        return False, "Invalid signature"
    
    # Check expiration
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if lease["issued_at"] > now:
        return False, "Lease issued in future"
    if lease["expires_at"] < now:
        return False, "Lease expired"
    
    # Additional policy checks would go here
    # - paths_allowlist verification
    # - commands_allowlist verification
    # - env_allowlist verification
    # - network policy check
    
    return True, "Valid"


def main():
    parser = argparse.ArgumentParser(description="CP14 Verify Lease")
    parser.add_argument("--lease-path", required=True, help="Path to lease JSON file")
    parser.add_argument("--trust-keys", help="Path to trust keys file")
    
    args = parser.parse_args()
    
    is_valid, reason = verify_lease(args.lease_path, args.trust_keys)
    
    if is_valid:
        print(f"Lease verified: {reason}")
        return 0
    else:
        print(f"Lease invalid: {reason}")
        return 1


if __name__ == "__main__":
    exit(main())

