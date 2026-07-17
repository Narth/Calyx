from __future__ import annotations

from calyx.governance.state_model import derive_ui_status


def test_derive_ui_status_actionable_for_approved_proposal() -> None:
    proposal = {"lifecycle_state": "approved", "approval_status": "approved"}
    assert derive_ui_status(proposal, halted=False, caution_active=False) == "actionable"


def test_derive_ui_status_halt_overrides_actionable() -> None:
    proposal = {"lifecycle_state": "approved", "approval_status": "approved"}
    assert derive_ui_status(proposal, halted=True, caution_active=False) == "not_actionable_halted"


def test_derive_ui_status_caution_overrides_everything() -> None:
    proposal = {"lifecycle_state": "approved", "approval_status": "approved"}
    assert derive_ui_status(proposal, halted=False, caution_active=True) == "not_actionable_caution"


def test_derive_ui_status_consumed_is_not_actionable() -> None:
    proposal = {"lifecycle_state": "consumed", "approval_status": "approved"}
    assert derive_ui_status(proposal, halted=False, caution_active=False) == "not_actionable_consumed"
