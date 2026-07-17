"""Shared governance primitives for proposal-capable, human-gated actions."""

from .approvals import can_approve_proposal, can_reject_proposal, validate_operator_path
from .execution_gate import can_accept_execution_attempt, consume_approved_proposal
from .proposals import (
    REQUIRED_PROOF_INPUTS,
    apply_timeout_transition,
    is_display_receipt_current,
    validate_proposal,
)
from .receipts import emit_governance_receipt, make_receipt, validate_receipt
from .reconciliation import resolve_post_attempt_state
from .state_model import (
    APPROVAL_STATUSES,
    DERIVED_UI_STATUSES,
    GuardDecision,
    LIFECYCLE_STATES,
    derive_ui_status,
)

__all__ = [
    "APPROVAL_STATUSES",
    "DERIVED_UI_STATUSES",
    "GuardDecision",
    "LIFECYCLE_STATES",
    "REQUIRED_PROOF_INPUTS",
    "apply_timeout_transition",
    "can_accept_execution_attempt",
    "can_approve_proposal",
    "can_reject_proposal",
    "consume_approved_proposal",
    "derive_ui_status",
    "emit_governance_receipt",
    "is_display_receipt_current",
    "make_receipt",
    "resolve_post_attempt_state",
    "validate_operator_path",
    "validate_proposal",
    "validate_receipt",
]
