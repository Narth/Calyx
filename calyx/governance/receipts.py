"""Canonical governance receipt helpers and invariants."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from calyx.kernel.receipts import append_receipt_line

from .state_model import GuardDecision

RECEIPT_TYPES = frozenset(
    {
        "proposal_created",
        "proposal_displayed",
        "approval_granted",
        "approval_rejected",
        "proposal_timed_out",
        "execution_attempted",
        "execution_succeeded",
        "execution_failed",
        "reconciliation_completed",
        "halt_invoked",
        "policy_violation_refused",
    }
)

_OUTCOME_BY_TYPE = {
    "proposal_created": "recorded",
    "proposal_displayed": "displayed",
    "approval_granted": "approved",
    "approval_rejected": "rejected",
    "proposal_timed_out": "timed_out",
    "execution_attempted": "attempted",
    "execution_succeeded": "succeeded",
    "execution_failed": "failed",
    "reconciliation_completed": "reconciled",
    "halt_invoked": "halted",
    "policy_violation_refused": "refused",
}


def validate_receipt(receipt: dict[str, Any]) -> GuardDecision:
    """Validate canonical receipt-family invariants."""

    required = ("receipt_type", "corr_id", "ts_utc", "component", "outcome_status")
    missing = [key for key in required if key not in receipt]
    if missing:
        return GuardDecision(False, f"missing_receipt_fields:{','.join(missing)}")

    receipt_type = receipt["receipt_type"]
    if receipt_type not in RECEIPT_TYPES:
        return GuardDecision(False, "invalid_receipt_type")

    if receipt["outcome_status"] != _OUTCOME_BY_TYPE[receipt_type]:
        return GuardDecision(False, "receipt_type_outcome_mismatch")

    proposal_linked = {
        "proposal_created",
        "proposal_displayed",
        "approval_granted",
        "approval_rejected",
        "proposal_timed_out",
        "execution_attempted",
        "execution_succeeded",
        "execution_failed",
        "reconciliation_completed",
    }
    if receipt_type in proposal_linked and not receipt.get("proposal_id"):
        return GuardDecision(False, "proposal_id_required")

    if receipt_type in {"approval_granted", "approval_rejected"}:
        operator_path = receipt.get("operator_path")
        if not isinstance(operator_path, dict):
            return GuardDecision(False, "operator_path_required")
        if operator_path.get("operator_present") is not True:
            return GuardDecision(False, "operator_present_required")

    if receipt_type in {"approval_rejected", "proposal_timed_out", "execution_failed", "policy_violation_refused"}:
        reason = receipt.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return GuardDecision(False, "reason_required")

    return GuardDecision(True, "valid")


def make_receipt(
    *,
    receipt_type: str,
    corr_id: str,
    component: str,
    proposal_id: str | None = None,
    operator_path: dict[str, Any] | None = None,
    reason: str | None = None,
    ts_utc: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "receipt_type": receipt_type,
        "corr_id": corr_id,
        "proposal_id": proposal_id,
        "ts_utc": ts_utc or datetime.now(timezone.utc).isoformat(),
        "component": component,
        "outcome_status": _OUTCOME_BY_TYPE[receipt_type],
    }
    if operator_path is not None:
        payload["operator_path"] = operator_path
    if reason is not None:
        payload["reason"] = reason
    if extra:
        payload.update(extra)
    return payload


def emit_governance_receipt(
    receipt: dict[str, Any],
    *,
    repo_root: Path | None = None,
    prefix: str = "governance",
) -> Path:
    validation = validate_receipt(receipt)
    if not validation.allowed:
        raise ValueError(validation.reason)
    return append_receipt_line(
        {
            "timestamp_utc": receipt["ts_utc"],
            "phase": "governance",
            "status": receipt["outcome_status"],
            "receipt_type": receipt["receipt_type"],
            **receipt,
        },
        prefix=prefix,
        repo_root=repo_root,
    )
