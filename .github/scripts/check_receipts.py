"""Validate that the current PR generated its bounded Hub Runner CI receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def check_receipts(pr_number: int, receipts_path: Path) -> bool:
    """Check for the validate-only Hub Runner receipt tied to this PR."""
    if pr_number <= 0:
        print("ERROR: PR number must be a positive integer")
        return False
    receipts_path.mkdir(parents=True, exist_ok=True)

    hub_receipts = list(receipts_path.glob("hub_runner__*.jsonl"))
    if not hub_receipts:
        print("ERROR: No Hub Runner receipts found")
        return False

    expected_envelope_id = f"ci-pr-{pr_number}-hub-runner-receipt"
    for receipt_path in hub_receipts:
        try:
            lines = receipt_path.read_text(encoding="utf-8").splitlines()
            records = [json.loads(line) for line in lines if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: Unreadable Hub Runner receipt {receipt_path}: {exc}")
            return False
        for record in records:
            if (
                record.get("envelope_id") == expected_envelope_id
                and record.get("receipt_type") == "hub_runner"
                and record.get("phase") == "validate"
                and record.get("status") == "allowed"
                and record.get("reason") == "swarm_validate_only_phase2"
            ):
                print(f"Validated Hub Runner CI receipt for PR {pr_number}: {receipt_path}")
                return True

    print(f"ERROR: No validate-only Hub Runner receipt matched PR {pr_number}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--receipts-path", default="runtime/receipts")
    args = parser.parse_args()
    
    receipts_path = Path(args.receipts_path)
    if not check_receipts(args.pr_number, receipts_path):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
