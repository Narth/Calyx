from __future__ import annotations

from datetime import datetime, timezone

from calyx.governance.proposals import apply_timeout_transition, validate_proposal


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


def test_validate_proposal_accepts_valid_pending_review() -> None:
    decision = validate_proposal(_proposal())
    assert decision.allowed is True


def test_validate_proposal_rejects_placeholder_review_content() -> None:
    proposal = _proposal()
    proposal["thesis_summary"] = "TBD"
    decision = validate_proposal(proposal)
    assert decision.allowed is False
    assert decision.reason == "weak_review_content:thesis_summary"


def test_apply_timeout_transition_marks_missing_proof_as_timed_out() -> None:
    proposal = _proposal()
    updated, decision = apply_timeout_transition(
        proposal,
        now=datetime(2026, 3, 27, 10, 5, tzinfo=timezone.utc),
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:04:00Z",
            "account_snapshot_ts": "2026-03-27T10:04:00Z",
            "policy_snapshot_ts": "2026-03-27T10:04:00Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 300,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
    )
    assert decision.allowed is True
    assert updated["lifecycle_state"] == "timed_out"
    assert updated["approval_status"] == "not_approvable"
    assert updated["timeout_reason"] == "missing_proof:budget_posture_ts"


def test_apply_timeout_transition_marks_stale_proof_as_timed_out() -> None:
    proposal = _proposal()
    updated, _ = apply_timeout_transition(
        proposal,
        now=datetime(2026, 3, 27, 10, 10, tzinfo=timezone.utc),
        proof_inputs={
            "market_snapshot_ts": "2026-03-27T10:00:00Z",
            "account_snapshot_ts": "2026-03-27T10:09:00Z",
            "policy_snapshot_ts": "2026-03-27T10:09:00Z",
            "budget_posture_ts": "2026-03-27T10:09:00Z",
        },
        max_age_seconds={
            "market_snapshot_ts": 60,
            "account_snapshot_ts": 300,
            "policy_snapshot_ts": 300,
            "budget_posture_ts": 300,
        },
    )
    assert updated["lifecycle_state"] == "timed_out"
    assert updated["timeout_reason"] == "stale_proof:market_snapshot_ts"
