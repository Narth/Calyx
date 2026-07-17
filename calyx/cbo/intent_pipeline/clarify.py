"""Clarify: check intent readiness, request clarification, update artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calyx.kernel.failure_patterns import attach_failure_pattern_metadata
from calyx.kernel.routing_proof import validate_routing_proof

from .intake_card import (
    intake_card_clarification_message,
    merge_intake_card,
    validate_intake_card,
)
from .routing_proof import normalize_routing_proof
from .registry import load_intent_artifact, load_status, save_status, append_clarification


def needs_clarification(artifact: dict[str, Any], status: dict[str, Any] | None) -> bool:
    """True if intent is ambiguous or missing required fields for planning."""
    if status and status.get("status") == "ready":
        return False
    intent = (artifact.get("intent") or "").strip()
    if not intent or len(intent) < 2:
        return True
    task_type = artifact.get("task_type")
    if not task_type:
        return True
    merged = merge_intake_card(artifact)
    valid, _ = validate_intake_card(merged.get("intake_card") or {})
    if not valid:
        return True
    routing_valid, _ = validate_routing_proof(normalize_routing_proof(merged))
    if not routing_valid:
        return True
    return False


def mark_ready(intent_id: str, runtime_dir: Path) -> Path:
    """Mark intent as ready for planning."""
    artifact = load_intent_artifact(intent_id, runtime_dir)
    if artifact is None:
        return save_status(intent_id, runtime_dir, {"status": "pending_clarification", "reason": "intent_artifact_missing"})
    merged = merge_intake_card(artifact)
    valid, missing = validate_intake_card(merged.get("intake_card") or {})
    if not valid:
        message = intake_card_clarification_message(missing)
        append_clarification(intent_id, runtime_dir, {"request": message, "source": "phase1_intake_card"})
        return save_status(
            intent_id,
            runtime_dir,
            attach_failure_pattern_metadata(
                {
                "status": "pending_clarification",
                "intake_card_status": "needs_clarification",
                "missing_intake_fields": missing,
                "reason": "phase1_intake_card_incomplete",
                },
                pattern_ids=["scope_drift"],
            ),
        )
    merged["routing_proof"] = normalize_routing_proof(merged)
    routing_valid, routing_missing = validate_routing_proof(merged.get("routing_proof") or {})
    if not routing_valid:
        append_clarification(
            intent_id,
            runtime_dir,
            {"request": f"Phase II routing proof incomplete. Missing fields: {', '.join(routing_missing)}.", "source": "phase2_routing_proof"},
        )
        return save_status(
            intent_id,
            runtime_dir,
            attach_failure_pattern_metadata(
                {
                "status": "pending_clarification",
                "intake_card_status": "complete",
                "missing_intake_fields": [],
                "routing_proof_status": "needs_clarification",
                "missing_routing_fields": routing_missing,
                "reason": "phase2_routing_proof_incomplete",
                },
                pattern_ids=["tool_misuse", "hallucinated_context"],
            ),
        )
    from .registry import save_intent_artifact
    save_intent_artifact(intent_id, runtime_dir, merged)
    return save_status(
        intent_id,
        runtime_dir,
        {
            "status": "ready",
            "intake_card_status": "complete",
            "missing_intake_fields": [],
            "routing_proof_status": "complete",
            "missing_routing_fields": [],
        },
    )


def request_clarification(intent_id: str, runtime_dir: Path, message: str) -> Path:
    """Append clarification request to artifact."""
    from datetime import datetime, timezone
    return append_clarification(
        intent_id,
        runtime_dir,
        {"ts_utc": datetime.now(timezone.utc).isoformat(), "request": message},
    )
