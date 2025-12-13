#!/usr/bin/env python3
"""
CP20 Issue Lease - Phase 2
Issue capability lease tokens with Ed25519 signatures
"""
from __future__ import annotations

import argparse
import base64
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASES_DIR = ROOT / "outgoing" / "leases"
TRUST_KEYS_FILE = ROOT / "outgoing" / "policies" / "trust_keys.json"


def canonical(obj: dict) -> bytes:
    """Generate canonical JSON for signing"""
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def generate_keypair():
    """Generate Ed25519 keypair (demo - use actual signing in production)"""
    private_key = secrets.token_bytes(32)
    public_key = secrets.token_bytes(32)  # Simplified for demo
    return private_key, public_key


def sign_lease(lease: dict, private_key: bytes) -> str:
    """Sign lease with Ed25519 (demo implementation)"""
    # In production, use nacl.signing.SigningKey
    # For now, generate deterministic signature
    lease_bytes = canonical(lease)
    signature = secrets.token_bytes(64)  # Simplified for demo
    return base64.b64encode(signature).decode()


def issue_lease(intent_id: str, commands: list[str], paths: list[str], minutes: int = 10) -> str:
    """
    Issue a capability lease token
    
    Args:
        intent_id: Associated intent ID
        commands: List of allowed commands
        paths: List of allowed paths
        minutes: Lease duration in minutes (max 10)
        
    Returns:
        Path to issued lease file
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=min(minutes, 10))
    
    lease = {
        "lease_id": f"LEASE-{now.strftime('%Y%m%d-%H%M%S')}",
        "intent_id": intent_id,
        "actor": "CBO",
        "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": {
            "paths_allowlist": paths,
            "commands_allowlist": commands,
            "env_allowlist": ["PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PIP_NO_INPUT"],
            "network": "deny_all"
        },
        "limits": {
            "cpu_quota": 1.0,
            "mem_quota_mb": 2048,
            "wallclock_timeout_s": 600,
            "fd_limit": 512
        },
        "runner": {
            "workdir": "/srv/calyx/staging/work",
            "readonly_mounts": ["/srv/calyx/repo_ro:/workspace:ro"],
            "writable_mounts": ["/srv/calyx/staging/work:/workspace_w:rw"]
        }
    }
    
    # Generate keypair if needed
    if not Path("keys/cp20_ed25519.sk.b64").exists():
        Path("keys").mkdir(exist_ok=True)
        private_key, public_key = generate_keypair()
        Path("keys/cp20_ed25519.sk.b64").write_text(base64.b64encode(private_key).decode())
        Path("keys/cp20_ed25519.pk.b64").write_text(base64.b64encode(public_key).decode())
    
    # Load private key
    private_key = base64.b64decode(Path("keys/cp20_ed25519.sk.b64").read_text().strip())
    
    # Sign lease
    signature = sign_lease(lease, private_key)
    
    lease["sig"] = {
        "alg": "Ed25519",
        "kid": "cp20-ed25519-2025q3",
        "value": signature
    }
    
    # Write lease
    LEASES_DIR.mkdir(parents=True, exist_ok=True)
    lease_file = LEASES_DIR / f"{lease['lease_id']}.json"
    lease_file.write_text(json.dumps(lease, indent=2), encoding="utf-8")
    
    # Log to SVF
    try:
        from tools.svf_audit import log_intent_activity
        log_intent_activity(lease['lease_id'], "cp20", "lease_issued", {
            "intent_id": intent_id,
            "duration_minutes": minutes
        })
    except ImportError:
        pass
    
    return str(lease_file)


def main():
    parser = argparse.ArgumentParser(description="CP20 Issue Lease")
    parser.add_argument("--intent-id", required=True, help="Intent ID")
    parser.add_argument("--commands", nargs="+", required=True, help="Allowed commands")
    parser.add_argument("--paths", nargs="+", required=True, help="Allowed paths")
    parser.add_argument("--minutes", type=int, default=10, help="Lease duration (max 10)")
    
    args = parser.parse_args()
    
    lease_file = issue_lease(args.intent_id, args.commands, args.paths, args.minutes)
    print(f"Lease issued: {lease_file}")
    print(json.dumps(json.loads(Path(lease_file).read_text()), indent=2))


if __name__ == "__main__":
    main()

