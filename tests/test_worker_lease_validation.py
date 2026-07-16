from __future__ import annotations

import json
from pathlib import Path

from calyx.kernel.envelope import WorkEnvelope
from calyx.kernel.swarm_lease import (
    WORKER_LEASE_SCHEMA,
    WORKER_LEASE_SCHEMA_VERSION,
    build_static_worker_leases_artifact,
    build_worker_ownership_map,
    issue_static_worker_leases,
    transition_worker_lease_state,
    validate_static_worker_lease_set,
    validate_worker_lease,
)


def _envelope_scope_swarm() -> dict:
    return {
        "swarm_run_id": "swarm-run-001",
        "file_scope": {
            "read_paths": ["docs/planning/**", "calyx/kernel/**", "tests/**"],
            "write_paths": ["calyx/kernel/swarm_work_envelope.py", "tests/test_worker_lease_validation.py"],
        },
        "tool_scope": ["read_files", "write_files"],
        "network_scope": {"mode": "deny", "allowlist": []},
    }


def _valid_worker_lease() -> dict:
    return {
        "schema": WORKER_LEASE_SCHEMA,
        "schema_version": WORKER_LEASE_SCHEMA_VERSION,
        "swarm_run_id": "swarm-run-001",
        "work_envelope_id": "env-001",
        "lease_id": "lease-001",
        "worker_id": "worker-01",
        "lease_state": "proposed",
        "issued_at_utc": "2026-04-16T00:00:00Z",
        "expires_at_utc": "2026-04-16T00:10:00Z",
        "max_runtime_sec": 600,
        "token_budget": {"max_tokens": 4000},
        "compute_budget": {"max_tool_calls": 20},
        "ownership_scope": {
            "read_paths": ["docs/planning/**", "calyx/kernel/**"],
            "write_paths": ["calyx/kernel/swarm_work_envelope.py"],
            "deny_paths": ["runtime/**"],
        },
        "allowed_tool_classes": ["read_files", "write_files"],
        "network_scope": {"mode": "deny", "allowlist": []},
        "success_criteria": ["Schema validation passes"],
        "approval_context": {"requires_human_approval": False},
        "revocation_reason": "",
        "notes": "Phase 0 static lease only",
    }


def _valid_worker_plan_entry() -> dict:
    lease = _valid_worker_lease()
    return {
        "worker_id": lease["worker_id"],
        "task_intent": "Prepare static lease artifact",
        "ownership_scope": lease["ownership_scope"],
        "allowed_tool_classes": lease["allowed_tool_classes"],
        "network_scope": lease["network_scope"],
        "success_criteria": ["Lease derived"],
    }


def _valid_swarm_constraints() -> dict:
    return {
        "ownership_policy": "exclusive_write_scope",
        "overlapping_write_scope_declared": False,
        "requires_receipt_bundle": True,
        "requires_trace_graph": True,
        "reconciliation_required": True,
    }


def _valid_swarm_envelope() -> WorkEnvelope:
    return WorkEnvelope(
        envelope_id="env-swarm-phase1",
        intent_id="intent-swarm-phase1",
        task_type="doc_update",
        scope={
            "paths": ["calyx/kernel/**"],
            "swarm": {
                **_envelope_scope_swarm(),
                "task_intent": "Static lease issuance",
                "success_criteria": ["Lease issuance recorded"],
                "worker_plan": [_valid_worker_plan_entry()],
            },
        },
        constraints={
            "timeout_seconds": 600,
            "swarm": _valid_swarm_constraints(),
        },
        ts_utc="2026-04-16T00:00:00Z",
        source="discord",
        requires_human_approval=False,
        approval_token=None,
    )


def _overlapping_swarm_envelope(*, overlap_declared: bool) -> WorkEnvelope:
    shared_path = "calyx/kernel/swarm_work_envelope.py"
    return WorkEnvelope(
        envelope_id="env-swarm-overlap",
        intent_id="intent-swarm-overlap",
        task_type="doc_update",
        scope={
            "paths": ["calyx/kernel/**"],
            "swarm": {
                **_envelope_scope_swarm(),
                "task_intent": "Overlap validation",
                "success_criteria": ["Conflict detection works"],
                "worker_plan": [
                    _valid_worker_plan_entry(),
                    {
                        "worker_id": "worker-02",
                        "task_intent": "Attempt same write path",
                        "ownership_scope": {
                            "read_paths": ["calyx/kernel/**"],
                            "write_paths": [shared_path],
                            "deny_paths": ["runtime/**"],
                        },
                        "allowed_tool_classes": ["read_files", "write_files"],
                        "network_scope": {"mode": "deny", "allowlist": []},
                        "success_criteria": ["Conflict surfaced"],
                    },
                ],
            },
        },
        constraints={
            "timeout_seconds": 600,
            "swarm": {
                "ownership_policy": "exclusive_write_scope",
                "overlapping_write_scope_declared": overlap_declared,
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


def test_valid_worker_lease_within_envelope_scope_is_accepted() -> None:
    valid, errors = validate_worker_lease(
        _valid_worker_lease(),
        envelope_scope_swarm=_envelope_scope_swarm(),
    )

    assert valid is True
    assert errors == []


def test_worker_lease_schema_mismatch_is_rejected() -> None:
    lease = _valid_worker_lease()
    lease["schema"] = "station.swarm.worker_lease.v0"
    valid, errors = validate_worker_lease(lease, envelope_scope_swarm=_envelope_scope_swarm())

    assert valid is False
    assert any("worker_lease.schema must equal" in error for error in errors)


def test_worker_lease_exceeding_envelope_scope_is_rejected() -> None:
    lease = _valid_worker_lease()
    lease["ownership_scope"]["write_paths"] = ["calyx/kernel/contract.py"]
    valid, errors = validate_worker_lease(lease, envelope_scope_swarm=_envelope_scope_swarm())

    assert valid is False
    assert any("ownership_scope.write_paths exceed envelope scope" in error for error in errors)


def test_worker_lease_tool_scope_violation_is_rejected() -> None:
    lease = _valid_worker_lease()
    lease["allowed_tool_classes"] = ["read_files", "write_files", "run_shell"]
    valid, errors = validate_worker_lease(lease, envelope_scope_swarm=_envelope_scope_swarm())

    assert valid is False
    assert any("allowed_tool_classes exceed envelope tool_scope" in error for error in errors)


def test_worker_lease_network_scope_violation_is_rejected() -> None:
    lease = _valid_worker_lease()
    lease["network_scope"] = {"mode": "allowlist", "allowlist": ["api.example.com"]}
    valid, errors = validate_worker_lease(lease, envelope_scope_swarm=_envelope_scope_swarm())

    assert valid is False
    assert any("network_scope cannot widen envelope deny posture" in error for error in errors)


def test_build_static_worker_leases_artifact_derives_proposed_leases() -> None:
    artifact = build_static_worker_leases_artifact(
        _valid_swarm_envelope(),
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    assert artifact["schema"] == "station.swarm.worker_leases.v1"
    assert artifact["lease_state"] == "proposed"
    assert artifact["worker_count"] == 1
    lease = artifact["leases"][0]
    assert lease["work_envelope_id"] == "env-swarm-phase1"
    assert lease["lease_state"] == "proposed"
    assert lease["max_runtime_sec"] == 600
    assert lease["approval_context"]["issuance_mode"] == "phase1_static"


def test_build_worker_ownership_map_exposes_per_path_ownership() -> None:
    artifact = build_static_worker_leases_artifact(
        _valid_swarm_envelope(),
        issued_at_utc="2026-04-16T00:00:00Z",
    )
    ownership_map = build_worker_ownership_map(artifact)

    assert ownership_map["schema"] == "station.swarm.ownership_map.v1"
    assert ownership_map["worker_count"] == 1
    assert ownership_map["workers"][0]["worker_id"] == "worker-01"
    path_rows = {entry["path"]: entry for entry in ownership_map["path_ownership"]}
    assert path_rows["calyx/kernel/swarm_work_envelope.py"]["writers"] == ["worker-01"]
    assert path_rows["runtime/**"]["denied_for"] == ["worker-01"]
    assert ownership_map["overlapping_write_paths"] == []


def test_validate_static_worker_lease_set_rejects_declared_overlap_without_resolution() -> None:
    valid, errors, _lease_artifact, ownership_map = validate_static_worker_lease_set(
        _overlapping_swarm_envelope(overlap_declared=True),
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    assert valid is False
    assert any("not supported in phase2" in error for error in errors)
    assert ownership_map["overlapping_write_paths"][0]["worker_ids"] == ["worker-01", "worker-02"]


def test_validate_static_worker_lease_set_rejects_conflicting_ownership_scope() -> None:
    envelope = _valid_swarm_envelope()
    worker = envelope.scope["swarm"]["worker_plan"][0]
    worker["ownership_scope"]["deny_paths"] = [
        "runtime/**",
        "calyx/kernel/swarm_work_envelope.py",
    ]

    valid, errors, _lease_artifact, _ownership_map = validate_static_worker_lease_set(
        envelope,
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    assert valid is False
    assert any("both write_paths and deny_paths" in error for error in errors)


def test_issue_static_worker_leases_writes_artifact_and_receipt(tmp_path: Path) -> None:
    (
        artifact,
        ownership_map,
        lifecycle,
        trace_graph,
        receipt_bundle,
        artifact_path,
        ownership_map_path,
        lifecycle_path,
        trace_graph_path,
        receipt_bundle_path,
        receipt_path,
        transition_receipt_paths,
    ) = issue_static_worker_leases(
        _valid_swarm_envelope(),
        tmp_path / "runtime",
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    persisted_artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    persisted_ownership_map = json.loads(ownership_map_path.read_text(encoding="utf-8"))
    persisted_lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    persisted_trace_graph = json.loads(trace_graph_path.read_text(encoding="utf-8"))
    persisted_bundle = json.loads(receipt_bundle_path.read_text(encoding="utf-8"))
    persisted_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    transition_receipt = json.loads(transition_receipt_paths[0].read_text(encoding="utf-8"))

    assert artifact["worker_count"] == 1
    assert ownership_map["worker_count"] == 1
    assert lifecycle["lease_count"] == 1
    assert trace_graph["root_node_id"] == "planner::swarm-run-001"
    assert receipt_bundle["bundle_status"] == "complete"
    assert persisted_artifact["work_envelope_id"] == "env-swarm-phase1"
    assert persisted_ownership_map["work_envelope_id"] == "env-swarm-phase1"
    assert persisted_lifecycle["work_envelope_id"] == "env-swarm-phase1"
    assert persisted_trace_graph["work_envelope_id"] == "env-swarm-phase1"
    assert persisted_bundle["work_envelope_id"] == "env-swarm-phase1"
    assert persisted_receipt["receipt_type"] == "swarm.worker_lease.issuance_static"
    assert persisted_receipt["worker_execution_enabled"] is False
    assert persisted_receipt["ownership_conflict_count"] == 0
    assert persisted_receipt["transition_receipt_count"] == 1
    assert persisted_receipt["trace_graph_path"] == str(trace_graph_path)
    assert persisted_receipt["receipt_bundle_path"] == str(receipt_bundle_path)
    assert transition_receipt["receipt_type"] == "swarm_lease_transition"
    assert transition_receipt["previous_state"] is None
    assert transition_receipt["new_state"] == "proposed"
    assert artifact_path.name == "worker_leases.json"
    assert ownership_map_path.name == "ownership_map.json"
    assert lifecycle_path.name == "lease_lifecycle.json"
    assert trace_graph_path.name == "trace_graph.json"
    assert receipt_bundle_path.name == "receipt_bundle.json"


def test_transition_worker_lease_state_records_valid_lifecycle_progression(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    (
        _artifact,
        _ownership_map,
        _lifecycle,
        _trace_graph,
        _receipt_bundle,
        _artifact_path,
        _ownership_map_path,
        _lifecycle_path,
        _trace_graph_path,
        _receipt_bundle_path,
        _receipt_path,
        _transition_receipt_paths,
    ) = issue_static_worker_leases(
        _valid_swarm_envelope(),
        runtime_dir,
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    lease_artifact, lifecycle, receipt_path = transition_worker_lease_state(
        runtime_dir,
        swarm_run_id="swarm-run-001",
        lease_id="swarm-run-001--worker-01",
        new_state="approved",
        transition_reason="operator approved static lease",
        trigger_source="operator",
        evidence_refs=["approval:lease-review-001"],
        timestamp_utc="2026-04-16T00:01:00Z",
    )
    lease_artifact, lifecycle, receipt_path = transition_worker_lease_state(
        runtime_dir,
        swarm_run_id="swarm-run-001",
        lease_id="swarm-run-001--worker-01",
        new_state="active",
        transition_reason="sandbox preparation acknowledged for future phase",
        trigger_source="validation",
        evidence_refs=["validation:phase3-ready"],
        timestamp_utc="2026-04-16T00:02:00Z",
    )
    lease_artifact, lifecycle, receipt_path = transition_worker_lease_state(
        runtime_dir,
        swarm_run_id="swarm-run-001",
        lease_id="swarm-run-001--worker-01",
        new_state="completed",
        transition_reason="lifecycle test closure",
        trigger_source="system",
        evidence_refs=["test:test_transition_worker_lease_state_records_valid_lifecycle_progression"],
        timestamp_utc="2026-04-16T00:03:00Z",
    )

    persisted_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    persisted_trace_graph = json.loads((runtime_dir / "cbo" / "swarm" / "swarm-run-001" / "trace_graph.json").read_text(encoding="utf-8"))
    persisted_bundle = json.loads((runtime_dir / "cbo" / "swarm" / "swarm-run-001" / "receipt_bundle.json").read_text(encoding="utf-8"))

    assert lease_artifact["leases"][0]["lease_state"] == "completed"
    assert lifecycle["leases"][0]["current_state"] == "completed"
    assert lifecycle["leases"][0]["terminal_state"] == "completed"
    assert len(lifecycle["leases"][0]["transition_history"]) == 4
    assert len([node for node in persisted_trace_graph["nodes"] if node["action_type"] == "lease_transition"]) == 4
    assert persisted_bundle["lifecycle_artifact_refs"][-1] == str(receipt_path)
    assert persisted_receipt["previous_state"] == "active"
    assert persisted_receipt["new_state"] == "completed"


def test_transition_worker_lease_state_rejects_invalid_transition(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    issue_static_worker_leases(
        _valid_swarm_envelope(),
        runtime_dir,
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    try:
        transition_worker_lease_state(
            runtime_dir,
            swarm_run_id="swarm-run-001",
            lease_id="swarm-run-001--worker-01",
            new_state="active",
            transition_reason="attempt to skip approval",
            trigger_source="operator",
            evidence_refs=["approval:missing-step"],
            timestamp_utc="2026-04-16T00:01:00Z",
        )
    except ValueError as exc:
        assert "invalid_lease_transition:proposed->active" in str(exc)
    else:
        raise AssertionError("expected invalid transition to be rejected")


def test_transition_worker_lease_state_rejects_missing_justification(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    issue_static_worker_leases(
        _valid_swarm_envelope(),
        runtime_dir,
        issued_at_utc="2026-04-16T00:00:00Z",
    )

    try:
        transition_worker_lease_state(
            runtime_dir,
            swarm_run_id="swarm-run-001",
            lease_id="swarm-run-001--worker-01",
            new_state="approved",
            transition_reason="",
            trigger_source="operator",
            evidence_refs=[],
            timestamp_utc="2026-04-16T00:01:00Z",
        )
    except ValueError as exc:
        assert "transition_reason must be a non-empty string" in str(exc)
    else:
        raise AssertionError("expected missing justification to be rejected")
