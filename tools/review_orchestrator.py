#!/usr/bin/env python3
"""
Review Orchestrator - Phase 1 Shadow Mode
Routes proposals to reviewers and manages state machine
Part of Capability Evolution Phase 1
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
INTENTS_DIR = ROOT / "outgoing" / "intents"
PROPOSALS_DIR = ROOT / "outgoing" / "proposals"
REVIEWS_DIR = ROOT / "outgoing" / "reviews"

# SVF imports
try:
    from tools.svf_audit import log_intent_activity
    from tools.svf_channels import send_message
    SVF_AVAILABLE = True
except ImportError:
    SVF_AVAILABLE = False
    def log_intent_activity(*args, **kwargs):
        pass
    def send_message(*args, **kwargs):
        pass


def load_capability_matrix() -> dict:
    """Load capability matrix"""
    matrix_file = ROOT / "outgoing" / "policies" / "capability_matrix.yaml"
    if not matrix_file.exists():
        return {}
    
    import yaml
    with matrix_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_constraints(intent: dict, proposals_dir: Path) -> tuple[bool, str]:
    """
    Check if intent satisfies Phase 1 constraints
    
    Returns:
        (is_valid, reason)
    """
    # Get metadata
    artifacts = intent.get("artifacts", {})
    intent_id = intent.get("intent_id", "")
    # Prefer provided metadata path; fallback to proposals/<intent_id>/metadata.json
    metadata_path = _resolve_artifact(artifacts.get("metadata"), proposals_dir / intent_id / "metadata.json")
    
    if not metadata_path.exists():
        return False, "metadata file not found"
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        return False, f"failed to read metadata: {e}"
    
    # Check line limit
    lines_added = meta.get("lines_added", 0)
    lines_removed = meta.get("lines_removed", 0)
    total_lines = lines_added + lines_removed
    
    matrix = load_capability_matrix()
    phase1 = matrix.get("phases", {}).get("phase1", {})
    max_lines = phase1.get("capabilities", {}).get("propose_patch", {}).get("constraints", {}).get("max_diff_lines", 500)
    
    if total_lines > max_lines:
        return False, f"diff too large: {total_lines} > {max_lines}"
    
    # Check reverse patch exists
    reverse_patch = artifacts.get("reverse_diff")
    if not reverse_patch or not Path(reverse_patch).exists():
        return False, "reverse patch not found"
    
    # Check tests reference
    if not intent.get("tests_reference"):
        return False, "tests_reference required"
    
    return True, ""


def _resolve_artifact(path_str: Optional[str], fallback: Path) -> Path:
    """Return absolute path from artifact string or fallback."""
    if path_str:
        p = Path(path_str)
        if not p.is_absolute():
            p = ROOT / p
        return p
    return fallback


def send_for_review(intent_id: str, artifacts: dict, reviewers: List[str], proposals_dir: Path, reviews_dir: Path):
    """Send intent to reviewers - invoke CP14/CP18 processors (CLI static mode)."""
    import subprocess

    # Fallbacks under proposals/<intent_id>/
    base = proposals_dir / intent_id
    patch_path = _resolve_artifact(artifacts.get("patch") or artifacts.get("change_patch"), base / "change.patch")
    metadata_path = _resolve_artifact(artifacts.get("metadata"), base / "metadata.json")

    for reviewer in reviewers:
        if reviewer == "cp14":
            cmd = [
                "python", "tools/cp14_sentinel.py",
                "--patch", str(patch_path),
                "--metadata", str(metadata_path),
                "--intent-id", intent_id,
            ]
            subprocess.run(cmd, capture_output=True, text=True)

        elif reviewer == "cp18":
            cmd = [
                "python", "tools/cp18_validator.py",
                "--patch", str(patch_path),
                "--metadata", str(metadata_path),
                "--intent-id", intent_id,
            ]
            subprocess.run(cmd, capture_output=True, text=True)

        if SVF_AVAILABLE:
            log_intent_activity(intent_id, "cbo", f"sent_to_{reviewer}", {"reviewer": reviewer})


def wait_for_verdicts(intent_id: str, agents: List[str], reviews_dir: Path, timeout_s: int = 600) -> Dict[str, str]:
    """
    Wait for verdicts from all agents
    
    Returns:
        Dictionary mapping agent names to verdicts
    """
    start_time = time.time()
    verdicts = {}
    
    while time.time() - start_time < timeout_s:
        verdicts = {}
        for agent in agents:
            verdict_file = reviews_dir / f"{intent_id}.{agent}.verdict.json"
            if verdict_file.exists():
                try:
                    with verdict_file.open("r", encoding="utf-8") as f:
                        verdict_data = json.load(f)
                        verdicts[agent] = verdict_data.get("verdict", "UNKNOWN")
                except Exception:
                    continue
        
        if set(verdicts.keys()) == set(agents):
            return verdicts
        
        time.sleep(1)
    
    return verdicts


def route_for_review(intent_json_path: str, proposals_dir: str = None, reviews_dir: str = None) -> str:
    """
    Route intent for review
    
    Returns:
        Final status
    """
    intent_file = Path(intent_json_path)
    if not intent_file.exists():
        raise FileNotFoundError(f"Intent file not found: {intent_json_path}")
    
    intent = json.loads(intent_file.read_text(encoding="utf-8"))
    iid = intent["intent_id"]
    
    proposals_dir = Path(proposals_dir) if proposals_dir else PROPOSALS_DIR
    reviews_dir = Path(reviews_dir) if reviews_dir else REVIEWS_DIR
    
    # Enforce constraints
    is_valid, reason = check_constraints(intent, proposals_dir)
    if not is_valid:
        intent["status"] = "rejected"
        intent["rejection_reason"] = reason
        intent_file.write_text(json.dumps(intent, indent=2), encoding="utf-8")
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cbo", "rejected_constraints", {"reason": reason})
        return "rejected"
    
    # Update status
    intent["status"] = "under_review"
    intent_file.write_text(json.dumps(intent, indent=2), encoding="utf-8")
    
    if SVF_AVAILABLE:
        log_intent_activity(iid, "cbo", "under_review", {})
    
    # Send to reviewers (invoke processors)
    reviewers = intent.get("reviewers", ["cp18", "cp14"])
    send_for_review(iid, intent.get("artifacts", {}), reviewers, proposals_dir, reviews_dir)
    
    # Wait for verdicts
    verdicts = wait_for_verdicts(iid, reviewers, reviews_dir, timeout_s=600)
    
    # CP16 Decision Matrix
    cp14_verdict = verdicts.get("cp14", "UNKNOWN")
    cp18_verdict = verdicts.get("cp18", "UNKNOWN")
    
    # Decision matrix per CGPT spec
    if cp14_verdict == "PASS" and cp18_verdict == "PASS":
        # Both pass - approve
        intent["status"] = "approved_pending_human"
        intent["arbitration_note"] = None
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cbo", "approved_pending_human", {"verdicts": verdicts})
    
    elif cp14_verdict == "FAIL" and cp18_verdict == "PASS":
        # CP14 fails - security issue
        intent["status"] = "rejected"
        intent["rejection_reason"] = "Security scan failed"
        intent["arbitration_note"] = "CP14 FAIL: Security issues detected. CP16 decision: Reject (security takes precedence)"
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cp16", "arbitrated", {"cp14": "FAIL", "cp18": "PASS", "decision": "reject"})
    
    elif cp14_verdict == "PASS" and cp18_verdict == "FAIL":
        # CP18 fails - validation issue
        intent["status"] = "rejected"
        intent["rejection_reason"] = "Validation failed"
        intent["arbitration_note"] = "CP18 FAIL: Validation issues detected. CP16 decision: Reject (tests/quality required)"
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cp16", "arbitrated", {"cp14": "PASS", "cp18": "FAIL", "decision": "reject"})
    
    elif cp14_verdict == "FAIL" and cp18_verdict == "FAIL":
        # Both fail - reject
        intent["status"] = "rejected"
        intent["rejection_reason"] = "Both security and validation failed"
        intent["arbitration_note"] = "CP14 FAIL, CP18 FAIL: Multiple issues detected. CP16 decision: Reject"
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cp16", "arbitrated", {"cp14": "FAIL", "cp18": "FAIL", "decision": "reject"})
    
    else:
        # Unknown state
        intent["status"] = "rejected"
        intent["rejection_reason"] = f"Unknown verdicts: {verdicts}"
        intent["arbitration_note"] = "Unknown verdict state"
        if SVF_AVAILABLE:
            log_intent_activity(iid, "cbo", "rejected_unknown", {"verdicts": verdicts})
    
    intent_file.write_text(json.dumps(intent, indent=2), encoding="utf-8")
    return intent["status"]


def main():
    parser = argparse.ArgumentParser(description="Review Orchestrator - Phase 1")
    parser.add_argument("--intent-path", required=True, help="Path to intent JSON file")
    parser.add_argument("--proposals-dir", help="Proposals directory")
    parser.add_argument("--reviews-dir", help="Reviews directory")
    
    args = parser.parse_args()
    
    try:
        status = route_for_review(args.intent_path, args.proposals_dir, args.reviews_dir)
        print(f"Intent status: {status}")
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

