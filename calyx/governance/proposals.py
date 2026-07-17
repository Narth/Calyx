"""Proposal validation, supersession, and timeout rules."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .state_model import APPROVAL_STATUSES, GuardDecision, LIFECYCLE_STATES

REQUIRED_PROPOSAL_FIELDS = (
    "proposal_id",
    "corr_id",
    "created_at",
    "expires_at",
    "lifecycle_state",
    "approval_status",
    "rationale_summary",
    "evidence_summary",
    "thesis_summary",
    "freshness_assessment",
    "timing_window_summary",
    "monitoring_plan",
    "policy_snapshot",
    "budget_posture",
)

REQUIRED_PROOF_INPUTS = (
    "market_snapshot_ts",
    "account_snapshot_ts",
    "policy_snapshot_ts",
    "budget_posture_ts",
)

_SUBSTANTIVE_TEXT_FIELDS = (
    "rationale_summary",
    "evidence_summary",
    "thesis_summary",
    "freshness_assessment",
    "timing_window_summary",
    "monitoring_plan",
)

_PLACEHOLDER_TOKENS = {
    "n/a",
    "na",
    "none",
    "placeholder",
    "todo",
    "tbd",
    "machine-generated",
    "auto",
}


def _parse_utc(ts: str) -> datetime:
    normalized = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_substantive_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        return False
    return normalized not in _PLACEHOLDER_TOKENS


def validate_proposal(proposal: dict[str, Any]) -> GuardDecision:
    """Validate the frozen proposal canon before any lifecycle logic is applied."""

    missing = [key for key in REQUIRED_PROPOSAL_FIELDS if key not in proposal]
    if missing:
        return GuardDecision(False, f"missing_required_fields:{','.join(missing)}")

    if proposal["lifecycle_state"] not in LIFECYCLE_STATES:
        return GuardDecision(False, "invalid_lifecycle_state")
    if proposal["approval_status"] not in APPROVAL_STATUSES:
        return GuardDecision(False, "invalid_approval_status")

    for key in ("proposal_id", "corr_id"):
        if not isinstance(proposal[key], str) or not proposal[key].strip():
            return GuardDecision(False, f"invalid_{key}")

    try:
        created_at = _parse_utc(proposal["created_at"])
        expires_at = _parse_utc(proposal["expires_at"])
    except Exception:
        return GuardDecision(False, "invalid_timestamp")

    if expires_at <= created_at:
        return GuardDecision(False, "expires_at_not_after_created_at")

    for field in _SUBSTANTIVE_TEXT_FIELDS:
        if not _is_substantive_text(proposal.get(field)):
            return GuardDecision(False, f"weak_review_content:{field}")

    lifecycle_state = proposal["lifecycle_state"]
    approval_status = proposal["approval_status"]
    rejection_reason = proposal.get("rejection_reason")
    failure_reason = proposal.get("failure_reason")
    timeout_reason = proposal.get("timeout_reason")

    if lifecycle_state == "rejected" or approval_status == "rejected":
        if not _is_substantive_text(rejection_reason):
            return GuardDecision(False, "rejection_reason_required")
    elif rejection_reason:
        return GuardDecision(False, "rejection_reason_present_without_rejected_state")

    if lifecycle_state == "timed_out":
        if not _is_substantive_text(timeout_reason):
            return GuardDecision(False, "timeout_reason_required")
        if approval_status != "not_approvable":
            return GuardDecision(False, "timed_out_requires_not_approvable")
    elif timeout_reason:
        return GuardDecision(False, "timeout_reason_present_without_timed_out_state")

    if lifecycle_state == "execution_failed":
        if not _is_substantive_text(failure_reason):
            return GuardDecision(False, "failure_reason_required")
    elif failure_reason:
        return GuardDecision(False, "failure_reason_present_without_failed_state")

    if lifecycle_state == "approved" and approval_status != "approved":
        return GuardDecision(False, "approved_state_requires_approved_status")
    if lifecycle_state == "pending_review" and approval_status != "pending":
        return GuardDecision(False, "pending_review_requires_pending_status")
    if lifecycle_state == "rejected" and approval_status != "rejected":
        return GuardDecision(False, "rejected_state_requires_rejected_status")

    return GuardDecision(True, "valid")


def is_display_receipt_current(
    receipts: list[dict[str, Any]],
    *,
    proposal_id: str,
    created_at: str,
) -> bool:
    """
    A display receipt is current only if it matches the exact proposal instance and
    was emitted after the proposal was created.
    """

    created_ts = _parse_utc(created_at)
    for receipt in receipts:
        if receipt.get("receipt_type") != "proposal_displayed":
            continue
        if receipt.get("proposal_id") != proposal_id:
            continue
        try:
            if _parse_utc(receipt["ts_utc"]) >= created_ts:
                return True
        except Exception:
            continue
    return False


def evaluate_material_decay(
    proposal: dict[str, Any],
    *,
    now: datetime,
    proof_inputs: dict[str, Any],
    max_age_seconds: dict[str, int],
) -> GuardDecision:
    """Deny by default if fit-for-action cannot be proven from bounded proof inputs."""

    proposal_check = validate_proposal(proposal)
    if not proposal_check.allowed:
        return proposal_check

    try:
        created_at = _parse_utc(proposal["created_at"])
        expires_at = _parse_utc(proposal["expires_at"])
    except Exception:
        return GuardDecision(False, "invalid_timestamp")

    if now >= expires_at:
        return GuardDecision(False, "expired")

    if created_at > now:
        return GuardDecision(False, "created_at_in_future")

    evidence_timestamps = proof_inputs.get("evidence_timestamps")
    if evidence_timestamps is not None and not evidence_timestamps:
        return GuardDecision(False, "missing_evidence_timestamps")

    required_inputs = list(REQUIRED_PROOF_INPUTS)
    if evidence_timestamps is not None:
        required_inputs.append("evidence_timestamps")

    for key in required_inputs:
        if key not in proof_inputs:
            return GuardDecision(False, f"missing_proof:{key}")
        value = proof_inputs[key]
        if value in (None, "", []):
            return GuardDecision(False, f"missing_proof:{key}")
        if isinstance(value, str):
            values = [value]
        elif isinstance(value, list):
            values = value
        else:
            return GuardDecision(False, f"invalid_proof_shape:{key}")

        ttl = max_age_seconds.get(key)
        if ttl is None:
            return GuardDecision(False, f"missing_ttl:{key}")

        for raw_ts in values:
            try:
                ts = _parse_utc(raw_ts)
            except Exception:
                return GuardDecision(False, f"invalid_proof_timestamp:{key}")
            if ts > now:
                return GuardDecision(False, f"contradictory_proof:{key}")
            age_seconds = (now - ts).total_seconds()
            if age_seconds > ttl:
                return GuardDecision(False, f"stale_proof:{key}")
            if ts < created_at:
                return GuardDecision(False, f"contradictory_proof:{key}")

    if proof_inputs.get("ambiguous") is True:
        return GuardDecision(False, "ambiguous_proof")

    return GuardDecision(True, "fit_for_action")


def apply_timeout_transition(
    proposal: dict[str, Any],
    *,
    now: datetime,
    proof_inputs: dict[str, Any],
    max_age_seconds: dict[str, int],
) -> tuple[dict[str, Any], GuardDecision]:
    """
    Transition to timed_out / not_approvable when action fitness cannot be proven.
    """

    fitness = evaluate_material_decay(
        proposal,
        now=now,
        proof_inputs=proof_inputs,
        max_age_seconds=max_age_seconds,
    )
    if fitness.allowed:
        return deepcopy(proposal), GuardDecision(True, "still_actionable")

    updated = deepcopy(proposal)
    updated["lifecycle_state"] = "timed_out"
    updated["approval_status"] = "not_approvable"
    updated["timeout_reason"] = fitness.reason
    return updated, GuardDecision(
        True,
        "timed_out",
        next_lifecycle_state="timed_out",
        next_approval_status="not_approvable",
    )
