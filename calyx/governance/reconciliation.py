"""Post-attempt outcome classification and caution handling."""

from __future__ import annotations

from typing import Any

from .state_model import GuardDecision


def resolve_post_attempt_state(evidence: dict[str, Any]) -> GuardDecision:
    """Resolve the next lifecycle posture from bounded post-attempt evidence."""

    if evidence.get("api_ack_state") == "ambiguous":
        return GuardDecision(True, "ambiguous_api_ack", next_lifecycle_state="post_attempt_caution")
    if evidence.get("fill_state") == "unknown":
        return GuardDecision(True, "unknown_fill_state", next_lifecycle_state="post_attempt_caution")
    if evidence.get("reconciliation_state") == "ambiguous":
        return GuardDecision(True, "ambiguous_reconciliation", next_lifecycle_state="post_attempt_caution")
    if evidence.get("reconciliation_state") == "complete":
        return GuardDecision(True, "reconciled", next_lifecycle_state="reconciled")
    if evidence.get("fill_state") in {"filled", "partial"}:
        return GuardDecision(True, "monitored", next_lifecycle_state="monitored")
    if evidence.get("api_ack_state") == "rejected":
        return GuardDecision(True, "execution_failed", next_lifecycle_state="execution_failed")
    return GuardDecision(True, "execution_failed", next_lifecycle_state="execution_failed")
