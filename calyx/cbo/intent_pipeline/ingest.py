"""Ingest: Mail Envelope -> Intent Artifact. Reads from CBO mail_inbox."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from calyx.kernel.integrity_gate import spine_operation_lease

from .intake_card import merge_intake_card, validate_intake_card
from .routing_proof import normalize_routing_proof
from .registry import get_intent_dir, save_intent_artifact, save_status


def get_mail_inbox(runtime_dir: Path) -> Path:
    return runtime_dir / "cbo" / "mail_inbox"


def list_pending_mail(runtime_dir: Path) -> list[Path]:
    """List JSON files in CBO mail_inbox."""
    inbox = get_mail_inbox(runtime_dir)
    if not inbox.exists():
        return []
    return sorted(inbox.glob("*.json"))


def ingest_mail_envelope(mail_path: Path, runtime_dir: Path) -> str | None:
    """
    Ingest one Mail Envelope from mail_path into Intent Artifact store.
    Moves mail file into intent artifact receipts (or deletes after copy).
    Returns intent_id (envelope_id) or None on failure.
    """
    repo_root = runtime_dir.parent
    with spine_operation_lease(runtime_dir, repo_root, include_execution_path=False, skip_if_env=True) as ok:
        if not ok:
            return None

        try:
            with open(mail_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except Exception:
            return None
        intent_id = envelope.get("envelope_id") or envelope.get("msg_id") or mail_path.stem
        dir_path = get_intent_dir(intent_id, runtime_dir)
        normalized = merge_intake_card(envelope)
        normalized["routing_proof"] = normalize_routing_proof(normalized)
        intake_valid, missing = validate_intake_card(normalized.get("intake_card") or {})
        normalized["intake_card_status"] = "complete" if intake_valid else "needs_clarification"
        normalized["missing_intake_fields"] = missing
        save_intent_artifact(intent_id, runtime_dir, normalized)
        save_status(
            intent_id,
            runtime_dir,
            {
                "status": "pending_clarification",
                "ingested_at": envelope.get("ts_utc", ""),
                "intake_card_status": normalized["intake_card_status"],
                "missing_intake_fields": missing,
                "routing_proof_status": "complete",
            },
        )
        receipt_dest = dir_path / "receipts" / f"mail_{mail_path.name}"
        receipt_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(mail_path), str(receipt_dest))
        return intent_id
