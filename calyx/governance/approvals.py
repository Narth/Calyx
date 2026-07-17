"""Approval and rejection rules for operator-present local actions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .proposals import apply_timeout_transition, is_display_receipt_current, validate_proposal
from .receipts import validate_receipt
from .state_model import GuardDecision


def validate_operator_path(operator_path: dict[str, Any] | None) -> GuardDecision:
    if not isinstance(operator_path, dict):
        return GuardDecision(False, "operator_path_required")
    required = ("surface", "session_id", "interaction_kind", "operator_present")
    missing = [key for key in required if key not in operator_path]
    if missing:
        return GuardDecision(False, f"missing_operator_path_fields:{','.join(missing)}")
    if operator_path.get("operator_present") is not True:
        return GuardDecision(False, "operator_present_required")
    for key in ("surface", "session_id", "interaction_kind"):
        if not isinstance(operator_path.get(key), str) or not operator_path[key].strip():
            return GuardDecision(False, f"invalid_operator_path:{key}")
    return GuardDecision(True, "valid")


def can_approve_proposal(
    proposal: dict[str, Any],
    *,
    receipts: list[dict[str, Any]],
    operator_path: dict[str, Any] | None,
    now: datetime,
    on_shift: bool,
    halted: bool,
    caution_active: bool,
    proof_inputs: dict[str, Any],
    max_age_seconds: dict[str, int],
) -> GuardDecision:
    proposal_check = validate_proposal(proposal)
    if not proposal_check.allowed:
        return proposal_check

    operator_check = validate_operator_path(operator_path)
    if not operator_check.allowed:
        return operator_check

    if not on_shift:
        return GuardDecision(False, "off_shift")
    if halted:
        return GuardDecision(False, "halted")
    if caution_active:
        return GuardDecision(False, "global_post_attempt_caution")
    if proposal["lifecycle_state"] != "pending_review":
        return GuardDecision(False, "proposal_not_pending_review")
    if proposal["approval_status"] != "pending":
        return GuardDecision(False, "proposal_not_pending")
    if not is_display_receipt_current(
        receipts,
        proposal_id=proposal["proposal_id"],
        created_at=proposal["created_at"],
    ):
        return GuardDecision(False, "proposal_not_displayed")

    timed_out, timeout_decision = apply_timeout_transition(
        proposal,
        now=now,
        proof_inputs=proof_inputs,
        max_age_seconds=max_age_seconds,
    )
    if timeout_decision.next_lifecycle_state == "timed_out":
        return GuardDecision(False, timed_out["timeout_reason"])

    return GuardDecision(
        True,
        "approval_allowed",
        next_lifecycle_state="approved",
        next_approval_status="approved",
    )


def can_reject_proposal(
    proposal: dict[str, Any],
    *,
    operator_path: dict[str, Any] | None,
    reason: str | None,
) -> GuardDecision:
    proposal_check = validate_proposal(proposal)
    if not proposal_check.allowed:
        return proposal_check
    operator_check = validate_operator_path(operator_path)
    if not operator_check.allowed:
        return operator_check
    if proposal["lifecycle_state"] != "pending_review":
        return GuardDecision(False, "proposal_not_pending_review")
    if proposal["approval_status"] != "pending":
        return GuardDecision(False, "proposal_not_pending")
    if not isinstance(reason, str) or not reason.strip():
        return GuardDecision(False, "rejection_reason_required")
    return GuardDecision(
        True,
        "rejection_allowed",
        next_lifecycle_state="rejected",
        next_approval_status="rejected",
    )


def has_prior_approval_receipt(receipts: list[dict[str, Any]], *, proposal_id: str) -> bool:
    for receipt in receipts:
        result = validate_receipt(receipt)
        if not result.allowed:
            continue
        if receipt.get("receipt_type") == "approval_granted" and receipt.get("proposal_id") == proposal_id:
            return True
    return False
