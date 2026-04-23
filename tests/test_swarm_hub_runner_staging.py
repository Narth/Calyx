from __future__ import annotations

import json
from pathlib import Path


def _valid_swarm_envelope():
    from calyx.kernel.envelope import WorkEnvelope

    return WorkEnvelope(
        envelope_id="env-swarm-hub",
        intent_id="intent-swarm-hub",
        task_type="doc_update",
        scope={
            "paths": ["calyx/kernel/**"],
            "swarm": {
                "swarm_run_id": "swarm-run-hub",
                "task_intent": "Validate-only swarm envelope",
                "file_scope": {
                    "read_paths": ["docs/planning/**", "calyx/kernel/**", "tests/**"],
                    "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                },
                "tool_scope": ["read_files", "write_files"],
                "network_scope": {"mode": "deny", "allowlist": []},
                "success_criteria": ["Validation passes"],
                "worker_plan": [
                    {
                        "worker_id": "worker-01",
                        "task_intent": "Prepare patch",
                        "ownership_scope": {
                            "read_paths": ["calyx/kernel/**"],
                            "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                            "deny_paths": ["runtime/**"],
                        },
                        "allowed_tool_classes": ["read_files", "write_files"],
                        "network_scope": {"mode": "deny", "allowlist": []},
                        "success_criteria": ["Patch prepared"],
                    }
                ],
            },
        },
        constraints={
            "timeout_seconds": 300,
            "swarm": {
                "ownership_policy": "exclusive_write_scope",
                "overlapping_write_scope_declared": False,
                "requires_receipt_bundle": True,
                "requires_trace_graph": True,
                "reconciliation_required": True,
            },
        },
        ts_utc="2026-04-16T00:00:00Z",
        source="discord",
        requires_human_approval=False,
        approval_token=None,
    )


def _invalid_overlap_swarm_envelope():
    envelope = _valid_swarm_envelope()
    envelope.scope["swarm"]["worker_plan"].append(
        {
            "worker_id": "worker-02",
            "task_intent": "Overlap same write path",
            "ownership_scope": {
                "read_paths": ["calyx/kernel/**"],
                "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                "deny_paths": ["runtime/**"],
            },
            "allowed_tool_classes": ["read_files"],
            "network_scope": {"mode": "deny", "allowlist": []},
            "success_criteria": ["Conflict surfaced"],
        }
    )
    envelope.constraints["swarm"]["overlapping_write_scope_declared"] = True
    return envelope


def _write_minted_status(runtime_dir: Path, envelope) -> None:
    intent_dir = runtime_dir / "cbo" / "intents" / envelope.intent_id
    intent_dir.mkdir(parents=True, exist_ok=True)
    with open(intent_dir / "status.json", "w", encoding="utf-8") as handle:
        json.dump({"status": "minted", "work_envelope_hash": envelope.deterministic_hash()}, handle)


def test_run_work_envelope_denies_swarm_execution_in_validate_only_mode(tmp_path: Path, monkeypatch) -> None:
    from calyx.execution.hub_runner import run_work_envelope

    runtime_dir = tmp_path / "runtime"
    envelope = _valid_swarm_envelope()
    _write_minted_status(runtime_dir, envelope)
    monkeypatch.setenv("CALYX_RUNTIME_DIR", str(runtime_dir))

    ok, err = run_work_envelope(envelope, repo_root=Path(__file__).resolve().parents[1])

    assert ok is False
    assert err == "swarm_execution_not_enabled_phase2"


def test_run_work_envelope_denies_invalid_swarm_lease_set_before_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from calyx.execution.hub_runner import run_work_envelope

    runtime_dir = tmp_path / "runtime"
    envelope = _invalid_overlap_swarm_envelope()
    _write_minted_status(runtime_dir, envelope)
    monkeypatch.setenv("CALYX_RUNTIME_DIR", str(runtime_dir))

    ok, err = run_work_envelope(envelope, repo_root=Path(__file__).resolve().parents[1])

    assert ok is False
    assert err == "invalid_swarm_lease_set"
