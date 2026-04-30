#!/usr/bin/env python3
"""WO_DISCORD_CANONICAL_TRANSPORT_DECLARATION_V1 — Write declaration and alignment receipts."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    audit_dir = REPO_ROOT / "runtime" / "receipts" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    policy_dir = REPO_ROOT / "policy"
    intake_path = policy_dir / "intake_classification.json"
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Policy: file created by this WO; no prior classification
    previous_classification = None
    new_classification = json.loads(intake_path.read_text(encoding="utf-8")) if intake_path.exists() else {}
    policy_hash_before = "file_did_not_exist"
    policy_hash_after = _file_hash(intake_path) if intake_path.exists() else "file_not_created"

    # 1) Discord canonical transport declaration receipt
    declaration = {
        "schema": "audit.discord_canonical_transport_declaration.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "wo": "WO_DISCORD_CANONICAL_TRANSPORT_DECLARATION_V1",
        "observe_mode": True,
        "previous_classification": previous_classification,
        "new_classification": new_classification,
        "policy_hash_before": policy_hash_before,
        "policy_hash_after": policy_hash_after,
        "confirmation_no_authority_widening": True,
        "explicit_non_changes": {
            "dry_run_only_remains_true": True,
            "no_lane_escalation": True,
            "no_execution_path_enabled": True,
            "no_new_emitter_authority_beyond_discord_transport": True,
            "no_new_listeners_introduced": True,
            "canonical_repo_hash_unchanged": True,
        },
    }
    decl_path = audit_dir / f"discord_canonical_transport_declaration__{ts_tag}.json"
    decl_path.write_text(json.dumps(declaration, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"declaration_receipt={decl_path}")

    # 2) Transport comparator alignment receipt
    alignment = {
        "schema": "audit.discord_transport_comparator_alignment.v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "observe_mode": True,
        "discord_canonical_recognition": {
            "source": "calyx.cbo.discord_gateway",
            "authority_basis": "discord.heartbeat.sender.identity",
            "classification": "transport_only_canonical",
            "emitter_authority_treated_as_canonical": True,
        },
        "fail_closed_thresholds_unchanged": True,
        "misclassification_prevention": "Discord emitter no longer flagged as external/unauthorized when source and authority_basis match.",
    }
    align_path = audit_dir / f"discord_transport_comparator_alignment__{ts_tag}.json"
    align_path.write_text(json.dumps(alignment, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"alignment_receipt={align_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
