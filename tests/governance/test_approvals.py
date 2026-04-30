from __future__ import annotations

from datetime import datetime, timezone

from calyx.governance.approvals import can_approve_proposal, can_reject_proposal
from calyx.governance.receipts import make_receipt


def _proposal() -> dict:
    return {
        "proposal_id": "p1",
        "corr_id": "c1",
        "created_at": "2026-03-27T10:00:00Z",
        "expires_at": "2026-03-27T10:30:00Z",
        "lifecycle_state": "pending_review",
        "approval_status": "pending",
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
    }


def _operator_path() -> dict:
    return {
        "surface": "workstation_console",
        "session_id": "sess-1",
        "interaction_kind": "approve_command",
        "operator_present": True,
    }


def _display_receipt(proposal_id: str = "p1") -> dict:
    return make_receipt(
        receipt_type="proposal_displayed",
        corr_id="c1",
        proposal_id=proposal_id,
        component="console",
        ts_utc="2026-03-27T10:01:00Z",
    )


def test_can_approve_requires_display_receipt() -> None:
    decision = can_approve_proposal(
        _proposal(),
        receipts=[],
        operator_path=_operator_path(),
        now=datetime(2026, 3, 27, 10, 2, tzinfo=timezone.utc),
        on_shift=True,
        halted=False,
        caution_active=False,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:01:30Z",
            "account_snapshot_ts": "2026-03-27T10:01:30Z",
            "policy_snapshot_ts": "2026-03-27T10:01:30Z",
            "budget_posture_ts": "2026-03-27T10:01:30Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
    )
    assert decision.allowed is False
    assert decision.reason == "proposal_not_displayed"


def test_can_approve_denies_halt_even_if_displayed() -> None:
    decision = can_approve_proposal(
        _proposal(),
        receipts=[_display_receipt()],
        operator_path=_operator_path(),
        now=datetime(2026, 3, 27, 10, 2, tzinfo=timezone.utc),
        on_shift=True,
        halted=True,
        caution_active=False,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:01:30Z",
            "account_snapshot_ts": "2026-03-27T10:01:30Z",
            "policy_snapshot_ts": "2026-03-27T10:01:30Z",
            "budget_posture_ts": "2026-03-27T10:01:30Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
    )
    assert decision.allowed is False
    assert decision.reason == "halted"


def test_can_approve_denies_superseded_display_receipt() -> None:
    decision = can_approve_proposal(
        _proposal(),
        receipts=[_display_receipt("old-proposal")],
        operator_path=_operator_path(),
        now=datetime(2026, 3, 27, 10, 2, tzinfo=timezone.utc),
        on_shift=True,
        halted=False,
        caution_active=False,
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:01:30Z",
            "account_snapshot_ts": "2026-03-27T10:01:30Z",
            "policy_snapshot_ts": "2026-03-27T10:01:30Z",
            "budget_posture_ts": "2026-03-27T10:01:30Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
    )
    assert decision.allowed is False
    assert decision.reason == "proposal_not_displayed"


def test_can_reject_requires_reason() -> None:
    decision = can_reject_proposal(_proposal(), operator_path=_operator_path(), reason="")
    assert decision.allowed is False
    assert decision.reason == "rejection_reason_required"
