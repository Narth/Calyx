"""
Validate that contract SHA256 matches PR description.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def compute_contract_hash(contract_path: Path) -> str:
    """Compute SHA256 of contract file."""
    content = contract_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    args = parser.parse_args()
    
    contract_path = Path(args.contract)
    if not contract_path.exists():
        print(f"ERROR: Contract not found: {contract_path}")
        exit(1)
    
    hash_val = compute_contract_hash(contract_path)
    print(f"Contract SHA256: {hash_val}")
    
    # In production, would fetch PR description and verify hash matches
    print(f"NOTE: PR #{args.pr_number} hash validation is a stub")


if __name__ == "__main__":
    main()
