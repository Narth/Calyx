"""
Generate CI receipt artifact.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--risk-tier", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    receipt = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pr_number": args.pr_number,
        "risk_tier": args.risk_tier,
        "ci_workflow": "code_factory_gates",
        "status": "completed"
    }
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    
    print(f"CI receipt written: {output_path}")


if __name__ == "__main__":
    main()
