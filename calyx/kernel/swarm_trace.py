"""Structural swarm trace graph and receipt bundle support for non-executing runs."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SWARM_TRACE_NODE_SCHEMA = "station.swarm.trace_node.v1"
SWARM_TRACE_NODE_SCHEMA_VERSION = "1.0.0"
SWARM_TRACE_GRAPH_SCHEMA = "station.swarm.trace_graph.v1"
SWARM_TRACE_GRAPH_SCHEMA_VERSION = "1.0.0"
SWARM_RECEIPT_BUNDLE_SCHEMA = "station.swarm.receipt_bundle.v1"
SWARM_RECEIPT_BUNDLE_SCHEMA_VERSION = "1.0.0"

ALLOWED_TRACE_RESULT_STATUS = frozenset(
    {"pending", "running", "passed", "failed", "blocked", "revoked", "expired", "quarantined"}
)
ROOT_ACTION_TYPE = "plan"
WORKER_ACTION_TYPE = "worker"
LEASE_TRANSITION_ACTION_TYPE = "lease_transition"
SANDBOX_PREPARE_ACTION_TYPE = "sandbox_prepare"
SNAPSHOT_PRE_EXECUTION_ACTION_TYPE = "snapshot_pre_execution"
ALLOWED_BUNDLE_STATUS = frozenset({"complete", "partial", "degraded", "invalid"})
ALLOWED_REPLAY_GUARANTEE = frozenset({"complete", "partial", "degraded", "invalid"})


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _as_unique_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if _is_non_empty_string(item):
            text = item.strip()
            if text not in out:
                out.append(text)
    return out


def _safe_segment(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not _is_non_empty_string(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return path


def _read_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _looks_like_file_ref(value: str | None) -> bool:
    if not _is_non_empty_string(value):
        return False
    text = value.strip()
    return ("\\" in text) or ("/" in text) or text.endswith(".json")


def _path_exists(ref: str | None) -> bool:
    if not _is_non_empty_string(ref):
        return False
    try:
        return Path(ref).exists()
    except OSError:
        return False


def build_anomaly_record(
    *,
    anomaly_code: str,
    detail: str,
    severity: str = "elevated",
    artifact_scope: str = "trace_graph",
    refs: list[str] | None = None,
    lease_id: str | None = None,
    worker_id: str | None = None,
) -> dict[str, Any]:
    return {
        "anomaly_code": anomaly_code,
        "severity": severity,
        "artifact_scope": artifact_scope,
        "detail": detail,
        "lease_id": lease_id,
        "worker_id": worker_id,
        "refs": _as_unique_string_list(refs or []),
    }


def _merge_anomalies(*anomaly_lists: Any) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None, str | None, tuple[str, ...]]] = set()
    for anomaly_list in anomaly_lists:
        if not isinstance(anomaly_list, list):
            continue
        for item in anomaly_list:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("anomaly_code")),
                str(item.get("detail")),
                item.get("lease_id"),
                item.get("worker_id"),
                tuple(_as_unique_string_list(item.get("refs"))),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _count_severity(anomalies: list[dict[str, Any]], *levels: str) -> int:
    return sum(1 for item in anomalies if item.get("severity") in levels)


def _build_replay_manifest(
    *,
    work_envelope_ref: str | None,
    lease_artifact: dict[str, Any] | None,
    lifecycle: dict[str, Any] | None,
    trace_graph: dict[str, Any] | None,
    required_refs: list[str],
    missing_refs: list[str],
    artifact_generation_order: list[str],
    sandbox_manifest_refs: list[str] | None = None,
    snapshot_refs: list[str] | None = None,
) -> dict[str, Any]:
    leases = lease_artifact.get("leases", []) if isinstance(lease_artifact, dict) else []
    lifecycle_rows = {
        row.get("lease_id"): row
        for row in (lifecycle.get("leases", []) if isinstance(lifecycle, dict) else [])
        if isinstance(row, dict) and _is_non_empty_string(row.get("lease_id"))
    }
    nodes = trace_graph.get("nodes", []) if isinstance(trace_graph, dict) else []
    worker_nodes = {
        node.get("lease_id"): node
        for node in nodes
        if isinstance(node, dict) and node.get("action_type") == WORKER_ACTION_TYPE
    }
    transition_nodes = sorted(
        [
            node
            for node in nodes
            if isinstance(node, dict) and node.get("action_type") == LEASE_TRANSITION_ACTION_TYPE
        ],
        key=lambda node: str(node.get("timestamp_utc", "")),
    )
    sandbox_refs = _as_unique_string_list(sandbox_manifest_refs or [])
    snapshot_record_refs = _as_unique_string_list(snapshot_refs or [])
    worker_set = []
    for lease in leases:
        if not isinstance(lease, dict):
            continue
        lease_id = lease.get("lease_id")
        lifecycle_row = lifecycle_rows.get(lease_id, {})
        worker_node = worker_nodes.get(lease_id, {})
        worker_set.append(
            {
                "worker_id": lease.get("worker_id"),
                "lease_id": lease_id,
                "lease_state": lease.get("lease_state"),
                "worker_node_id": worker_node.get("node_id"),
                "parent_node_id": worker_node.get("parent_id"),
                "transition_count": len(lifecycle_row.get("transition_history", []))
                if isinstance(lifecycle_row, dict)
                else 0,
            }
        )

    replay_guarantee = "complete"
    if missing_refs:
        replay_guarantee = "degraded"
    elif _looks_like_file_ref(work_envelope_ref) and not _path_exists(work_envelope_ref):
        replay_guarantee = "partial"

    return {
        "root_authority_ref": {
            "ref": work_envelope_ref,
            "materialized": _path_exists(work_envelope_ref) if _looks_like_file_ref(work_envelope_ref) else None,
        },
        "worker_set": worker_set,
        "transition_sequence": [
            {
                "node_id": node.get("node_id"),
                "lease_id": node.get("lease_id"),
                "worker_id": node.get("worker_id"),
                "timestamp_utc": node.get("timestamp_utc"),
                "artifact_refs": _as_unique_string_list(node.get("artifact_refs")),
            }
            for node in transition_nodes
        ],
        "artifact_generation_order": artifact_generation_order,
        "required_refs": required_refs,
        "missing_refs": missing_refs,
        "sandbox_manifest_refs": sandbox_refs,
        "snapshot_refs": snapshot_record_refs,
        "diff_refs": [],
        "execution_artifacts_present": False,
        "replay_guarantee": replay_guarantee,
    }


def get_swarm_run_dir(runtime_dir: Path, swarm_run_id: str) -> Path:
    return runtime_dir / "cbo" / "swarm" / _safe_segment(swarm_run_id)


def get_trace_graph_path(runtime_dir: Path, swarm_run_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "trace_graph.json"


def get_receipt_bundle_path(runtime_dir: Path, swarm_run_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "receipt_bundle.json"


def _discover_sandbox_manifest_refs(runtime_dir: Path, swarm_run_id: str) -> list[str]:
    sandboxes_dir = get_swarm_run_dir(runtime_dir, swarm_run_id) / "sandboxes"
    if not sandboxes_dir.exists():
        return []
    refs = sorted(str(path) for path in sandboxes_dir.glob("*/manifest.json") if path.is_file())
    return refs


def _discover_snapshot_refs(runtime_dir: Path, swarm_run_id: str) -> list[str]:
    snapshots_dir = get_swarm_run_dir(runtime_dir, swarm_run_id) / "snapshots"
    if not snapshots_dir.exists():
        return []
    refs = sorted(
        str(path)
        for path in snapshots_dir.glob("*.json")
        if path.is_file() and not path.name.endswith("__inventory.json")
    )
    return refs


def _result_status_for_lease_state(lease_state: str) -> str:
    mapping = {
        "proposed": "pending",
        "approved": "pending",
        "active": "running",
        "completed": "passed",
        "revoked": "revoked",
        "expired": "expired",
    }
    return mapping.get(lease_state, "blocked")


def build_planner_root_node(
    *,
    swarm_run_id: str,
    work_envelope_id: str,
    timestamp_utc: str | None = None,
    work_envelope_ref: str | None = None,
) -> dict[str, Any]:
    ts = timestamp_utc or _utc_now_iso()
    return {
        "schema": SWARM_TRACE_NODE_SCHEMA,
        "schema_version": SWARM_TRACE_NODE_SCHEMA_VERSION,
        "node_id": f"planner::{swarm_run_id}",
        "parent_id": None,
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "lease_id": None,
        "worker_id": None,
        "sandbox_id": None,
        "action_type": ROOT_ACTION_TYPE,
        "timestamp_utc": ts,
        "inputs": {"work_envelope_ref": work_envelope_ref},
        "outputs": {"planner_state": "swarm_static_structure_initialized"},
        "result_status": "passed",
        "artifact_refs": [work_envelope_ref] if _is_non_empty_string(work_envelope_ref) else [],
    }


def build_worker_trace_node(
    *,
    swarm_run_id: str,
    work_envelope_id: str,
    lease: dict[str, Any],
    parent_id: str,
) -> dict[str, Any]:
    return {
        "schema": SWARM_TRACE_NODE_SCHEMA,
        "schema_version": SWARM_TRACE_NODE_SCHEMA_VERSION,
        "node_id": f"worker::{lease['lease_id']}",
        "parent_id": parent_id,
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "lease_id": lease["lease_id"],
        "worker_id": lease["worker_id"],
        "sandbox_id": None,
        "action_type": WORKER_ACTION_TYPE,
        "timestamp_utc": lease["issued_at_utc"],
        "inputs": {
            "ownership_scope": lease.get("ownership_scope"),
            "allowed_tool_classes": lease.get("allowed_tool_classes"),
            "network_scope": lease.get("network_scope"),
        },
        "outputs": {"lease_state": lease.get("lease_state")},
        "result_status": _result_status_for_lease_state(lease.get("lease_state", "")),
        "artifact_refs": [],
    }


def build_lease_transition_trace_node(
    *,
    event: dict[str, Any],
    parent_id: str,
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SWARM_TRACE_NODE_SCHEMA,
        "schema_version": SWARM_TRACE_NODE_SCHEMA_VERSION,
        "node_id": f"lease_transition::{event['lease_id']}::{event['new_state']}::{event['timestamp_utc']}",
        "parent_id": parent_id,
        "swarm_run_id": event["swarm_run_id"],
        "work_envelope_id": event["work_envelope_id"],
        "lease_id": event["lease_id"],
        "worker_id": event["worker_id"],
        "sandbox_id": event.get("sandbox_id"),
        "action_type": LEASE_TRANSITION_ACTION_TYPE,
        "timestamp_utc": event["timestamp_utc"],
        "inputs": {
            "previous_state": event.get("previous_state"),
            "transition_reason": event.get("transition_reason"),
            "trigger_source": event.get("trigger_source"),
            "evidence_refs": event.get("evidence_refs", []),
        },
        "outputs": {"new_state": event["new_state"]},
        "result_status": _result_status_for_lease_state(event["new_state"]),
        "artifact_refs": artifact_refs or [],
    }


def build_sandbox_prepare_trace_node(
    *,
    sandbox_manifest: dict[str, Any],
    parent_id: str,
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SWARM_TRACE_NODE_SCHEMA,
        "schema_version": SWARM_TRACE_NODE_SCHEMA_VERSION,
        "node_id": f"sandbox_prepare::{sandbox_manifest['sandbox_id']}",
        "parent_id": parent_id,
        "swarm_run_id": sandbox_manifest["swarm_run_id"],
        "work_envelope_id": sandbox_manifest["work_envelope_id"],
        "lease_id": sandbox_manifest["lease_id"],
        "worker_id": sandbox_manifest["worker_id"],
        "sandbox_id": sandbox_manifest["sandbox_id"],
        "action_type": SANDBOX_PREPARE_ACTION_TYPE,
        "timestamp_utc": _utc_now_iso(),
        "inputs": {
            "isolation_mode": sandbox_manifest.get("isolation_mode"),
            "read_paths": sandbox_manifest.get("read_paths", []),
            "write_paths": sandbox_manifest.get("write_paths", []),
            "deny_paths": sandbox_manifest.get("deny_paths", []),
            "allowed_tool_classes": sandbox_manifest.get("allowed_tool_classes", []),
            "network_scope": sandbox_manifest.get("network_scope"),
        },
        "outputs": {"sandbox_state": sandbox_manifest.get("sandbox_state")},
        "result_status": "passed",
        "artifact_refs": artifact_refs or [],
    }


def build_snapshot_pre_execution_trace_node(
    *,
    snapshot_record: dict[str, Any],
    sandbox_id: str,
    work_envelope_id: str,
    parent_id: str,
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SWARM_TRACE_NODE_SCHEMA,
        "schema_version": SWARM_TRACE_NODE_SCHEMA_VERSION,
        "node_id": f"snapshot_pre_execution::{snapshot_record['snapshot_id']}",
        "parent_id": parent_id,
        "swarm_run_id": snapshot_record["swarm_run_id"],
        "work_envelope_id": work_envelope_id,
        "lease_id": snapshot_record["lease_id"],
        "worker_id": snapshot_record["worker_id"],
        "sandbox_id": sandbox_id,
        "action_type": SNAPSHOT_PRE_EXECUTION_ACTION_TYPE,
        "timestamp_utc": snapshot_record["captured_at_utc"],
        "inputs": {
            "snapshot_method": snapshot_record.get("snapshot_method"),
            "snapshot_stage": snapshot_record.get("snapshot_stage"),
        },
        "outputs": {
            "scope_hash": snapshot_record.get("scope_hash"),
            "rollback_method": snapshot_record.get("rollback_method"),
        },
        "result_status": "passed",
        "artifact_refs": artifact_refs or [],
    }


def validate_trace_graph(trace_graph: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(trace_graph, dict):
        return False, ["trace_graph must be a mapping"]
    if not isinstance(trace_graph.get("anomalies"), list):
        errors.append("trace_graph.anomalies must be a list")
    nodes = trace_graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return False, ["trace_graph.nodes must be a non-empty list"]

    node_ids: set[str] = set()
    node_by_id: dict[str, dict[str, Any]] = {}
    root_nodes: list[dict[str, Any]] = []

    for index, node in enumerate(nodes):
        label = f"trace_graph.nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{label} must be a mapping")
            continue
        node_id = node.get("node_id")
        if not _is_non_empty_string(node_id):
            errors.append(f"{label}.node_id must be a non-empty string")
            continue
        if node_id in node_ids:
            errors.append(f"{label}.node_id duplicates existing node_id '{node_id}'")
            continue
        node_ids.add(node_id)
        node_by_id[node_id] = node

        if node.get("result_status") not in ALLOWED_TRACE_RESULT_STATUS:
            errors.append(
                f"{label}.result_status must be one of: {', '.join(sorted(ALLOWED_TRACE_RESULT_STATUS))}"
            )
        if _parse_iso(node.get("timestamp_utc")) is None:
            errors.append(f"{label}.timestamp_utc must be a valid ISO-8601 timestamp")
        if not isinstance(node.get("inputs"), dict):
            errors.append(f"{label}.inputs must be a mapping")
        if not isinstance(node.get("outputs"), dict):
            errors.append(f"{label}.outputs must be a mapping")
        if not isinstance(node.get("artifact_refs"), list):
            errors.append(f"{label}.artifact_refs must be a list")

        parent_id = node.get("parent_id")
        if parent_id is None:
            root_nodes.append(node)
        elif not _is_non_empty_string(parent_id):
            errors.append(f"{label}.parent_id must be a non-empty string or null")

        action_type = node.get("action_type")
        if action_type == WORKER_ACTION_TYPE:
            if not _is_non_empty_string(node.get("lease_id")):
                errors.append(f"{label}.lease_id is required for worker nodes")
            if not _is_non_empty_string(node.get("worker_id")):
                errors.append(f"{label}.worker_id is required for worker nodes")
        if action_type == LEASE_TRANSITION_ACTION_TYPE:
            if not _is_non_empty_string(node.get("lease_id")):
                errors.append(f"{label}.lease_id is required for lease transition nodes")
            if not _is_non_empty_string(node.get("worker_id")):
                errors.append(f"{label}.worker_id is required for lease transition nodes")
        if action_type == SANDBOX_PREPARE_ACTION_TYPE:
            if not _is_non_empty_string(node.get("lease_id")):
                errors.append(f"{label}.lease_id is required for sandbox prepare nodes")
            if not _is_non_empty_string(node.get("worker_id")):
                errors.append(f"{label}.worker_id is required for sandbox prepare nodes")
            if not _is_non_empty_string(node.get("sandbox_id")):
                errors.append(f"{label}.sandbox_id is required for sandbox prepare nodes")
        if action_type == SNAPSHOT_PRE_EXECUTION_ACTION_TYPE:
            if not _is_non_empty_string(node.get("lease_id")):
                errors.append(f"{label}.lease_id is required for snapshot nodes")
            if not _is_non_empty_string(node.get("worker_id")):
                errors.append(f"{label}.worker_id is required for snapshot nodes")
            if not _is_non_empty_string(node.get("sandbox_id")):
                errors.append(f"{label}.sandbox_id is required for snapshot nodes")

    if len(root_nodes) != 1:
        errors.append("trace_graph must contain exactly one root node")
    elif root_nodes[0].get("action_type") != ROOT_ACTION_TYPE:
        errors.append("trace_graph root node must have action_type 'plan'")
    elif trace_graph.get("root_node_id") != root_nodes[0].get("node_id"):
        errors.append("trace_graph.root_node_id must match the root node node_id")

    for node in nodes:
        parent_id = node.get("parent_id")
        if parent_id is None:
            continue
        if parent_id not in node_by_id:
            errors.append(f"trace_graph node '{node.get('node_id')}' references missing parent_id '{parent_id}'")
            continue
        if node.get("action_type") == LEASE_TRANSITION_ACTION_TYPE:
            parent = node_by_id[parent_id]
            if parent.get("action_type") != WORKER_ACTION_TYPE:
                errors.append(
                    f"lease transition node '{node.get('node_id')}' must have a worker parent"
                )
        if node.get("action_type") == SANDBOX_PREPARE_ACTION_TYPE:
            parent = node_by_id[parent_id]
            if parent.get("action_type") != WORKER_ACTION_TYPE:
                errors.append(
                    f"sandbox prepare node '{node.get('node_id')}' must have a worker parent"
                )
        if node.get("action_type") == SNAPSHOT_PRE_EXECUTION_ACTION_TYPE:
            parent = node_by_id[parent_id]
            if parent.get("action_type") != SANDBOX_PREPARE_ACTION_TYPE:
                errors.append(
                    f"snapshot node '{node.get('node_id')}' must have a sandbox prepare parent"
                )
    return len(errors) == 0, errors


def build_initial_trace_graph(
    *,
    lease_artifact: dict[str, Any],
    lifecycle: dict[str, Any],
    transition_receipt_paths: list[Path],
    work_envelope_ref: str | None = None,
) -> dict[str, Any]:
    swarm_run_id = lease_artifact["swarm_run_id"]
    work_envelope_id = lease_artifact["work_envelope_id"]
    root_node = build_planner_root_node(
        swarm_run_id=swarm_run_id,
        work_envelope_id=work_envelope_id,
        timestamp_utc=lease_artifact.get("issued_at_utc"),
        work_envelope_ref=work_envelope_ref,
    )
    nodes: list[dict[str, Any]] = [root_node]
    anomalies: list[dict[str, Any]] = []
    receipt_by_lease_and_state: dict[tuple[str, str, str], str] = {}
    for path in transition_receipt_paths:
        ref = str(path)
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            anomalies.append(
                build_anomaly_record(
                    anomaly_code="skipped_transition_ref",
                    detail=f"transition receipt could not be parsed: {ref}",
                    severity="risk",
                    artifact_scope="trace_graph",
                    refs=[ref],
                )
            )
            continue
        lease_id = payload.get("lease_id")
        new_state = payload.get("new_state")
        timestamp_utc = payload.get("timestamp_utc")
        if (
            _is_non_empty_string(lease_id)
            and _is_non_empty_string(new_state)
            and _is_non_empty_string(timestamp_utc)
        ):
            receipt_by_lease_and_state[(lease_id, new_state, timestamp_utc)] = ref
        else:
            anomalies.append(
                build_anomaly_record(
                    anomaly_code="skipped_transition_ref",
                    detail=f"transition receipt missing required linkage fields: {ref}",
                    severity="risk",
                    artifact_scope="trace_graph",
                    refs=[ref],
                )
            )

    lifecycle_rows = {row["lease_id"]: row for row in lifecycle.get("leases", [])}
    matched_receipt_keys: set[tuple[str, str, str]] = set()
    for lease in lease_artifact.get("leases", []):
        worker_node = build_worker_trace_node(
            swarm_run_id=swarm_run_id,
            work_envelope_id=work_envelope_id,
            lease=lease,
            parent_id=root_node["node_id"],
        )
        nodes.append(worker_node)
        lifecycle_row = lifecycle_rows.get(lease["lease_id"]) or {}
        if not lifecycle_row:
            anomalies.append(
                build_anomaly_record(
                    anomaly_code="invalid_lifecycle_linkage",
                    detail=f"lease '{lease['lease_id']}' has no lifecycle row",
                    severity="risk",
                    artifact_scope="trace_graph",
                    refs=[],
                    lease_id=lease["lease_id"],
                    worker_id=lease["worker_id"],
                )
            )
        for event in lifecycle_row.get("transition_history", []):
            event_key = (event["lease_id"], event["new_state"], event["timestamp_utc"])
            receipt_ref = receipt_by_lease_and_state.get(event_key)
            if receipt_ref:
                matched_receipt_keys.add(event_key)
            else:
                anomalies.append(
                    build_anomaly_record(
                        anomaly_code="missing_expected_artifact_ref",
                        detail=(
                            f"lease transition '{event['lease_id']}' -> '{event['new_state']}' "
                            "has no matching transition receipt ref"
                        ),
                        severity="risk",
                        artifact_scope="trace_graph",
                        refs=[],
                        lease_id=event["lease_id"],
                        worker_id=event["worker_id"],
                    )
                )
            nodes.append(
                build_lease_transition_trace_node(
                    event=event,
                    parent_id=worker_node["node_id"],
                    artifact_refs=[receipt_ref] if receipt_ref else [],
                )
            )

    for event_key, receipt_ref in receipt_by_lease_and_state.items():
        if event_key not in matched_receipt_keys:
            anomalies.append(
                build_anomaly_record(
                    anomaly_code="unmatched_transition_ref",
                    detail=f"transition receipt ref was not matched to lifecycle event: {receipt_ref}",
                    severity="elevated",
                    artifact_scope="trace_graph",
                    refs=[receipt_ref],
                )
            )

    trace_graph = {
        "schema": SWARM_TRACE_GRAPH_SCHEMA,
        "schema_version": SWARM_TRACE_GRAPH_SCHEMA_VERSION,
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "root_node_id": root_node["node_id"],
        "updated_at_utc": lease_artifact.get("issued_at_utc") or _utc_now_iso(),
        "nodes": nodes,
        "anomalies": anomalies,
    }
    valid, errors = validate_trace_graph(trace_graph)
    if not valid:
        raise ValueError("invalid_initial_trace_graph: " + "; ".join(errors))
    return trace_graph


def write_trace_graph(runtime_dir: Path, trace_graph: dict[str, Any]) -> Path:
    swarm_run_id = trace_graph.get("swarm_run_id")
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("trace_graph missing swarm_run_id")
    valid, errors = validate_trace_graph(trace_graph)
    if not valid:
        raise ValueError("invalid_trace_graph: " + "; ".join(errors))
    return _write_json_atomic(get_trace_graph_path(runtime_dir, swarm_run_id), trace_graph)


def build_swarm_receipt_bundle(
    *,
    swarm_run_id: str,
    work_envelope_id: str,
    work_envelope_ref: str | None,
    lease_artifact: dict[str, Any] | None,
    lifecycle: dict[str, Any] | None,
    trace_graph: dict[str, Any] | None,
    worker_leases_path: Path,
    ownership_map_path: Path,
    lifecycle_path: Path,
    trace_graph_path: Path,
    transition_receipt_paths: list[Path],
    sandbox_manifest_paths: list[Path] | None = None,
    snapshot_paths: list[Path] | None = None,
    anomalies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("swarm_run_id must be a non-empty string")
    if not _is_non_empty_string(work_envelope_id):
        raise ValueError("work_envelope_id must be a non-empty string")
    sandbox_refs = [str(path) for path in (sandbox_manifest_paths or [])]
    snapshot_refs = [str(path) for path in (snapshot_paths or [])]
    artifact_generation_order = [
        str(worker_leases_path),
        str(ownership_map_path),
        str(lifecycle_path),
    ] + [str(path) for path in transition_receipt_paths] + [str(trace_graph_path)] + sandbox_refs + snapshot_refs
    required_refs = artifact_generation_order.copy()
    missing_refs = [ref for ref in required_refs if not _path_exists(ref)]

    lifecycle_rows = {
        row.get("lease_id"): row
        for row in (lifecycle.get("leases", []) if isinstance(lifecycle, dict) else [])
        if isinstance(row, dict) and _is_non_empty_string(row.get("lease_id"))
    }
    base_anomalies = _merge_anomalies(anomalies or [], trace_graph.get("anomalies", []) if isinstance(trace_graph, dict) else [])
    derived_anomalies: list[dict[str, Any]] = []

    for lease in lease_artifact.get("leases", []) if isinstance(lease_artifact, dict) else []:
        if lease.get("lease_id") not in lifecycle_rows:
            derived_anomalies.append(
                build_anomaly_record(
                    anomaly_code="invalid_lifecycle_linkage",
                    detail=f"lease '{lease.get('lease_id')}' is missing from lifecycle artifact",
                    severity="risk",
                    artifact_scope="receipt_bundle",
                    refs=[str(lifecycle_path)],
                    lease_id=lease.get("lease_id"),
                    worker_id=lease.get("worker_id"),
                )
            )

    if _looks_like_file_ref(work_envelope_ref) and not _path_exists(work_envelope_ref):
        derived_anomalies.append(
            build_anomaly_record(
                anomaly_code="bundle_incomplete",
                detail=f"root authority artifact not yet materialized: {work_envelope_ref}",
                severity="elevated",
                artifact_scope="receipt_bundle",
                refs=[work_envelope_ref],
            )
        )

    for ref in missing_refs:
        derived_anomalies.append(
            build_anomaly_record(
                anomaly_code="missing_expected_artifact_ref",
                detail=f"required artifact ref is missing: {ref}",
                severity="risk",
                artifact_scope="receipt_bundle",
                refs=[ref],
            )
        )

    all_anomalies = _merge_anomalies(base_anomalies, derived_anomalies)
    replay_manifest = _build_replay_manifest(
        work_envelope_ref=work_envelope_ref,
        lease_artifact=lease_artifact,
        lifecycle=lifecycle,
        trace_graph=trace_graph,
        required_refs=required_refs,
        missing_refs=missing_refs,
        artifact_generation_order=artifact_generation_order,
        sandbox_manifest_refs=sandbox_refs,
        snapshot_refs=snapshot_refs,
    )

    if missing_refs or _count_severity(all_anomalies, "risk", "critical") > 0:
        bundle_status = "degraded"
    elif _count_severity(all_anomalies, "elevated") > 0:
        bundle_status = "partial"
    else:
        bundle_status = "complete"

    bundle = {
        "schema": SWARM_RECEIPT_BUNDLE_SCHEMA,
        "schema_version": SWARM_RECEIPT_BUNDLE_SCHEMA_VERSION,
        "receipt_bundle_id": f"bundle::{swarm_run_id}",
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "issued_at_utc": _utc_now_iso(),
        "work_envelope_ref": work_envelope_ref,
        "worker_lease_refs": [str(worker_leases_path), str(ownership_map_path)],
        "sandbox_manifests": sandbox_refs,
        "sandbox_manifest_refs": sandbox_refs,
        "snapshot_refs": snapshot_refs,
        "lifecycle_artifact_refs": [str(lifecycle_path)] + [str(path) for path in transition_receipt_paths],
        "trace_graph_ref": str(trace_graph_path),
        "test_results": [],
        "merge_decision": None,
        "anomalies": all_anomalies,
        "reconciliation_summary": {
            "status": "structural_only",
            "notes": "Execution not enabled; bundle contains staged structural artifacts only.",
            "anomaly_count": len(all_anomalies),
            "risk_anomaly_count": _count_severity(all_anomalies, "risk", "critical"),
        },
        "replay_manifest": replay_manifest,
        "bundle_status": bundle_status,
    }
    valid, errors = validate_swarm_receipt_bundle(bundle)
    if not valid:
        bundle["bundle_status"] = "invalid"
        bundle.setdefault("anomalies", []).append(
            build_anomaly_record(
                anomaly_code="bundle_invalid",
                detail="bundle failed schema validation: " + "; ".join(errors),
                severity="critical",
                artifact_scope="receipt_bundle",
                refs=[str(trace_graph_path)],
            )
        )
    return bundle


def validate_swarm_receipt_bundle(bundle: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return False, ["swarm_receipt_bundle must be a mapping"]
    required = (
        "receipt_bundle_id",
        "swarm_run_id",
        "work_envelope_id",
        "work_envelope_ref",
        "worker_lease_refs",
        "sandbox_manifests",
        "sandbox_manifest_refs",
        "snapshot_refs",
        "lifecycle_artifact_refs",
        "trace_graph_ref",
        "anomalies",
        "bundle_status",
        "replay_manifest",
    )
    for field in required:
        if field not in bundle:
            errors.append(f"swarm_receipt_bundle missing required field '{field}'")
    if bundle.get("bundle_status") not in ALLOWED_BUNDLE_STATUS:
        errors.append("swarm_receipt_bundle.bundle_status must be one of: " + ", ".join(sorted(ALLOWED_BUNDLE_STATUS)))
    if not isinstance(bundle.get("worker_lease_refs"), list) or not bundle.get("worker_lease_refs"):
        errors.append("swarm_receipt_bundle.worker_lease_refs must be a non-empty list")
    if not isinstance(bundle.get("sandbox_manifests"), list):
        errors.append("swarm_receipt_bundle.sandbox_manifests must be a list")
    if not isinstance(bundle.get("sandbox_manifest_refs"), list):
        errors.append("swarm_receipt_bundle.sandbox_manifest_refs must be a list")
    if not isinstance(bundle.get("snapshot_refs"), list):
        errors.append("swarm_receipt_bundle.snapshot_refs must be a list")
    if not isinstance(bundle.get("lifecycle_artifact_refs"), list) or not bundle.get("lifecycle_artifact_refs"):
        errors.append("swarm_receipt_bundle.lifecycle_artifact_refs must be a non-empty list")
    if not _is_non_empty_string(bundle.get("trace_graph_ref")):
        errors.append("swarm_receipt_bundle.trace_graph_ref must be a non-empty string")
    if not _is_non_empty_string(bundle.get("work_envelope_ref")):
        errors.append("swarm_receipt_bundle.work_envelope_ref must be a non-empty string")
    if not isinstance(bundle.get("anomalies"), list):
        errors.append("swarm_receipt_bundle.anomalies must be a list")
    replay_manifest = bundle.get("replay_manifest")
    if not isinstance(replay_manifest, dict):
        errors.append("swarm_receipt_bundle.replay_manifest must be a mapping")
    else:
        for field in (
            "root_authority_ref",
            "worker_set",
            "transition_sequence",
            "artifact_generation_order",
            "required_refs",
            "missing_refs",
            "replay_guarantee",
            "sandbox_manifest_refs",
            "snapshot_refs",
            "diff_refs",
        ):
            if field not in replay_manifest:
                errors.append(f"swarm_receipt_bundle.replay_manifest missing required field '{field}'")
        if replay_manifest.get("replay_guarantee") not in ALLOWED_REPLAY_GUARANTEE:
            errors.append(
                "swarm_receipt_bundle.replay_manifest.replay_guarantee must be one of: "
                + ", ".join(sorted(ALLOWED_REPLAY_GUARANTEE))
            )
    if bundle.get("bundle_status") == "complete":
        if isinstance(replay_manifest, dict) and replay_manifest.get("missing_refs"):
            errors.append("swarm_receipt_bundle.bundle_status cannot be complete when replay_manifest.missing_refs is non-empty")
    if bundle.get("sandbox_manifests") != bundle.get("sandbox_manifest_refs"):
        errors.append("swarm_receipt_bundle.sandbox_manifests must match sandbox_manifest_refs")
    return len(errors) == 0, errors


def write_swarm_receipt_bundle(runtime_dir: Path, bundle: dict[str, Any]) -> Path:
    swarm_run_id = bundle.get("swarm_run_id")
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("swarm_receipt_bundle missing swarm_run_id")
    valid, errors = validate_swarm_receipt_bundle(bundle)
    if not valid:
        raise ValueError("invalid_swarm_receipt_bundle: " + "; ".join(errors))
    return _write_json_atomic(get_receipt_bundle_path(runtime_dir, swarm_run_id), bundle)


def refresh_swarm_receipt_bundle(runtime_dir: Path, swarm_run_id: str) -> dict[str, Any]:
    bundle_path = get_receipt_bundle_path(runtime_dir, swarm_run_id)
    if not bundle_path.exists():
        raise FileNotFoundError(f"receipt_bundle missing: {bundle_path}")
    bundle = _read_json(bundle_path)

    trace_graph_ref = bundle.get("trace_graph_ref")
    worker_lease_refs = bundle.get("worker_lease_refs") or []
    lifecycle_artifact_refs = bundle.get("lifecycle_artifact_refs") or []
    lease_artifact = _read_json(Path(worker_lease_refs[0])) if len(worker_lease_refs) > 0 and _path_exists(worker_lease_refs[0]) else {}
    lifecycle = _read_json(Path(lifecycle_artifact_refs[0])) if len(lifecycle_artifact_refs) > 0 and _path_exists(lifecycle_artifact_refs[0]) else {}
    trace_graph = _read_json(Path(trace_graph_ref)) if _path_exists(trace_graph_ref) else {}
    sandbox_manifest_refs = _discover_sandbox_manifest_refs(runtime_dir, swarm_run_id)
    snapshot_refs = _discover_snapshot_refs(runtime_dir, swarm_run_id)
    refreshed = build_swarm_receipt_bundle(
        swarm_run_id=bundle["swarm_run_id"],
        work_envelope_id=bundle["work_envelope_id"],
        work_envelope_ref=bundle.get("work_envelope_ref"),
        lease_artifact=lease_artifact,
        lifecycle=lifecycle,
        trace_graph=trace_graph,
        worker_leases_path=Path(worker_lease_refs[0]),
        ownership_map_path=Path(worker_lease_refs[1]),
        lifecycle_path=Path(lifecycle_artifact_refs[0]),
        trace_graph_path=Path(trace_graph_ref),
        transition_receipt_paths=[Path(ref) for ref in lifecycle_artifact_refs[1:]],
        sandbox_manifest_paths=[Path(ref) for ref in sandbox_manifest_refs],
        snapshot_paths=[Path(ref) for ref in snapshot_refs],
        anomalies=[],
    )
    _write_json_atomic(bundle_path, refreshed)
    return refreshed


def append_transition_to_trace_graph(
    runtime_dir: Path,
    *,
    swarm_run_id: str,
    event: dict[str, Any],
    transition_receipt_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_graph_path = get_trace_graph_path(runtime_dir, swarm_run_id)
    bundle_path = get_receipt_bundle_path(runtime_dir, swarm_run_id)
    if not trace_graph_path.exists():
        raise FileNotFoundError(f"trace_graph missing: {trace_graph_path}")
    if not bundle_path.exists():
        raise FileNotFoundError(f"receipt_bundle missing: {bundle_path}")

    trace_graph = _read_json(trace_graph_path)
    bundle = _read_json(bundle_path)
    worker_node_id = f"worker::{event['lease_id']}"
    worker_node = next((node for node in trace_graph.get("nodes", []) if node.get("node_id") == worker_node_id), None)
    if not worker_node:
        raise ValueError(f"missing worker trace node for lease_id '{event['lease_id']}'")

    transition_node = build_lease_transition_trace_node(
        event=event,
        parent_id=worker_node_id,
        artifact_refs=[str(transition_receipt_path)],
    )
    trace_graph.setdefault("nodes", []).append(transition_node)
    trace_graph["updated_at_utc"] = event["timestamp_utc"]
    valid, errors = validate_trace_graph(trace_graph)
    if not valid:
        raise ValueError("invalid_trace_graph_after_transition: " + "; ".join(errors))
    _write_json_atomic(trace_graph_path, trace_graph)

    lifecycle_refs = bundle.setdefault("lifecycle_artifact_refs", [])
    transition_ref = str(transition_receipt_path)
    if transition_ref not in lifecycle_refs:
        lifecycle_refs.append(transition_ref)
    bundle["issued_at_utc"] = event["timestamp_utc"]
    _write_json_atomic(bundle_path, bundle)
    refreshed_bundle = refresh_swarm_receipt_bundle(runtime_dir, swarm_run_id)
    return trace_graph, refreshed_bundle


def append_sandbox_preparation_to_trace_graph(
    runtime_dir: Path,
    *,
    swarm_run_id: str,
    sandbox_manifests: list[dict[str, Any]],
    sandbox_manifest_paths: list[Path],
    snapshot_records: list[dict[str, Any]],
    snapshot_paths: list[Path],
) -> tuple[dict[str, Any], dict[str, Any]]:
    trace_graph_path = get_trace_graph_path(runtime_dir, swarm_run_id)
    bundle_path = get_receipt_bundle_path(runtime_dir, swarm_run_id)
    if not trace_graph_path.exists():
        raise FileNotFoundError(f"trace_graph missing: {trace_graph_path}")
    if not bundle_path.exists():
        raise FileNotFoundError(f"receipt_bundle missing: {bundle_path}")

    trace_graph = _read_json(trace_graph_path)
    manifest_by_lease = {item.get("lease_id"): item for item in sandbox_manifests if isinstance(item, dict)}
    manifest_path_by_lease = {
        manifest.get("lease_id"): path
        for manifest, path in zip(sandbox_manifests, sandbox_manifest_paths, strict=False)
        if isinstance(manifest, dict)
    }
    snapshot_by_lease = {item.get("lease_id"): item for item in snapshot_records if isinstance(item, dict)}
    snapshot_path_by_lease = {
        snapshot.get("lease_id"): path
        for snapshot, path in zip(snapshot_records, snapshot_paths, strict=False)
        if isinstance(snapshot, dict)
    }

    for worker_node in [node for node in trace_graph.get("nodes", []) if node.get("action_type") == WORKER_ACTION_TYPE]:
        lease_id = worker_node.get("lease_id")
        sandbox_manifest = manifest_by_lease.get(lease_id)
        if not sandbox_manifest:
            continue
        sandbox_node = build_sandbox_prepare_trace_node(
            sandbox_manifest=sandbox_manifest,
            parent_id=worker_node["node_id"],
            artifact_refs=[str(manifest_path_by_lease[lease_id])],
        )
        if not any(node.get("node_id") == sandbox_node["node_id"] for node in trace_graph.get("nodes", [])):
            trace_graph.setdefault("nodes", []).append(sandbox_node)

        snapshot_record = snapshot_by_lease.get(lease_id)
        snapshot_path = snapshot_path_by_lease.get(lease_id)
        if not snapshot_record or snapshot_path is None:
            continue
        artifact_refs = [str(snapshot_path)] + _as_unique_string_list(snapshot_record.get("artifact_paths"))
        snapshot_node = build_snapshot_pre_execution_trace_node(
            snapshot_record=snapshot_record,
            sandbox_id=sandbox_manifest["sandbox_id"],
            work_envelope_id=sandbox_manifest["work_envelope_id"],
            parent_id=sandbox_node["node_id"],
            artifact_refs=artifact_refs,
        )
        if not any(node.get("node_id") == snapshot_node["node_id"] for node in trace_graph.get("nodes", [])):
            trace_graph.setdefault("nodes", []).append(snapshot_node)

    trace_graph["updated_at_utc"] = _utc_now_iso()
    valid, errors = validate_trace_graph(trace_graph)
    if not valid:
        raise ValueError("invalid_trace_graph_after_sandbox_prepare: " + "; ".join(errors))
    _write_json_atomic(trace_graph_path, trace_graph)

    bundle = _read_json(bundle_path)
    bundle["sandbox_manifests"] = [str(path) for path in sandbox_manifest_paths]
    bundle["sandbox_manifest_refs"] = [str(path) for path in sandbox_manifest_paths]
    bundle["snapshot_refs"] = [str(path) for path in snapshot_paths]
    _write_json_atomic(bundle_path, bundle)
    refreshed_bundle = refresh_swarm_receipt_bundle(runtime_dir, swarm_run_id)
    return trace_graph, refreshed_bundle
