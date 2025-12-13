#!/usr/bin/env python3
"""
Acknowledge a sysint suggestion to prevent it from being re-reported
Creates an acknowledged.jsonl file to track dismissed suggestions
"""

import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
ACKNOWLEDGED_FILE = ROOT / "calyx" / "cbo" / "sysint_acknowledged.jsonl"

def acknowledge_suggestion(suggestion_id: str, reason: str = "User acknowledged") -> None:
    """Add a suggestion to the acknowledged list"""
    ACKNOWLEDGED_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "suggestion_id": suggestion_id,
        "acknowledged_at": datetime.now().isoformat(),
        "reason": reason,
    }
    
    with ACKNOWLEDGED_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"[OK] Acknowledged suggestion: {suggestion_id}")
    print(f"     Reason: {reason}")

def is_acknowledged(suggestion_id: str) -> bool:
    """Check if a suggestion has been acknowledged"""
    if not ACKNOWLEDGED_FILE.exists():
        return False
    
    with ACKNOWLEDGED_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    if record.get("suggestion_id") == suggestion_id:
                        return True
                except Exception:
                    pass
    return False

def list_acknowledged() -> list:
    """List all acknowledged suggestions"""
    if not ACKNOWLEDGED_FILE.exists():
        return []
    
    acknowledged = []
    with ACKNOWLEDGED_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    acknowledged.append(json.loads(line))
                except Exception:
                    pass
    return acknowledged

def main():
    if len(sys.argv) < 2:
        print("Usage: python acknowledge_sysint_suggestion.py <suggestion_id> [reason]")
        print("\nExample:")
        print("  python acknowledge_sysint_suggestion.py wsl_not_available \"WSL is functioning correctly\"")
        print("\nCurrent acknowledged suggestions:")
        for item in list_acknowledged():
            print(f"  - {item.get('suggestion_id')}: {item.get('reason')}")
        sys.exit(1)
    
    suggestion_id = sys.argv[1]
    reason = sys.argv[2] if len(sys.argv) > 2 else "User acknowledged"
    
    acknowledge_suggestion(suggestion_id, reason)

if __name__ == "__main__":
    main()

