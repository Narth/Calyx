"""Shared execution-gate validation. No live execution logic belongs here."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable

from .approvals import has_prior_approval_receipt
from .proposals import apply_timeout_transition, validate_proposal
from .state_model import GuardDecision


def can_accept_execution_attempt(
    proposal: dict[str, Any],
    *,
    receipts: list[dict[str, Any]],
    now: datetime,
    halted: bool,
    caution_active: bool,
    proof_inputs: dict[str, Any],
    max_age_seconds: dict[str, int],
    request_params: dict[str, Any],
    locked_fields: Iterable[str],
) -> GuardDecision:
    proposal_check = validate_proposal(proposal)
    if not proposal_check.allowed:
        return proposal_check
    if halted:
        return GuardDecision(False, "halted")
    if caution_active:
        return GuardDecision(False, "global_post_attempt_caution")
    if proposal["lifecycle_state"] != "approved":
        return GuardDecision(False, "proposal_not_approved")
    if proposal["approval_status"] != "approved":
        return GuardDecision(False, "approval_not_granted")
    if not has_prior_approval_receipt(receipts, proposal_id=proposal["proposal_id"]):
        return GuardDecision(False, "missing_prior_approval_receipt")

    timed_out, timeout_decision = apply_timeout_transition(
        proposal,
        now=now,
        proof_inputs=proof_inputs,
        max_age_seconds=max_age_seconds,
    )
    if timeout_decision.next_lifecycle_state == "timed_out":
        return GuardDecision(False, timed_out["timeout_reason"])

    for key in locked_fields:
        if proposal.get(key) != request_params.get(key):
            return GuardDecision(False, f"parameter_mismatch:{key}")

    return GuardDecision(
        True,
        "execution_attempt_allowed",
        next_lifecycle_state="consumed",
        next_approval_status="approved",
    )


def consume_approved_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(proposal)
    updated["lifecycle_state"] = "consumed"
    return updated
