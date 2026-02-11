#!/usr/bin/env python3
"""
Governance gate validator (updated to support approval_policy.json).

Usage:
  python tools/governance_gate.py --validate path/to/intent.json

Outputs a validation summary to stdout and appends a record to logs/governance/gate_log.jsonl
"""
from __future__ import annotations
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
# Primary capabilities path is governance/capabilities.json; fall back to capabilities/capabilities.json
_primary_cap = ROOT / "governance" / "capabilities.json"
_fallback_cap = ROOT / "capabilities" / "capabilities.json"
CAP_PATH = _primary_cap if _primary_cap.exists() else _fallback_cap
MANIFEST_PATH = ROOT / "governance" / "action_manifest.json"
SCHEMA_PATH = ROOT / "governance" / "intent_schema.json"
APPROVAL_POLICY_PATH = ROOT / "governance" / "approval_policy.json"
LOG_DIR = ROOT / "logs" / "governance"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "gate_log.jsonl"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def validate_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    cap = load_json(CAP_PATH)
    manifest = load_json(MANIFEST_PATH)
    schema = load_json(SCHEMA_PATH)
    policy = load_json(APPROVAL_POLICY_PATH)

    failures: List[str] = []

    # Basic schema checks (lightweight: required fields)
    for req in schema.get("required", []):
        if req not in intent:
            failures.append(f"missing_field:{req}")

    # Find action entry
    action_name = intent.get("intent")
    action_entry = None
    for a in manifest.get("actions", []):
        if a.get("name") == action_name:
            action_entry = a
            break
    if action_entry is None:
        failures.append("unknown_action")

    # Capabilities check
    if action_entry:
        req_caps = action_entry.get("required_capabilities", [])
        for rc in req_caps:
            allowed = cap.get(rc, False)
            if not allowed:
                failures.append(f"capability_missing:{rc}")

    # Approval policy: auto-approve low-risk actions (policy-controlled)
    auto_approve = policy.get("auto_approve", [])
    never_auto = policy.get("never_auto_approve", [])
    default_requires = policy.get("default_requires_approval", True)

    # If action is explicitly in never_auto_approve, we keep requires_approval true
    auto_approved = False
    if action_name in auto_approve and action_name not in never_auto and not failures:
        # mark as auto approved
        auto_approved = True

    # If intent explicitly has requires_approval flag, respect that (but never_auto_approve trumps)
    intent_requires_approval = intent.get("requires_approval", default_requires)
    if action_name in never_auto:
        intent_requires_approval = True

    # For the gate's evidence, include resolved requires_approval_final
    requires_approval_final = bool(intent_requires_approval) and (not auto_approved)

    # Enforce requires_approval policy (we only log here; actual execution daemon will check)
    # Only failure is if someone set requires_approval to false while action in never_auto_approve
    if action_name in never_auto and intent.get("requires_approval") == False:
        failures.append("policy_requires_approval")

    validation_result = "pass" if not failures else "fail"

    result = {
        "timestamp": _now_iso(),
        "intent_id": intent.get("intent_id"),
        "action": action_name,
        "validation_result": validation_result,
        "failures": failures,
        "capabilities_snapshot_hash": _hash(cap),
        "manifest_hash": _hash(manifest),
        "approval_policy_hash": _hash(policy),
        "auto_approved": auto_approved,
        "requires_approval_final": requires_approval_final
    }

    # write evidence record
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", help="Path to intent JSON to validate")
    args = parser.parse_args()
    if args.validate:
        p = Path(args.validate)
        intent = json.loads(p.read_text(encoding="utf-8"))
        out = validate_intent(intent)
        print(json.dumps(out, indent=2))
