from __future__ import annotations

import json
from pathlib import Path

from calyx.kernel.swarm_sandbox import prepare_read_only_probe_sandboxes
from calyx.kernel.swarm_trace import (
    ROOT_ACTION_TYPE,
    SANDBOX_PREPARE_ACTION_TYPE,
    SNAPSHOT_PRE_EXECUTION_ACTION_TYPE,
    WORKER_ACTION_TYPE,
    append_sandbox_preparation_to_trace_graph,
    build_initial_trace_graph,
    build_lease_transition_trace_node,
    build_planner_root_node,
    build_swarm_receipt_bundle,
    build_worker_trace_node,
    get_receipt_bundle_path,
    get_trace_graph_path,
    validate_swarm_receipt_bundle,
    validate_trace_graph,
    write_swarm_receipt_bundle,
    write_trace_graph,
)


def _lease_artifact(worker_count: int = 1) -> dict:
    leases = []
    for index in range(worker_count):
        worker_num = index + 1
        leases.append(
            {
                "schema": "station.swarm.worker_lease.v1",
                "schema_version": "1.0.0",
                "swarm_run_id": "swarm-run-trace",
                "lease_id": f"swarm-run-trace--worker-{worker_num:02d}",
                "worker_id": f"worker-{worker_num:02d}",
                "work_envelope_id": "env-trace",
                "lease_state": "proposed",
                "issued_at_utc": "2026-04-16T00:00:00Z",
                "expires_at_utc": "2026-04-16T00:10:00Z",
                "max_runtime_sec": 600,
                "token_budget": {"max_tokens": 4000},
                "compute_budget": {"max_tool_calls": 20},
                "ownership_scope": {
                    "read_paths": ["calyx/kernel/**"],
                    "write_paths": [f"calyx/kernel/swarm_trace_{worker_num:02d}.py"],
                    "deny_paths": ["runtime/**"],
                },
                "allowed_tool_classes": ["read_files", "write_files"],
                "network_scope": {"mode": "deny", "allowlist": []},
                "success_criteria": ["Trace node structure emitted"],
                "approval_context": {"requires_human_approval": False},
                "revocation_reason": None,
                "notes": "Trace-only lease fixture",
            }
        )
    return {
        "schema": "station.swarm.worker_leases.v1",
        "schema_version": "1.0.0",
        "swarm_run_id": "swarm-run-trace",
        "work_envelope_id": "env-trace",
        "lease_state": "proposed",
        "issued_at_utc": "2026-04-16T00:00:00Z",
        "worker_count": worker_count,
        "leases": leases,
    }


def _lifecycle(worker_count: int = 1) -> dict:
    rows = []
    for index in range(worker_count):
        worker_num = index + 1
        event = {
            "swarm_run_id": "swarm-run-trace",
            "work_envelope_id": "env-trace",
            "lease_id": f"swarm-run-trace--worker-{worker_num:02d}",
            "worker_id": f"worker-{worker_num:02d}",
            "previous_state": None,
            "new_state": "proposed",
            "transition_reason": "static lease issuance",
            "trigger_source": "system",
            "timestamp_utc": "2026-04-16T00:00:00Z",
            "evidence_refs": ["work_envelope:env-trace"],
        }
        rows.append(
            {
                "lease_id": f"swarm-run-trace--worker-{worker_num:02d}",
                "worker_id": f"worker-{worker_num:02d}",
                "current_state": "proposed",
                "terminal_state": None,
                "transition_history": [event],
            }
        )
    return {
        "schema": "station.swarm.lease_lifecycle.v1",
        "schema_version": "1.0.0",
        "swarm_run_id": "swarm-run-trace",
        "work_envelope_id": "env-trace",
        "updated_at_utc": "2026-04-16T00:00:00Z",
        "lease_count": worker_count,
        "leases": rows,
    }


def test_valid_root_planner_node_creation() -> None:
    node = build_planner_root_node(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        timestamp_utc="2026-04-16T00:00:00Z",
        work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
    )

    assert node["node_id"] == "planner::swarm-run-trace"
    assert node["parent_id"] is None
    assert node["action_type"] == ROOT_ACTION_TYPE


def test_valid_single_worker_child_node_creation() -> None:
    node = build_worker_trace_node(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        lease=_lease_artifact()["leases"][0],
        parent_id="planner::swarm-run-trace",
    )

    assert node["parent_id"] == "planner::swarm-run-trace"
    assert node["action_type"] == WORKER_ACTION_TYPE
    assert node["lease_id"] == "swarm-run-trace--worker-01"


def test_lease_transition_nodes_appear_in_trace_graph(tmp_path: Path) -> None:
    transition_receipt = tmp_path / "transition.json"
    transition_receipt.write_text("{}", encoding="utf-8")
    trace_graph = build_initial_trace_graph(
        lease_artifact=_lease_artifact(),
        lifecycle=_lifecycle(),
        transition_receipt_paths=[transition_receipt],
        work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
    )

    transition_nodes = [node for node in trace_graph["nodes"] if node["action_type"] == "lease_transition"]
    assert len(trace_graph["nodes"]) == 3
    assert len(transition_nodes) == 1
    assert transition_nodes[0]["parent_id"] == "worker::swarm-run-trace--worker-01"


def test_multi_worker_structural_graph_creation(tmp_path: Path) -> None:
    receipt_one = tmp_path / "swarm_lease_transition__1.json"
    receipt_two = tmp_path / "swarm_lease_transition__2.json"
    receipt_one.write_text(
        '{"lease_id":"swarm-run-trace--worker-01","new_state":"proposed","timestamp_utc":"2026-04-16T00:00:00Z"}',
        encoding="utf-8",
    )
    receipt_two.write_text(
        '{"lease_id":"swarm-run-trace--worker-02","new_state":"proposed","timestamp_utc":"2026-04-16T00:00:00Z"}',
        encoding="utf-8",
    )
    trace_graph = build_initial_trace_graph(
        lease_artifact=_lease_artifact(worker_count=2),
        lifecycle=_lifecycle(worker_count=2),
        transition_receipt_paths=[receipt_one, receipt_two],
        work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
    )

    worker_nodes = [node for node in trace_graph["nodes"] if node["action_type"] == "worker"]
    transition_nodes = [node for node in trace_graph["nodes"] if node["action_type"] == "lease_transition"]
    assert len(worker_nodes) == 2
    assert len(transition_nodes) == 2
    assert all(node["parent_id"].startswith("worker::swarm-run-trace--worker-") for node in transition_nodes)
    assert trace_graph["anomalies"] == []


def test_sandbox_and_snapshot_nodes_are_emitted_with_receipt_bundle_refs(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    repo_root = tmp_path / "repo"
    work_envelope = tmp_path / "env-trace.json"
    work_envelope.write_text("{}", encoding="utf-8")
    target_file = repo_root / "calyx" / "kernel" / "swarm_trace_01.py"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# staged\n", encoding="utf-8")

    lease_artifact = _lease_artifact()
    lifecycle = _lifecycle()
    receipt_one = tmp_path / "swarm_lease_transition__1.json"
    receipt_one.write_text(
        '{"lease_id":"swarm-run-trace--worker-01","new_state":"proposed","timestamp_utc":"2026-04-16T00:00:00Z"}',
        encoding="utf-8",
    )
    trace_graph = build_initial_trace_graph(
        lease_artifact=lease_artifact,
        lifecycle=lifecycle,
        transition_receipt_paths=[receipt_one],
        work_envelope_ref=str(work_envelope),
    )
    trace_graph_path = write_trace_graph(runtime_dir, trace_graph)
    worker_leases = runtime_dir / "cbo" / "swarm" / "swarm-run-trace" / "worker_leases.json"
    ownership_map = runtime_dir / "cbo" / "swarm" / "swarm-run-trace" / "ownership_map.json"
    lifecycle_path = runtime_dir / "cbo" / "swarm" / "swarm-run-trace" / "lease_lifecycle.json"
    worker_leases.parent.mkdir(parents=True, exist_ok=True)
    worker_leases.write_text(json.dumps(lease_artifact), encoding="utf-8")
    ownership_map.write_text(json.dumps({"schema": "station.swarm.worker_ownership_map.v1", "worker_count": 1, "conflicts": []}), encoding="utf-8")
    lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
    bundle = build_swarm_receipt_bundle(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        work_envelope_ref=str(work_envelope),
        lease_artifact=lease_artifact,
        lifecycle=lifecycle,
        trace_graph=trace_graph,
        worker_leases_path=worker_leases,
        ownership_map_path=ownership_map,
        lifecycle_path=lifecycle_path,
        trace_graph_path=trace_graph_path,
        transition_receipt_paths=[receipt_one],
        anomalies=[],
    )
    write_swarm_receipt_bundle(runtime_dir, bundle)

    manifests, manifest_paths, snapshots, snapshot_paths = prepare_read_only_probe_sandboxes(
        lease_artifact,
        runtime_dir=runtime_dir,
        repo_root=repo_root,
    )
    updated_graph, updated_bundle = append_sandbox_preparation_to_trace_graph(
        runtime_dir,
        swarm_run_id="swarm-run-trace",
        sandbox_manifests=manifests,
        sandbox_manifest_paths=manifest_paths,
        snapshot_records=snapshots,
        snapshot_paths=snapshot_paths,
    )

    sandbox_nodes = [
        node for node in updated_graph["nodes"] if node["action_type"] == SANDBOX_PREPARE_ACTION_TYPE
    ]
    snapshot_nodes = [
        node for node in updated_graph["nodes"] if node["action_type"] == SNAPSHOT_PRE_EXECUTION_ACTION_TYPE
    ]
    assert len(sandbox_nodes) == 1
    assert len(snapshot_nodes) == 1
    assert sandbox_nodes[0]["parent_id"] == "worker::swarm-run-trace--worker-01"
    assert snapshot_nodes[0]["parent_id"] == sandbox_nodes[0]["node_id"]
    assert updated_bundle["sandbox_manifest_refs"] == [str(manifest_paths[0])]
    assert updated_bundle["snapshot_refs"] == [str(snapshot_paths[0])]


def test_missing_root_node_rejection() -> None:
    trace_graph = {
        "schema": "station.swarm.trace_graph.v1",
        "schema_version": "1.0.0",
        "swarm_run_id": "swarm-run-trace",
        "work_envelope_id": "env-trace",
        "root_node_id": "planner::swarm-run-trace",
        "updated_at_utc": "2026-04-16T00:00:00Z",
        "nodes": [
            build_worker_trace_node(
                swarm_run_id="swarm-run-trace",
                work_envelope_id="env-trace",
                lease=_lease_artifact()["leases"][0],
                parent_id="planner::swarm-run-trace",
            )
        ],
        "anomalies": [],
    }

    valid, errors = validate_trace_graph(trace_graph)
    assert valid is False
    assert any("exactly one root node" in error for error in errors)


def test_missing_lease_reference_rejection_for_worker_node() -> None:
    node = build_worker_trace_node(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        lease=_lease_artifact()["leases"][0],
        parent_id="planner::swarm-run-trace",
    )
    node["lease_id"] = None
    trace_graph = {
        "schema": "station.swarm.trace_graph.v1",
        "schema_version": "1.0.0",
        "swarm_run_id": "swarm-run-trace",
        "work_envelope_id": "env-trace",
        "root_node_id": "planner::swarm-run-trace",
        "updated_at_utc": "2026-04-16T00:00:00Z",
        "nodes": [
            build_planner_root_node(
                swarm_run_id="swarm-run-trace",
                work_envelope_id="env-trace",
                timestamp_utc="2026-04-16T00:00:00Z",
                work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
            ),
            node,
        ],
        "anomalies": [],
    }

    valid, errors = validate_trace_graph(trace_graph)
    assert valid is False
    assert any("lease_id is required for worker nodes" in error for error in errors)


def test_receipt_bundle_structure_validity(tmp_path: Path) -> None:
    worker_leases = tmp_path / "worker_leases.json"
    ownership_map = tmp_path / "ownership_map.json"
    lifecycle = tmp_path / "lease_lifecycle.json"
    trace_graph = tmp_path / "trace_graph.json"
    transition_receipt = tmp_path / "swarm_lease_transition__1.json"
    for path in (worker_leases, ownership_map, lifecycle, trace_graph, transition_receipt):
        path.write_text("{}", encoding="utf-8")

    bundle = build_swarm_receipt_bundle(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
        lease_artifact=_lease_artifact(),
        lifecycle=_lifecycle(),
        trace_graph={
            "schema": "station.swarm.trace_graph.v1",
            "schema_version": "1.0.0",
            "swarm_run_id": "swarm-run-trace",
            "work_envelope_id": "env-trace",
            "root_node_id": "planner::swarm-run-trace",
            "updated_at_utc": "2026-04-16T00:00:00Z",
            "nodes": [],
            "anomalies": [],
        },
        worker_leases_path=worker_leases,
        ownership_map_path=ownership_map,
        lifecycle_path=lifecycle,
        trace_graph_path=trace_graph,
        transition_receipt_paths=[transition_receipt],
        anomalies=[],
    )

    valid, errors = validate_swarm_receipt_bundle(bundle)
    assert valid is True
    assert errors == []
    assert bundle["bundle_status"] == "partial"
    assert bundle["replay_manifest"]["replay_guarantee"] == "partial"
    assert bundle["replay_manifest"]["worker_set"][0]["worker_id"] == "worker-01"


def test_parent_child_linkage_correctness() -> None:
    event = _lifecycle()["leases"][0]["transition_history"][0]
    node = build_lease_transition_trace_node(
        event=event,
        parent_id="worker::swarm-run-trace--worker-01",
        artifact_refs=["runtime/receipts/audit/swarm_lease_transition__x.json"],
    )
    assert node["parent_id"] == "worker::swarm-run-trace--worker-01"
    assert node["worker_id"] == "worker-01"


def test_anomaly_capture_and_degraded_bundle_state_when_refs_missing(tmp_path: Path) -> None:
    worker_leases = tmp_path / "worker_leases.json"
    ownership_map = tmp_path / "ownership_map.json"
    lifecycle = tmp_path / "lease_lifecycle.json"
    trace_graph = tmp_path / "trace_graph.json"
    worker_leases.write_text("{}", encoding="utf-8")
    ownership_map.write_text("{}", encoding="utf-8")
    lifecycle.write_text("{}", encoding="utf-8")
    bundle = build_swarm_receipt_bundle(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        work_envelope_ref="runtime/cbo/work_outbox/env-trace.json",
        lease_artifact=_lease_artifact(),
        lifecycle=_lifecycle(),
        trace_graph={
            "schema": "station.swarm.trace_graph.v1",
            "schema_version": "1.0.0",
            "swarm_run_id": "swarm-run-trace",
            "work_envelope_id": "env-trace",
            "root_node_id": "planner::swarm-run-trace",
            "updated_at_utc": "2026-04-16T00:00:00Z",
            "nodes": [],
            "anomalies": [],
        },
        worker_leases_path=worker_leases,
        ownership_map_path=ownership_map,
        lifecycle_path=lifecycle,
        trace_graph_path=trace_graph,
        transition_receipt_paths=[],
        anomalies=[],
    )

    assert bundle["bundle_status"] == "degraded"
    assert any(item["anomaly_code"] == "missing_expected_artifact_ref" for item in bundle["anomalies"])
    assert bundle["replay_manifest"]["missing_refs"] == [str(trace_graph)]


def test_invalid_bundle_state_when_required_structure_absent() -> None:
    valid, errors = validate_swarm_receipt_bundle(
        {
            "receipt_bundle_id": "bundle::bad",
            "swarm_run_id": "swarm-run-trace",
            "work_envelope_id": "env-trace",
            "work_envelope_ref": "runtime/cbo/work_outbox/env-trace.json",
            "worker_lease_refs": ["runtime/cbo/swarm/swarm-run-trace/worker_leases.json"],
            "lifecycle_artifact_refs": ["runtime/cbo/swarm/swarm-run-trace/lease_lifecycle.json"],
            "trace_graph_ref": "runtime/cbo/swarm/swarm-run-trace/trace_graph.json",
            "anomalies": [],
            "bundle_status": "invalid",
        }
    )
    assert valid is False
    assert any("replay_manifest" in error for error in errors)


def test_replay_manifest_completeness_for_multi_worker_graph(tmp_path: Path) -> None:
    worker_leases = tmp_path / "worker_leases.json"
    ownership_map = tmp_path / "ownership_map.json"
    lifecycle = tmp_path / "lease_lifecycle.json"
    trace_graph_path = tmp_path / "trace_graph.json"
    receipt_one = tmp_path / "swarm_lease_transition__1.json"
    receipt_two = tmp_path / "swarm_lease_transition__2.json"
    work_envelope = tmp_path / "env-trace.json"
    for path in (worker_leases, ownership_map, lifecycle, trace_graph_path, receipt_one, receipt_two, work_envelope):
        path.write_text("{}", encoding="utf-8")
    receipt_one.write_text(
        '{"lease_id":"swarm-run-trace--worker-01","new_state":"proposed","timestamp_utc":"2026-04-16T00:00:00Z"}',
        encoding="utf-8",
    )
    receipt_two.write_text(
        '{"lease_id":"swarm-run-trace--worker-02","new_state":"proposed","timestamp_utc":"2026-04-16T00:00:00Z"}',
        encoding="utf-8",
    )
    trace_graph = build_initial_trace_graph(
        lease_artifact=_lease_artifact(worker_count=2),
        lifecycle=_lifecycle(worker_count=2),
        transition_receipt_paths=[receipt_one, receipt_two],
        work_envelope_ref=str(work_envelope),
    )
    bundle = build_swarm_receipt_bundle(
        swarm_run_id="swarm-run-trace",
        work_envelope_id="env-trace",
        work_envelope_ref=str(work_envelope),
        lease_artifact=_lease_artifact(worker_count=2),
        lifecycle=_lifecycle(worker_count=2),
        trace_graph=trace_graph,
        worker_leases_path=worker_leases,
        ownership_map_path=ownership_map,
        lifecycle_path=lifecycle,
        trace_graph_path=trace_graph_path,
        transition_receipt_paths=[receipt_one, receipt_two],
        anomalies=[],
    )

    assert bundle["bundle_status"] == "complete"
    assert bundle["replay_manifest"]["replay_guarantee"] == "complete"
    assert len(bundle["replay_manifest"]["worker_set"]) == 2
    assert len(bundle["replay_manifest"]["transition_sequence"]) == 2
