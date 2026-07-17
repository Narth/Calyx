"""Phase II routing proof normalization for intent artifacts."""

from __future__ import annotations

from typing import Any

from calyx.kernel.routing_proof import build_routing_proof, validate_routing_proof


def _derive_source_targets(required_evidence: list[str]) -> list[str]:
    targets = ["intent_artifact"]
    for item in required_evidence:
        if not isinstance(item, str):
            continue
        if item.startswith("search_target:") or item.startswith("definition_target:"):
            if item not in targets:
                targets.append(item)
    return targets


def normalize_routing_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    """Derive a deterministic routing proof for the intent artifact."""
    explicit = artifact.get("routing_proof")
    if isinstance(explicit, dict):
        valid, _ = validate_routing_proof(explicit)
        if valid:
            return explicit
    intake_card = artifact.get("intake_card") or {}
    required_evidence = intake_card.get("REQUIRED_EVIDENCE") or []
    source_targets = _derive_source_targets(required_evidence)
    return build_routing_proof(
        selected_tool_path="INTENT_PIPELINE_PLAN_ROUTE",
        rejected_alternatives=[
            "DIRECT_MAIL_TO_EXECUTION",
            "DIRECT_WORK_OUTBOX_WRITE",
            "UNGROUNDED_SYNTHESIS",
        ],
        source_target_required=source_targets,
        intent=artifact.get("intent", ""),
        entry_point=artifact.get("source", ""),
        rationale="Route through persisted intent artifact, clarification, and plan before any executable envelope is minted.",
        resolved_source_targets=source_targets,
        proof_id=artifact.get("envelope_id") or artifact.get("msg_id"),
    )
