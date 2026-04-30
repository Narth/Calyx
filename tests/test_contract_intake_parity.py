"""WO_GOVERNANCE_CONTRACT_INTAKE_PARITY: Assert Discord intake allowlists derive from contract."""
from __future__ import annotations

from pathlib import Path

import pytest


def test_intake_allowlists_match_contract() -> None:
    """Intake must derive allowed_tasks and allowed_sources from CALYX_CONTRACT.yaml."""
    repo_root = Path(__file__).resolve().parents[1]
    contract_path = repo_root / "CALYX_CONTRACT.yaml"
    if not contract_path.exists():
        pytest.skip("CALYX_CONTRACT.yaml not found")

    from calyx.kernel.contract import load_contract

    contract, _ = load_contract(contract_path)
    contract_tasks = set(contract.get("allowed_tasks") or [])
    contract_sources = set((contract.get("allowed_sources") or {}).get("phase_b") or [])

    # DiscordIntake._get_contract_allowlists should return same
    from calyx.cbo.discord_intake import DiscordIntake

    config_path = repo_root / "runtime" / "discord_config.json"
    intake = DiscordIntake(config_path, repo_root)
    intake_tasks, intake_sources = intake._get_contract_allowlists()

    assert set(intake_tasks) == contract_tasks, "Intake allowed_tasks must match contract"
    assert set(intake_sources) == contract_sources, "Intake allowed_sources must match contract (phase_b)"


def test_intake_rejects_contract_disallowed_task() -> None:
    """Intake must reject task_type not in contract."""
    repo_root = Path(__file__).resolve().parents[1]
    from calyx.cbo.discord_intake import DiscordIntake

    config_path = repo_root / "runtime" / "discord_config.json"
    intake = DiscordIntake(config_path, repo_root)
    envelope = {
        "envelope_id": "test-123",
        "ts_utc": "2026-01-01T00:00:00Z",
        "source": "discord",
        "author": "123",
        "channel_id": "456",
        "message_id": "789",
        "intent": "test",
        "task_type": "arbitrary_unknown_task",
        "scope": {},
        "constraints": {},
        "requires_human_approval": False,
        "evidence_requirements": {},
    }
    valid, err = intake._validate_envelope(envelope)
    assert not valid
    assert "invalid_task_type" in (err or "")


def test_intake_accepts_contract_allowed_task() -> None:
    """Intake must accept repo_readonly_review (contract Phase 4 task)."""
    repo_root = Path(__file__).resolve().parents[1]
    contract_path = repo_root / "CALYX_CONTRACT.yaml"
    if not contract_path.exists():
        pytest.skip("CALYX_CONTRACT.yaml not found")

    from calyx.cbo.discord_intake import DiscordIntake

    config_path = repo_root / "runtime" / "discord_config.json"
    intake = DiscordIntake(config_path, repo_root)
    envelope = {
        "envelope_id": "test-456",
        "ts_utc": "2026-01-01T00:00:00Z",
        "source": "discord",
        "author": "123",
        "channel_id": "456",
        "message_id": "789",
        "intent": "test",
        "task_type": "repo_readonly_review",
        "scope": {},
        "constraints": {},
        "requires_human_approval": False,
        "evidence_requirements": {},
    }
    valid, err = intake._validate_envelope(envelope)
    assert valid, f"repo_readonly_review should be allowed: {err}"
