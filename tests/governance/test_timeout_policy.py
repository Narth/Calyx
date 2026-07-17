from __future__ import annotations

from datetime import datetime, timezone

from calyx.governance.execution_gate import can_accept_execution_attempt, consume_approved_proposal
from calyx.governance.receipts import make_receipt


def _approved_proposal() -> dict:
    return {
        "proposal_id": "p1",
        "corr_id": "c1",
        "created_at": "2026-03-27T10:00:00Z",
        "expires_at": "2026-03-27T10:30:00Z",
        "lifecycle_state": "approved",
        "approval_status": "approved",
        "rejection_reason": None,
        "failure_reason": None,
        "timeout_reason": None,
        "rationale_summary": "Bounded operator review is warranted due to fresh market movement.",
        "evidence_summary": "Recent market and account snapshots support review.",
        "thesis_summary": "Short-duration bounded opportunity remains open for review.",
        "freshness_assessment": "All required evidence is current enough for review.",
        "timing_window_summary": "Review remains valid for the next several minutes.",
        "monitoring_plan": "If later approved and filled, monitor until bounded posture resolves.",
        "policy_snapshot": {"version": "p1"},
        "budget_posture": {"version": "b1"},
        "market_id": "m1",
        "action": "buy",
        "max_price_cents": 45,
        "max_spend_cents": 800,
    }


def _approval_receipt() -> dict:
    return make_receipt(
        receipt_type="approval_granted",
        corr_id="c1",
        proposal_id="p1",
        component="console",
        operator_path={
            "surface": "workstation_console",
            "session_id": "sess-1",
            "interaction_kind": "approve_command",
            "operator_present": True,
        },
    )


def test_execution_attempt_requires_prior_approval_receipt() -> None:
    decision = can_accept_execution_attempt(
        _approved_proposal(),
        receipts=[],
        now=datetime(2026, 3, 27, 10, 5, tzinfo=timezone.utc),
        halted=False,
        caution_active=False,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:04:00Z",
            "account_snapshot_ts": "2026-03-27T10:04:00Z",
            "policy_snapshot_ts": "2026-03-27T10:04:00Z",
            "budget_posture_ts": "2026-03-27T10:04:00Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
        request_params={"action": "buy", "max_price_cents": 45, "max_spend_cents": 800},
        locked_fields=("action", "max_price_cents", "max_spend_cents"),
    )
    assert decision.allowed is False
    assert decision.reason == "missing_prior_approval_receipt"


def test_execution_attempt_consumes_at_gate_acceptance() -> None:
    decision = can_accept_execution_attempt(
        _approved_proposal(),
        receipts=[_approval_receipt()],
        now=datetime(2026, 3, 27, 10, 5, tzinfo=timezone.utc),
        halted=False,
        caution_active=False,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:04:00Z",
            "account_snapshot_ts": "2026-03-27T10:04:00Z",
            "policy_snapshot_ts": "2026-03-27T10:04:00Z",
            "budget_posture_ts": "2026-03-27T10:04:00Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
        request_params={"action": "buy", "max_price_cents": 45, "max_spend_cents": 800},
        locked_fields=("action", "max_price_cents", "max_spend_cents"),
    )
    assert decision.allowed is True
    assert decision.next_lifecycle_state == "consumed"
    updated = consume_approved_proposal(_approved_proposal())
    assert updated["lifecycle_state"] == "consumed"


def test_execution_attempt_denied_during_global_caution() -> None:
    decision = can_accept_execution_attempt(
        _approved_proposal(),
        receipts=[_approval_receipt()],
        now=datetime(2026, 3, 27, 10, 5, tzinfo=timezone.utc),
        halted=False,
        caution_active=True,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:04:00Z",
            "account_snapshot_ts": "2026-03-27T10:04:00Z",
            "policy_snapshot_ts": "2026-03-27T10:04:00Z",
            "budget_posture_ts": "2026-03-27T10:04:00Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
        request_params={"action": "buy", "max_price_cents": 45, "max_spend_cents": 800},
        locked_fields=("action", "max_price_cents", "max_spend_cents"),
    )
    assert decision.allowed is False
    assert decision.reason == "global_post_attempt_caution"
