from __future__ import annotations

import json
from pathlib import Path

from calyx.cbo.intent_pipeline.plan import build_plan, mint_work_envelope
from calyx.cbo.intent_pipeline.registry import get_intent_dir, save_intent_artifact, save_status
from calyx.kernel.contract import load_contract, validate_work_envelope
from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.paths import resolve_repo_root
from calyx.kernel.swarm_work_envelope import validate_swarm_extensions


def _valid_swarm_scope() -> dict:
    return {
        "swarm_run_id": "swarm-run-001",
        "task_intent": "Prepare schema-only swarm substrate validation.",
        "file_scope": {
            "read_paths": ["docs/planning/**", "calyx/kernel/**", "tests/**"],
            "write_paths": ["calyx/kernel/swarm_work_envelope.py", "tests/test_swarm_work_envelope.py"],
        },
        "tool_scope": ["read_files", "write_files"],
        "network_scope": {"mode": "deny", "allowlist": []},
        "success_criteria": ["Schema validates", "No worker execution enabled"],
        "worker_plan": [
            {
                "worker_id": "worker-01",
                "task_intent": "Validate swarm schema",
                "ownership_scope": {
                    "read_paths": ["docs/planning/**", "calyx/kernel/**"],
                    "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                    "deny_paths": ["runtime/**"],
                },
                "allowed_tool_classes": ["read_files", "write_files"],
                "network_scope": {"mode": "deny", "allowlist": []},
                "success_criteria": ["Validation helpers defined"],
            }
        ],
    }


def _valid_swarm_constraints() -> dict:
    return {
        "ownership_policy": "exclusive_write_scope",
        "overlapping_write_scope_declared": False,
        "requires_receipt_bundle": True,
        "requires_trace_graph": True,
        "reconciliation_required": True,
    }


def test_valid_minimal_swarm_envelope_is_accepted() -> None:
    scope = {"paths": ["calyx/kernel/**"], "swarm": _valid_swarm_scope()}
    constraints = {"timeout_seconds": 300, "swarm": _valid_swarm_constraints()}
    valid, errors = validate_swarm_extensions(scope, constraints)

    assert valid is True
    assert errors == []


def test_invalid_swarm_envelope_missing_required_fields_is_rejected() -> None:
    scope = {"swarm": {"swarm_run_id": "swarm-run-001"}}
    constraints = {"swarm": _valid_swarm_constraints()}
    valid, errors = validate_swarm_extensions(scope, constraints)

    assert valid is False
    assert any("scope.swarm missing required fields" in error for error in errors)


def test_overlapping_write_scopes_without_declaration_are_rejected() -> None:
    swarm_scope = _valid_swarm_scope()
    swarm_scope["worker_plan"].append(
        {
            "worker_id": "worker-02",
            "task_intent": "Also write same file",
            "ownership_scope": {
                "read_paths": ["calyx/kernel/**"],
                "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
                "deny_paths": ["runtime/**"],
            },
            "allowed_tool_classes": ["read_files"],
            "network_scope": {"mode": "deny", "allowlist": []},
            "success_criteria": ["Should be rejected"],
        }
    )
    valid, errors = validate_swarm_extensions(
        {"swarm": swarm_scope},
        {"swarm": _valid_swarm_constraints()},
    )

    assert valid is False
    assert any("overlaps with worker" in error for error in errors)


def test_tool_scope_violation_is_rejected() -> None:
    swarm_scope = _valid_swarm_scope()
    swarm_scope["worker_plan"][0]["allowed_tool_classes"] = ["run_shell"]
    valid, errors = validate_swarm_extensions(
        {"swarm": swarm_scope},
        {"swarm": _valid_swarm_constraints()},
    )

    assert valid is False
    assert any("allowed_tool_classes exceed envelope tool_scope" in error for error in errors)


def test_non_swarm_work_envelope_still_validates_unchanged() -> None:
    contract, contract_sha = load_contract(resolve_repo_root() / "CALYX_CONTRACT.yaml")
    envelope = WorkEnvelope(
        envelope_id="env-001",
        intent_id="intent-001",
        task_type="doc_update",
        scope={"paths": ["docs/**"]},
        constraints={"timeout_seconds": 120},
        ts_utc="2026-04-16T00:00:00+00:00",
        source="discord",
        requires_human_approval=False,
        approval_token=None,
    )

    allowed, reason = validate_work_envelope(envelope, contract, contract_sha)
    assert allowed is True
    assert reason is None


def test_build_plan_rejects_invalid_swarm_schema(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-swarm-invalid"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "envelope_id": "env-swarm-invalid",
            "intent": "Prepare a swarm schema validation plan.",
            "task_type": "doc_update",
            "scope": {"swarm": {"swarm_run_id": "swarm-run-001"}},
            "constraints": {"swarm": _valid_swarm_constraints()},
            "source": "discord",
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    plan = build_plan(intent_id, runtime_dir)
    status_path = get_intent_dir(intent_id, runtime_dir) / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert plan is None
    assert status["reason"] == "phase0_swarm_schema_invalid"
    assert status["swarm_schema_status"] == "needs_clarification"


def test_mint_work_envelope_emits_static_worker_leases_for_valid_swarm(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-swarm-phase1"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "envelope_id": "env-swarm-phase1",
            "intent": "Prepare static worker leases for a governed swarm envelope.",
            "task_type": "doc_update",
            "scope": {"paths": ["calyx/kernel/**"], "swarm": _valid_swarm_scope()},
            "constraints": {"timeout_seconds": 300, "swarm": _valid_swarm_constraints()},
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    envelope = mint_work_envelope(intent_id, runtime_dir, repo_root=resolve_repo_root())
    status_path = get_intent_dir(intent_id, runtime_dir) / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    leases_path = Path(status["worker_leases_path"])
    ownership_map_path = Path(status["ownership_map_path"])
    lifecycle_path = Path(status["lease_lifecycle_path"])
    trace_graph_path = Path(status["trace_graph_path"])
    receipt_bundle_path = Path(status["receipt_bundle_path"])
    sandbox_run_dir = runtime_dir / "cbo" / "swarm" / "swarm-run-001"
    receipt_path = Path(status["worker_lease_receipt_path"])
    work_outbox_path = runtime_dir / "cbo" / "work_outbox" / "env-swarm-phase1.json"
    lease_artifact = json.loads(leases_path.read_text(encoding="utf-8"))
    ownership_map = json.loads(ownership_map_path.read_text(encoding="utf-8"))
    lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    trace_graph = json.loads(trace_graph_path.read_text(encoding="utf-8"))
    receipt_bundle = json.loads(receipt_bundle_path.read_text(encoding="utf-8"))
    lease_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    sandbox_manifest_refs = receipt_bundle["sandbox_manifest_refs"]
    snapshot_refs = receipt_bundle["snapshot_refs"]

    assert envelope is not None
    assert status["swarm_lease_status"] == "static_issued"
    assert status["swarm_ownership_status"] == "validated"
    assert status["worker_lease_count"] == 1
    assert status["ownership_conflict_count"] == 0
    assert status["worker_lease_transition_receipt_count"] == 1
    assert status["worker_lease_terminal_count"] == 0
    assert status["sandbox_manifest_count"] == 1
    assert status["snapshot_count"] == 1
    assert status["trace_node_count"] == 5
    assert status["receipt_bundle_status"] == "complete"
    assert work_outbox_path.exists()
    assert leases_path.exists()
    assert ownership_map_path.exists()
    assert lifecycle_path.exists()
    assert trace_graph_path.exists()
    assert receipt_bundle_path.exists()
    assert receipt_path.exists()
    assert (sandbox_run_dir / "sandboxes").exists()
    assert (sandbox_run_dir / "snapshots").exists()
    assert lease_artifact["lease_state"] == "proposed"
    assert ownership_map["worker_count"] == 1
    assert lifecycle["lease_count"] == 1
    assert lifecycle["leases"][0]["current_state"] == "proposed"
    assert trace_graph["root_node_id"] == "planner::swarm-run-001"
    assert len([node for node in trace_graph["nodes"] if node["action_type"] == "sandbox_prepare"]) == 1
    assert len([node for node in trace_graph["nodes"] if node["action_type"] == "snapshot_pre_execution"]) == 1
    assert receipt_bundle["bundle_status"] == "complete"
    assert len(sandbox_manifest_refs) == 1
    assert len(snapshot_refs) == 1
    assert Path(sandbox_manifest_refs[0]).exists()
    assert Path(snapshot_refs[0]).exists()
    assert lease_receipt["receipt_type"] == "swarm.worker_lease.issuance_static"
    assert lease_receipt["worker_execution_enabled"] is False


def test_mint_non_swarm_envelope_does_not_emit_worker_leases(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-non-swarm-phase1"
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "envelope_id": "env-non-swarm-phase1",
            "intent": "Update docs without swarm extensions.",
            "task_type": "doc_update",
            "scope": {"paths": ["docs/**"]},
            "constraints": {"timeout_seconds": 120},
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    envelope = mint_work_envelope(intent_id, runtime_dir)
    status_path = get_intent_dir(intent_id, runtime_dir) / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert envelope is not None
    assert status["status"] == "minted"
    assert "worker_leases_path" not in status
    assert not (runtime_dir / "cbo" / "swarm").exists()


def test_mint_work_envelope_blocks_invalid_swarm_ownership_before_artifact_emission(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    intent_id = "intent-swarm-phase2-invalid"
    swarm_scope = _valid_swarm_scope()
    swarm_scope["worker_plan"].append(
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
            "success_criteria": ["Conflict should block mint"],
        }
    )
    constraints = _valid_swarm_constraints()
    constraints["overlapping_write_scope_declared"] = True
    save_intent_artifact(
        intent_id,
        runtime_dir,
        {
            "envelope_id": "env-swarm-phase2-invalid",
            "intent": "Attempt invalid overlapping static leases.",
            "task_type": "doc_update",
            "scope": {"paths": ["calyx/kernel/**"], "swarm": swarm_scope},
            "constraints": {"timeout_seconds": 300, "swarm": constraints},
            "source": "discord",
            "requires_human_approval": False,
            "approval_token": None,
        },
    )
    save_status(intent_id, runtime_dir, {"status": "ready"})

    envelope = mint_work_envelope(intent_id, runtime_dir)
    status_path = get_intent_dir(intent_id, runtime_dir) / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))

    assert envelope is None
    assert status["reason"] == "phase2_swarm_ownership_conflict"
    assert status["swarm_ownership_status"] == "needs_clarification"
    assert not (runtime_dir / "cbo" / "swarm").exists()
    assert not (runtime_dir / "cbo" / "work_outbox").exists()
