from __future__ import annotations

from calyx.governance.receipts import make_receipt, validate_receipt


def test_approval_receipt_requires_operator_path() -> None:
    receipt = make_receipt(
        receipt_type="approval_granted",
        corr_id="c1",
        proposal_id="p1",
        component="console",
    )
    decision = validate_receipt(receipt)
    assert decision.allowed is False
    assert decision.reason == "operator_path_required"


def test_receipt_type_and_outcome_must_match() -> None:
    receipt = make_receipt(
        receipt_type="proposal_created",
        corr_id="c1",
        proposal_id="p1",
        component="console",
    )
    receipt["outcome_status"] = "approved"
    decision = validate_receipt(receipt)
    assert decision.allowed is False
    assert decision.reason == "receipt_type_outcome_mismatch"


def test_execution_failed_requires_reason() -> None:
    receipt = make_receipt(
        receipt_type="execution_failed",
        corr_id="c1",
        proposal_id="p1",
        component="gate",
    )
    decision = validate_receipt(receipt)
    assert decision.allowed is False
    assert decision.reason == "reason_required"
