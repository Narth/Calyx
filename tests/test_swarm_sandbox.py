from __future__ import annotations

from pathlib import Path

from calyx.kernel.swarm_sandbox import (
    SWARM_CONTAINMENT_FAILURE_SCHEMA,
    SWARM_CONTAINMENT_FAILURE_SCHEMA_VERSION,
    SWARM_POST_EXECUTION_DIFF_SCHEMA,
    SWARM_POST_EXECUTION_DIFF_SCHEMA_VERSION,
    SWARM_SANDBOX_MANIFEST_SCHEMA,
    SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION,
    SWARM_SNAPSHOT_RECORD_SCHEMA,
    SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION,
    build_read_only_probe_sandbox_manifest,
    get_snapshot_inventory_path,
    materialize_prepared_sandbox,
    prepare_read_only_probe_sandbox,
    validate_containment_failure_record,
    validate_post_execution_diff,
    validate_sandbox_manifest,
    validate_sandbox_state_transition,
    validate_snapshot_record,
)


def _valid_worker_lease() -> dict:
    return {
        "schema": "station.swarm.worker_lease.v1",
        "schema_version": "1.0.0",
        "swarm_run_id": "swarm-run-001",
        "work_envelope_id": "env-001",
        "lease_id": "swarm-run-001--worker-01",
        "worker_id": "worker-01",
        "lease_state": "approved",
        "issued_at_utc": "2026-04-16T00:00:00Z",
        "expires_at_utc": "2026-04-16T00:10:00Z",
        "max_runtime_sec": 600,
        "token_budget": {"max_tokens": 4000},
        "compute_budget": {"max_tool_calls": 20},
        "ownership_scope": {
            "read_paths": ["docs/planning/**", "calyx/kernel/**"],
            "write_paths": ["calyx/kernel/swarm_sandbox.py"],
            "deny_paths": ["runtime/**"],
        },
        "allowed_tool_classes": ["read_files", "write_files"],
        "network_scope": {"mode": "deny", "allowlist": []},
        "success_criteria": ["Sandbox schema validates"],
        "approval_context": {"requires_human_approval": False},
        "revocation_reason": None,
        "notes": "Schema-only lease",
    }


def _valid_sandbox_manifest() -> dict:
    return {
        "schema": SWARM_SANDBOX_MANIFEST_SCHEMA,
        "schema_version": SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION,
        "sandbox_id": "sandbox--swarm-run-001--worker-01",
        "swarm_run_id": "swarm-run-001",
        "work_envelope_id": "env-001",
        "lease_id": "swarm-run-001--worker-01",
        "worker_id": "worker-01",
        "isolation_mode": "directory_overlay",
        "sandbox_root": "runtime/cbo/swarm/swarm-run-001/sandbox-worker-01",
        "read_paths": ["docs/planning/**", "calyx/kernel/**"],
        "write_paths": ["calyx/kernel/swarm_sandbox.py"],
        "deny_paths": ["runtime/**"],
        "allowed_tool_classes": ["read_files", "write_files"],
        "network_scope": {"mode": "deny", "allowlist": []},
        "pre_execution_snapshot_id": "snapshot-pre-001",
        "post_execution_diff_id": "diff-001",
        "sandbox_state": "prepared",
        "notes": "Schema-only containment surface",
    }


def _valid_snapshot_record() -> dict:
    return {
        "schema": SWARM_SNAPSHOT_RECORD_SCHEMA,
        "schema_version": SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION,
        "snapshot_id": "snapshot-pre-001",
        "swarm_run_id": "swarm-run-001",
        "lease_id": "swarm-run-001--worker-01",
        "worker_id": "worker-01",
        "snapshot_stage": "pre_execution",
        "snapshot_method": "scope_hash_only",
        "captured_at_utc": "2026-04-16T00:00:00Z",
        "scope_hash": "sha256:abc123",
        "artifact_paths": ["runtime/cbo/swarm/swarm-run-001/snapshots/snapshot-pre-001.json"],
        "rollback_method": "git_checkout_from_snapshot",
        "notes": "No live snapshot taken in phase0",
    }


def _valid_post_execution_diff() -> dict:
    return {
        "schema": SWARM_POST_EXECUTION_DIFF_SCHEMA,
        "schema_version": SWARM_POST_EXECUTION_DIFF_SCHEMA_VERSION,
        "diff_id": "diff-001",
        "swarm_run_id": "swarm-run-001",
        "lease_id": "swarm-run-001--worker-01",
        "worker_id": "worker-01",
        "changed_paths": ["calyx/kernel/swarm_sandbox.py"],
        "added_paths": [],
        "deleted_paths": [],
        "ownership_violations": [],
        "generated_artifacts": ["runtime/cbo/swarm/swarm-run-001/diffs/diff-001.json"],
        "diff_summary": {"changed_path_count": 1, "ownership_violation_count": 0},
    }


def _valid_containment_failure() -> dict:
    return {
        "schema": SWARM_CONTAINMENT_FAILURE_SCHEMA,
        "schema_version": SWARM_CONTAINMENT_FAILURE_SCHEMA_VERSION,
        "failure_class": "snapshot_missing",
        "swarm_run_id": "swarm-run-001",
        "lease_id": "swarm-run-001--worker-01",
        "worker_id": "worker-01",
        "sandbox_id": "sandbox--swarm-run-001--worker-01",
        "detected_at_utc": "2026-04-16T00:05:00Z",
        "detail": "pre-execution snapshot was not materialized",
        "artifact_refs": ["runtime/cbo/swarm/swarm-run-001/sandbox-worker-01/manifest.json"],
    }


def test_valid_sandbox_manifest_structure_is_accepted() -> None:
    valid, errors = validate_sandbox_manifest(
        _valid_sandbox_manifest(),
        worker_lease=_valid_worker_lease(),
    )

    assert valid is True
    assert errors == []


def test_invalid_sandbox_manifest_schema_is_rejected() -> None:
    manifest = _valid_sandbox_manifest()
    manifest["schema"] = "station.swarm.sandbox_manifest.v0"
    valid, errors = validate_sandbox_manifest(manifest, worker_lease=_valid_worker_lease())

    assert valid is False
    assert any("sandbox_manifest.schema must equal" in error for error in errors)


def test_invalid_sandbox_state_transition_is_rejected() -> None:
    valid, errors = validate_sandbox_state_transition("prepared", "sealed")

    assert valid is False
    assert errors == ["invalid_sandbox_transition:prepared->sealed"]


def test_lease_sandbox_identity_mismatch_is_rejected() -> None:
    manifest = _valid_sandbox_manifest()
    manifest["worker_id"] = "worker-02"
    valid, errors = validate_sandbox_manifest(manifest, worker_lease=_valid_worker_lease())

    assert valid is False
    assert any("sandbox_manifest.worker_id must match worker_lease.worker_id" in error for error in errors)


def test_snapshot_and_diff_schema_validity() -> None:
    snapshot_valid, snapshot_errors = validate_snapshot_record(
        _valid_snapshot_record(),
        sandbox_manifest=_valid_sandbox_manifest(),
    )
    diff_valid, diff_errors = validate_post_execution_diff(
        _valid_post_execution_diff(),
        sandbox_manifest=_valid_sandbox_manifest(),
    )

    assert snapshot_valid is True
    assert snapshot_errors == []
    assert diff_valid is True
    assert diff_errors == []


def test_post_execution_diff_rejects_changed_path_outside_manifest_scope() -> None:
    diff = _valid_post_execution_diff()
    diff["changed_paths"] = ["calyx/kernel/contract.py"]
    valid, errors = validate_post_execution_diff(diff, sandbox_manifest=_valid_sandbox_manifest())

    assert valid is False
    assert any("outside sandbox_manifest.write_paths" in error for error in errors)


def test_containment_failure_record_validity() -> None:
    valid, errors = validate_containment_failure_record(
        _valid_containment_failure(),
        sandbox_manifest=_valid_sandbox_manifest(),
    )

    assert valid is True
    assert errors == []


def test_valid_sandbox_prepare_path_materializes_manifest_and_snapshot(tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    target_file = repo_root / "calyx" / "kernel" / "swarm_sandbox.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# probe\n", encoding="utf-8")

    worker_lease = _valid_worker_lease()
    worker_lease["ownership_scope"]["read_paths"] = ["calyx/kernel/**"]
    worker_lease["ownership_scope"]["write_paths"] = ["calyx/kernel/swarm_sandbox.py"]

    manifest, manifest_path, snapshot_record, snapshot_path = prepare_read_only_probe_sandbox(
        worker_lease,
        runtime_dir=runtime_dir,
        repo_root=repo_root,
    )

    assert manifest["sandbox_state"] == "prepared"
    assert manifest_path.exists()
    assert snapshot_path.exists()
    assert snapshot_record["scope_hash"].startswith("sha256:")
    inventory_path = get_snapshot_inventory_path(
        runtime_dir,
        manifest["swarm_run_id"],
        snapshot_record["snapshot_id"],
    )
    assert inventory_path.exists()


def test_sandbox_prepare_rejects_missing_lease() -> None:
    try:
        prepare_read_only_probe_sandbox(
            None,
            runtime_dir=Path("runtime"),
            repo_root=Path("."),
        )
    except ValueError as exc:
        assert "requires a valid worker_lease" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing worker_lease")


def test_invalid_identity_binding_is_rejected_during_materialization(tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    worker_lease = _valid_worker_lease()
    manifest = build_read_only_probe_sandbox_manifest(worker_lease, runtime_dir=runtime_dir)
    manifest["worker_id"] = "worker-02"

    try:
        materialize_prepared_sandbox(
            runtime_dir=runtime_dir,
            repo_root=repo_root,
            sandbox_manifest=manifest,
            worker_lease=worker_lease,
        )
    except ValueError as exc:
        assert "invalid_sandbox_identity_binding" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid sandbox identity binding")
