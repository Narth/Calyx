"""Canonical governance states and presentation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LIFECYCLE_STATES = frozenset(
    {
        "pending_review",
        "approved",
        "rejected",
        "timed_out",
        "consumed",
        "execution_failed",
        "post_attempt_caution",
        "monitored",
        "reconciled",
    }
)

APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected", "not_approvable"})

DERIVED_UI_STATUSES = frozenset(
    {
        "actionable",
        "not_actionable_halted",
        "not_actionable_timed_out",
        "not_actionable_rejected",
        "not_actionable_consumed",
        "not_actionable_caution",
    }
)


@dataclass(frozen=True)
class GuardDecision:
    """Bounded result for transition and validator checks."""

    allowed: bool
    reason: str
    next_lifecycle_state: str | None = None
    next_approval_status: str | None = None


def derive_ui_status(proposal: dict[str, Any], *, halted: bool, caution_active: bool) -> str:
    """
    Derive a presentation-only UI status.

    This status is intentionally non-authoritative and must not be used as an
    execution or approval source of truth.
    """

    lifecycle_state = proposal.get("lifecycle_state")
    approval_status = proposal.get("approval_status")

    if caution_active or lifecycle_state == "post_attempt_caution":
        return "not_actionable_caution"
    if halted:
        return "not_actionable_halted"
    if lifecycle_state == "timed_out":
        return "not_actionable_timed_out"
    if lifecycle_state == "rejected" or approval_status == "rejected":
        return "not_actionable_rejected"
    if lifecycle_state == "consumed":
        return "not_actionable_consumed"
    if lifecycle_state == "approved" and approval_status == "approved":
        return "actionable"
    return "not_actionable_halted"
