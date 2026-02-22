"""Score: priority and risk scoring for intents. No execution."""

from __future__ import annotations

from typing import Any


def score_intent(artifact: dict[str, Any]) -> dict[str, Any]:
    """
    Return risk_tier and priority hint from artifact. Deterministic.
    """
    risk_hint = artifact.get("risk_hint") or "low"
    task_type = artifact.get("task_type") or "doc_update"
    if task_type in ("refactor_scope",) or artifact.get("requires_human_approval"):
        risk_tier = "high"
    elif task_type in ("lint_fix", "test_run", "code_review", "schema_validation"):
        risk_tier = "med"
    else:
        risk_tier = "low"
    return {"risk_tier": risk_tier, "priority_hint": 3}
