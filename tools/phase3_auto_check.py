#!/usr/bin/env python3
"""
Phase 3: Auto-Check for Approvals
Continuously checks for pending approvals and displays status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALERT_FILE = ROOT / "outgoing" / "APPROVAL_NEEDED.flag"


def check_approvals() -> bool:
    """
    Check if approvals are needed
    
    Returns:
        True if approvals needed
    """
    if ALERT_FILE.exists():
        try:
            alert = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
            print("\n" + "="*60)
            print("APPROVAL NEEDED!")
            print("="*60)
            print(f"Type: {alert.get('request_type')}")
            print(f"Intent: {alert.get('intent_id')}")
            print(f"Lease: {alert.get('lease_id')}")
            print(f"Details: {alert.get('details')}")
            print("\nTo approve: python tools/phase3_user_notifications.py --approve <lease_id>")
            print("="*60 + "\n")
            return True
        except Exception:
            pass
    
    return False


def main():
    approvals_needed = check_approvals()
    return 1 if approvals_needed else 0


if __name__ == "__main__":
    sys.exit(main())

