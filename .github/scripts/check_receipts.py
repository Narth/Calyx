"""
Check that required receipts are present for PR.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def check_receipts(pr_number: int, receipts_path: Path) -> bool:
    """Check if receipts exist for PR."""
    receipts_path.mkdir(parents=True, exist_ok=True)
    
    # Look for hub_runner receipts
    hub_receipts = list(receipts_path.glob("hub_runner__*.jsonl"))
    if not hub_receipts:
        print("WARNING: No hub_runner receipts found")
        return False
    
    # Look for manifests
    manifests_path = receipts_path.parent / "manifests"
    if manifests_path.exists():
        manifests = list(manifests_path.glob("*_manifest.json"))
        if not manifests:
            print("WARNING: No manifests found")
            return False
    
    print(f"Found {len(hub_receipts)} hub_runner receipt(s)")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--receipts-path", default="runtime/receipts")
    args = parser.parse_args()
    
    receipts_path = Path(args.receipts_path)
    if not check_receipts(args.pr_number, receipts_path):
        exit(1)


if __name__ == "__main__":
    main()
