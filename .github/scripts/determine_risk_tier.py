"""
Determine risk tier for a PR based on diff paths and contract rules.
"""
from __future__ import annotations

import argparse
import json
import yaml
from pathlib import Path
import subprocess


def get_pr_diff_paths(pr_number: int) -> list[str]:
    """Get list of changed file paths from PR."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def determine_risk_tier(contract: dict, diff_paths: list[str]) -> tuple[str, bool]:
    """Determine risk tier based on contract rules and diff paths."""
    risk_rules = contract.get("risk_rules", {})
    requires_approval = False
    
    # Check high risk triggers
    high_triggers = risk_rules.get("high", {}).get("triggers", [])
    for trigger in high_triggers:
        if isinstance(trigger, dict):
            if "diff_paths" in trigger:
                patterns = trigger["diff_paths"]
                if any(any(pattern in path for pattern in patterns) for path in diff_paths):
                    requires_approval = True
                    return "high", requires_approval
            elif trigger == "policy_files_changed":
                if any("governance" in p or "CALYX_CONTRACT.yaml" in p for p in diff_paths):
                    requires_approval = True
                    return "high", requires_approval
    
    # Check med risk triggers
    med_triggers = risk_rules.get("med", {}).get("triggers", [])
    for trigger in med_triggers:
        if isinstance(trigger, dict):
            if "dependency_files_changed" in trigger:
                dep_files = ["requirements.txt", "pyproject.toml", "package.json", "go.mod"]
                if any(f in str(p) for p in diff_paths for f in dep_files):
                    return "med", requires_approval
    
    return "low", requires_approval


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    # Load contract
    with open(args.contract, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    
    # Get diff paths
    diff_paths = get_pr_diff_paths(args.pr_number)
    
    # Determine risk tier
    risk_tier, requires_approval = determine_risk_tier(contract, diff_paths)
    
    # Write output
    output = {
        "risk_tier": risk_tier,
        "requires_approval": requires_approval,
        "diff_paths": diff_paths
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    print(f"Risk tier: {risk_tier}, Requires approval: {requires_approval}")


if __name__ == "__main__":
    main()
