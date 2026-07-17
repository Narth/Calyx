"""Worker lease schema validation and static issuance for governed swarm preparation."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .envelope import WorkEnvelope
from .swarm_trace import (
    append_transition_to_trace_graph,
    build_initial_trace_graph,
    build_swarm_receipt_bundle,
    write_swarm_receipt_bundle,
    write_trace_graph,
)
from .swarm_work_envelope import (
    ALLOWED_TOOL_CLASSES,
    REQUIRED_OWNERSHIP_SCOPE_FIELDS,
    validate_network_scope,
)


WORKER_LEASE_SCHEMA = "station.swarm.worker_lease.v1"
WORKER_LEASE_SCHEMA_VERSION = "1.0.0"
WORKER_LEASES_ARTIFACT_SCHEMA = "station.swarm.worker_leases.v1"
WORKER_LEASES_ARTIFACT_SCHEMA_VERSION = "1.0.0"
WORKER_OWNERSHIP_MAP_SCHEMA = "station.swarm.ownership_map.v1"
WORKER_OWNERSHIP_MAP_SCHEMA_VERSION = "1.0.0"
WORKER_LEASE_LIFECYCLE_SCHEMA = "station.swarm.lease_lifecycle.v1"
WORKER_LEASE_LIFECYCLE_SCHEMA_VERSION = "1.0.0"
WORKER_LEASE_ISSUANCE_RECEIPT_SCHEMA = "station.swarm.worker_lease_issuance.v1"
WORKER_LEASE_TRANSITION_RECEIPT_SCHEMA = "station.swarm.worker_lease_transition.v1"
ALLOWED_LEASE_STATES = frozenset({"proposed", "approved", "active", "expired", "revoked", "completed"})
ALLOWED_TRIGGER_SOURCES = frozenset({"system", "operator", "validation", "timeout"})
TERMINAL_LEASE_STATES = frozenset({"completed", "revoked", "expired"})
ALLOWED_LEASE_TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"approved"}),
    "approved": frozenset({"active", "revoked"}),
    "active": frozenset({"completed", "revoked", "expired"}),
    "completed": frozenset(),
    "revoked": frozenset(),
    "expired": frozenset(),
}
STATIC_LEASE_STATE = "proposed"
DEFAULT_WORKER_MAX_RUNTIME_SEC = 300
DEFAULT_WORKER_MAX_TOKENS = 4000
REQUIRED_WORKER_LEASE_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "swarm_run_id",
        "work_envelope_id",
        "lease_id",
        "worker_id",
        "lease_state",
        "issued_at_utc",
        "expires_at_utc",
        "max_runtime_sec",
        "token_budget",
        "compute_budget",
        "ownership_scope",
        "allowed_tool_classes",
        "network_scope",
        "success_criteria",
        "approval_context",
        "revocation_reason",
        "notes",
    }
)


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


def _parse_iso(value: Any) -> datetime | None:
    if not _is_non_empty_string(value):
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _coerce_utc_datetime(value: str | None) -> datetime:
    if value is None:
        return _utc_now()
    parsed = _parse_iso(value)
    if parsed is None:
        raise ValueError("issued_at_utc must be a valid ISO-8601 timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_segment(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


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


def _default_token_budget() -> dict[str, Any]:
    return {
        "max_tokens": DEFAULT_WORKER_MAX_TOKENS,
        "enforcement_status": "conceptual_static_v1",
    }


def _default_compute_budget(max_runtime_sec: int) -> dict[str, Any]:
    return {
        "max_tool_calls": max(10, min(50, max_runtime_sec // 30)),
        "enforcement_status": "conceptual_static_v1",
    }


def _resolve_swarm_envelope(envelope: WorkEnvelope | dict[str, Any]) -> WorkEnvelope:
    return envelope if isinstance(envelope, WorkEnvelope) else WorkEnvelope.from_dict(envelope)


def _get_scope_swarm(envelope: WorkEnvelope) -> dict[str, Any]:
    scope_swarm = (envelope.scope or {}).get("swarm")
    if not isinstance(scope_swarm, dict):
        raise ValueError("scope.swarm must be present for static worker lease issuance")
    return scope_swarm


def _get_constraints_swarm(envelope: WorkEnvelope) -> dict[str, Any]:
    constraints_swarm = (envelope.constraints or {}).get("swarm")
    if not isinstance(constraints_swarm, dict):
        raise ValueError("constraints.swarm must be present for static worker lease issuance")
    return constraints_swarm


def _root_max_runtime_sec(envelope: WorkEnvelope) -> int:
    raw_timeout = (envelope.constraints or {}).get("timeout_seconds")
    if isinstance(raw_timeout, int) and raw_timeout > 0:
        return raw_timeout
    return DEFAULT_WORKER_MAX_RUNTIME_SEC


def build_static_worker_leases_artifact(
    envelope: WorkEnvelope | dict[str, Any],
    *,
    issued_at_utc: str | None = None,
) -> dict[str, Any]:
    env = _resolve_swarm_envelope(envelope)
    swarm_valid, swarm_errors = env.validate_swarm_extensions()
    if not swarm_valid:
        raise ValueError("invalid_swarm_extension: " + "; ".join(swarm_errors))

    scope_swarm = _get_scope_swarm(env)
    _get_constraints_swarm(env)
    worker_plan = scope_swarm.get("worker_plan")
    if not isinstance(worker_plan, list) or not worker_plan:
        raise ValueError("scope.swarm.worker_plan must be a non-empty list")

    issued_at = _coerce_utc_datetime(issued_at_utc)
    issued_at_text = _to_utc_iso(issued_at)
    max_runtime_sec = _root_max_runtime_sec(env)
    expires_at_text = _to_utc_iso(issued_at + timedelta(seconds=max_runtime_sec))

    leases: list[dict[str, Any]] = []
    for index, worker in enumerate(worker_plan):
        if not isinstance(worker, dict):
            raise ValueError(f"scope.swarm.worker_plan[{index}] must be a mapping")
        worker_id = worker.get("worker_id")
        if not _is_non_empty_string(worker_id):
            raise ValueError(f"scope.swarm.worker_plan[{index}].worker_id must be a non-empty string")
        normalized_worker_id = worker_id.strip()
        lease = {
            "schema": WORKER_LEASE_SCHEMA,
            "schema_version": WORKER_LEASE_SCHEMA_VERSION,
            "swarm_run_id": scope_swarm["swarm_run_id"],
            "work_envelope_id": env.envelope_id,
            "lease_id": f"{scope_swarm['swarm_run_id']}--{normalized_worker_id}",
            "worker_id": normalized_worker_id,
            "lease_state": STATIC_LEASE_STATE,
            "issued_at_utc": issued_at_text,
            "expires_at_utc": expires_at_text,
            "max_runtime_sec": max_runtime_sec,
            "token_budget": _default_token_budget(),
            "compute_budget": _default_compute_budget(max_runtime_sec),
            "ownership_scope": worker.get("ownership_scope"),
            "allowed_tool_classes": worker.get("allowed_tool_classes"),
            "network_scope": worker.get("network_scope"),
            "success_criteria": worker.get("success_criteria"),
            "approval_context": {
                "requires_human_approval": env.requires_human_approval,
                "approval_token_present": bool(env.approval_token),
                "issuance_mode": "phase1_static",
            },
            "revocation_reason": None,
            "notes": "Static issuance only. Worker execution remains disabled.",
        }
        valid, errors = validate_worker_lease(lease, envelope_scope_swarm=scope_swarm)
        if not valid:
            raise ValueError(
                f"worker_lease_derivation_failed:{normalized_worker_id}: " + "; ".join(errors)
            )
        leases.append(lease)

    return {
        "schema": WORKER_LEASES_ARTIFACT_SCHEMA,
        "schema_version": WORKER_LEASES_ARTIFACT_SCHEMA_VERSION,
        "swarm_run_id": scope_swarm["swarm_run_id"],
        "work_envelope_id": env.envelope_id,
        "lease_state": STATIC_LEASE_STATE,
        "issued_at_utc": issued_at_text,
        "worker_count": len(leases),
        "leases": leases,
    }


def get_swarm_run_dir(runtime_dir: Path, swarm_run_id: str) -> Path:
    return runtime_dir / "cbo" / "swarm" / _safe_segment(swarm_run_id)


def get_worker_leases_path(runtime_dir: Path, swarm_run_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "worker_leases.json"


def get_worker_ownership_map_path(runtime_dir: Path, swarm_run_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "ownership_map.json"


def get_lease_lifecycle_path(runtime_dir: Path, swarm_run_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "lease_lifecycle.json"


def build_worker_ownership_map(lease_artifact: dict[str, Any]) -> dict[str, Any]:
    leases = lease_artifact.get("leases")
    if not isinstance(leases, list) or not leases:
        raise ValueError("worker_leases artifact must include a non-empty leases list")

    path_map: dict[str, dict[str, list[str]]] = {}
    worker_rows: list[dict[str, Any]] = []
    worker_ids: set[str] = set()
    conflicts: list[dict[str, Any]] = []

    for lease in leases:
        worker_id = lease.get("worker_id")
        if not _is_non_empty_string(worker_id):
            raise ValueError("worker_lease missing worker_id while building ownership_map")
        normalized_worker_id = worker_id.strip()
        if normalized_worker_id in worker_ids:
            conflicts.append(
                {
                    "conflict_code": "duplicate_worker_id",
                    "worker_ids": [normalized_worker_id],
                    "path": None,
                    "detail": f"duplicate worker_id '{normalized_worker_id}' present in worker lease set",
                }
            )
        worker_ids.add(normalized_worker_id)

        ownership_scope = lease.get("ownership_scope") or {}
        read_paths = _as_unique_string_list(ownership_scope.get("read_paths"))
        write_paths = _as_unique_string_list(ownership_scope.get("write_paths"))
        deny_paths = _as_unique_string_list(ownership_scope.get("deny_paths"))
        worker_rows.append(
            {
                "worker_id": normalized_worker_id,
                "lease_id": lease.get("lease_id"),
                "read_paths": read_paths,
                "write_paths": write_paths,
                "deny_paths": deny_paths,
            }
        )

        for category, paths in (
            ("readers", read_paths),
            ("writers", write_paths),
            ("denied_for", deny_paths),
        ):
            for path in paths:
                row = path_map.setdefault(path, {"readers": [], "writers": [], "denied_for": []})
                if normalized_worker_id not in row[category]:
                    row[category].append(normalized_worker_id)

    path_ownership = [
        {
            "path": path,
            "readers": sorted(entry["readers"]),
            "writers": sorted(entry["writers"]),
            "denied_for": sorted(entry["denied_for"]),
        }
        for path, entry in sorted(path_map.items())
    ]
    overlapping_write_paths = [
        {
            "path": entry["path"],
            "worker_ids": entry["writers"],
        }
        for entry in path_ownership
        if len(entry["writers"]) > 1
    ]
    return {
        "schema": WORKER_OWNERSHIP_MAP_SCHEMA,
        "schema_version": WORKER_OWNERSHIP_MAP_SCHEMA_VERSION,
        "swarm_run_id": lease_artifact.get("swarm_run_id"),
        "work_envelope_id": lease_artifact.get("work_envelope_id"),
        "lease_state": lease_artifact.get("lease_state"),
        "worker_count": lease_artifact.get("worker_count", len(worker_rows)),
        "workers": worker_rows,
        "path_ownership": path_ownership,
        "overlapping_write_paths": overlapping_write_paths,
        "conflicts": conflicts,
    }


def validate_static_worker_lease_set(
    envelope: WorkEnvelope | dict[str, Any],
    *,
    issued_at_utc: str | None = None,
) -> tuple[bool, list[str], dict[str, Any], dict[str, Any]]:
    env = _resolve_swarm_envelope(envelope)
    lease_artifact = build_static_worker_leases_artifact(env, issued_at_utc=issued_at_utc)
    ownership_map = build_worker_ownership_map(lease_artifact)
    constraints_swarm = _get_constraints_swarm(env)
    overlap_declared = bool(constraints_swarm.get("overlapping_write_scope_declared"))

    errors: list[str] = []
    conflicts = list(ownership_map.get("conflicts", []))
    for worker in ownership_map.get("workers", []):
        worker_id = worker.get("worker_id", "unknown-worker")
        read_paths = set(_as_unique_string_list(worker.get("read_paths")))
        write_paths = set(_as_unique_string_list(worker.get("write_paths")))
        deny_paths = set(_as_unique_string_list(worker.get("deny_paths")))
        conflicting_reads = sorted(read_paths & deny_paths)
        conflicting_writes = sorted(write_paths & deny_paths)
        for path in conflicting_reads:
            detail = f"worker '{worker_id}' declares path '{path}' in both read_paths and deny_paths"
            conflicts.append(
                {
                    "conflict_code": "conflicting_ownership_scope",
                    "worker_ids": [worker_id],
                    "path": path,
                    "detail": detail,
                }
            )
            errors.append(detail)
        for path in conflicting_writes:
            detail = f"worker '{worker_id}' declares path '{path}' in both write_paths and deny_paths"
            conflicts.append(
                {
                    "conflict_code": "conflicting_ownership_scope",
                    "worker_ids": [worker_id],
                    "path": path,
                    "detail": detail,
                }
            )
            errors.append(detail)

    for overlap in ownership_map.get("overlapping_write_paths", []):
        path = overlap.get("path")
        worker_ids = overlap.get("worker_ids") or []
        if overlap_declared:
            detail = (
                f"workers {', '.join(worker_ids)} declare shared write path '{path}', "
                "but explicit overlap resolution is not supported in phase2"
            )
            conflict_code = "ambiguous_ownership_resolution"
        else:
            detail = (
                f"workers {', '.join(worker_ids)} overlap on write path '{path}' without explicit declaration"
            )
            conflict_code = "overlapping_write_scope"
        conflicts.append(
            {
                "conflict_code": conflict_code,
                "worker_ids": worker_ids,
                "path": path,
                "detail": detail,
            }
        )
        errors.append(detail)

    for conflict in ownership_map.get("conflicts", []):
        detail = conflict.get("detail")
        if isinstance(detail, str) and detail not in errors:
            errors.append(detail)
    ownership_map["conflicts"] = conflicts
    return len(errors) == 0, errors, lease_artifact, ownership_map


def write_worker_leases_artifact(runtime_dir: Path, lease_artifact: dict[str, Any]) -> Path:
    swarm_run_id = lease_artifact.get("swarm_run_id")
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("worker_leases artifact missing swarm_run_id")
    path = get_worker_leases_path(runtime_dir, swarm_run_id.strip())
    return _write_json_atomic(path, lease_artifact)


def write_worker_ownership_map(runtime_dir: Path, ownership_map: dict[str, Any]) -> Path:
    swarm_run_id = ownership_map.get("swarm_run_id")
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("ownership_map missing swarm_run_id")
    path = get_worker_ownership_map_path(runtime_dir, swarm_run_id.strip())
    return _write_json_atomic(path, ownership_map)


def _normalize_evidence_refs(value: Any) -> list[str]:
    return _as_unique_string_list(value)


def _validate_transition_justification(
    *,
    transition_reason: str | None,
    trigger_source: str | None,
    evidence_refs: Any,
    timestamp_utc: str | None,
) -> tuple[bool, list[str], str, str, list[str], str]:
    errors: list[str] = []
    if not _is_non_empty_string(transition_reason):
        errors.append("transition_reason must be a non-empty string")
    if trigger_source not in ALLOWED_TRIGGER_SOURCES:
        errors.append(
            "trigger_source must be one of: " + ", ".join(sorted(ALLOWED_TRIGGER_SOURCES))
        )
    evidence = _normalize_evidence_refs(evidence_refs)
    resolved_ts = timestamp_utc or _to_utc_iso(_utc_now())
    if _parse_iso(resolved_ts) is None:
        errors.append("timestamp_utc must be a valid ISO-8601 timestamp")
    return (
        len(errors) == 0,
        errors,
        transition_reason.strip() if _is_non_empty_string(transition_reason) else "",
        trigger_source or "",
        evidence,
        resolved_ts,
    )


def _build_transition_event(
    *,
    swarm_run_id: str,
    work_envelope_id: str,
    lease_id: str,
    worker_id: str,
    previous_state: str | None,
    new_state: str,
    transition_reason: str,
    trigger_source: str,
    timestamp_utc: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    return {
        "transition_id": f"{lease_id}--{new_state}--{timestamp_utc}",
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "lease_id": lease_id,
        "worker_id": worker_id,
        "previous_state": previous_state,
        "new_state": new_state,
        "transition_reason": transition_reason,
        "trigger_source": trigger_source,
        "timestamp_utc": timestamp_utc,
        "evidence_refs": evidence_refs,
    }


def _emit_swarm_lease_transition_receipt(
    runtime_dir: Path,
    event: dict[str, Any],
) -> Path:
    ts = _parse_iso(event["timestamp_utc"]) or _utc_now()
    receipts_dir = runtime_dir / "receipts" / "audit"
    filename = (
        f"swarm_lease_transition__{ts.strftime('%Y%m%d_%H%M%S_%f')}_{_safe_segment(event['lease_id'])}.json"
    )
    payload = {
        "schema": WORKER_LEASE_TRANSITION_RECEIPT_SCHEMA,
        "receipt_type": "swarm_lease_transition",
        "timestamp_utc": event["timestamp_utc"],
        "phase": "lease_transition",
        "status": "completed",
        "swarm_run_id": event["swarm_run_id"],
        "work_envelope_id": event["work_envelope_id"],
        "lease_id": event["lease_id"],
        "worker_id": event["worker_id"],
        "previous_state": event["previous_state"],
        "new_state": event["new_state"],
        "transition_reason": event["transition_reason"],
        "trigger_source": event["trigger_source"],
        "evidence_refs": event["evidence_refs"],
    }
    return _write_json_atomic(receipts_dir / filename, payload)


def build_initial_lease_lifecycle(
    lease_artifact: dict[str, Any],
    *,
    transition_reason: str = "static lease issuance",
    trigger_source: str = "system",
    evidence_refs: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    swarm_run_id = lease_artifact.get("swarm_run_id")
    work_envelope_id = lease_artifact.get("work_envelope_id")
    if not _is_non_empty_string(swarm_run_id) or not _is_non_empty_string(work_envelope_id):
        raise ValueError("lease_artifact missing swarm_run_id or work_envelope_id")
    ok, errors, reason, trigger, evidence, timestamp_utc = _validate_transition_justification(
        transition_reason=transition_reason,
        trigger_source=trigger_source,
        evidence_refs=evidence_refs or [],
        timestamp_utc=lease_artifact.get("issued_at_utc"),
    )
    if not ok:
        raise ValueError("invalid_initial_lease_transition: " + "; ".join(errors))

    lifecycle_rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for lease in lease_artifact.get("leases", []):
        event = _build_transition_event(
            swarm_run_id=swarm_run_id,
            work_envelope_id=work_envelope_id,
            lease_id=lease["lease_id"],
            worker_id=lease["worker_id"],
            previous_state=None,
            new_state=lease["lease_state"],
            transition_reason=reason,
            trigger_source=trigger,
            timestamp_utc=timestamp_utc,
            evidence_refs=evidence,
        )
        events.append(event)
        lifecycle_rows.append(
            {
                "lease_id": lease["lease_id"],
                "worker_id": lease["worker_id"],
                "current_state": lease["lease_state"],
                "terminal_state": None,
                "transition_history": [event],
            }
        )

    lifecycle = {
        "schema": WORKER_LEASE_LIFECYCLE_SCHEMA,
        "schema_version": WORKER_LEASE_LIFECYCLE_SCHEMA_VERSION,
        "swarm_run_id": swarm_run_id,
        "work_envelope_id": work_envelope_id,
        "updated_at_utc": timestamp_utc,
        "lease_count": len(lifecycle_rows),
        "leases": lifecycle_rows,
    }
    return lifecycle, events


def write_lease_lifecycle(
    runtime_dir: Path,
    lifecycle: dict[str, Any],
) -> Path:
    swarm_run_id = lifecycle.get("swarm_run_id")
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("lease_lifecycle missing swarm_run_id")
    return _write_json_atomic(get_lease_lifecycle_path(runtime_dir, swarm_run_id), lifecycle)


def transition_worker_lease_state(
    runtime_dir: Path,
    *,
    swarm_run_id: str,
    lease_id: str,
    new_state: str,
    transition_reason: str,
    trigger_source: str,
    evidence_refs: list[str] | None = None,
    timestamp_utc: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    if not _is_non_empty_string(swarm_run_id):
        raise ValueError("swarm_run_id must be a non-empty string")
    if not _is_non_empty_string(lease_id):
        raise ValueError("lease_id must be a non-empty string")
    if new_state not in ALLOWED_LEASE_STATES:
        raise ValueError("new_state must be one of: " + ", ".join(sorted(ALLOWED_LEASE_STATES)))

    ok, errors, reason, trigger, evidence, resolved_ts = _validate_transition_justification(
        transition_reason=transition_reason,
        trigger_source=trigger_source,
        evidence_refs=evidence_refs or [],
        timestamp_utc=timestamp_utc,
    )
    if not ok:
        raise ValueError("invalid_transition_justification: " + "; ".join(errors))

    lease_artifact_path = get_worker_leases_path(runtime_dir, swarm_run_id)
    lifecycle_path = get_lease_lifecycle_path(runtime_dir, swarm_run_id)
    if not lease_artifact_path.exists():
        raise FileNotFoundError(f"worker_leases artifact missing: {lease_artifact_path}")
    if not lifecycle_path.exists():
        raise FileNotFoundError(f"lease_lifecycle artifact missing: {lifecycle_path}")

    lease_artifact = _read_json(lease_artifact_path)
    lifecycle = _read_json(lifecycle_path)

    lease_row = next((row for row in lease_artifact.get("leases", []) if row.get("lease_id") == lease_id), None)
    if not lease_row:
        raise ValueError(f"lease_id not found: {lease_id}")
    lifecycle_row = next((row for row in lifecycle.get("leases", []) if row.get("lease_id") == lease_id), None)
    if not lifecycle_row:
        raise ValueError(f"lease_id missing from lifecycle artifact: {lease_id}")

    previous_state = lease_row.get("lease_state")
    if previous_state not in ALLOWED_LEASE_STATES:
        raise ValueError(f"current lease state is invalid: {previous_state}")
    if new_state not in ALLOWED_LEASE_TRANSITIONS.get(previous_state, frozenset()):
        raise ValueError(f"invalid_lease_transition:{previous_state}->{new_state}")

    event = _build_transition_event(
        swarm_run_id=swarm_run_id,
        work_envelope_id=lease_row["work_envelope_id"],
        lease_id=lease_row["lease_id"],
        worker_id=lease_row["worker_id"],
        previous_state=previous_state,
        new_state=new_state,
        transition_reason=reason,
        trigger_source=trigger,
        timestamp_utc=resolved_ts,
        evidence_refs=evidence,
    )

    lease_row["lease_state"] = new_state
    if new_state == "revoked":
        lease_row["revocation_reason"] = reason
    lifecycle_row["current_state"] = new_state
    lifecycle_row["terminal_state"] = new_state if new_state in TERMINAL_LEASE_STATES else None
    lifecycle_row.setdefault("transition_history", []).append(event)
    lifecycle["updated_at_utc"] = resolved_ts

    _write_json_atomic(lease_artifact_path, lease_artifact)
    _write_json_atomic(lifecycle_path, lifecycle)
    receipt_path = _emit_swarm_lease_transition_receipt(runtime_dir, event)
    append_transition_to_trace_graph(
        runtime_dir,
        swarm_run_id=swarm_run_id,
        event=event,
        transition_receipt_path=receipt_path,
    )
    return lease_artifact, lifecycle, receipt_path


def write_static_lease_issuance_receipt(
    runtime_dir: Path,
    lease_artifact: dict[str, Any],
    *,
    artifact_path: Path,
    ownership_map: dict[str, Any],
    ownership_map_path: Path,
    lifecycle_path: Path,
    trace_graph_path: Path,
    receipt_bundle_path: Path,
    transition_receipt_paths: list[Path],
) -> Path:
    ts = _utc_now()
    payload = {
        "schema": WORKER_LEASE_ISSUANCE_RECEIPT_SCHEMA,
        "receipt_type": "swarm.worker_lease.issuance_static",
        "timestamp_utc": _to_utc_iso(ts),
        "phase": "lease_issuance",
        "status": "completed",
        "swarm_run_id": lease_artifact["swarm_run_id"],
        "work_envelope_id": lease_artifact["work_envelope_id"],
        "lease_state": lease_artifact["lease_state"],
        "worker_count": lease_artifact["worker_count"],
        "worker_ids": [lease["worker_id"] for lease in lease_artifact.get("leases", [])],
        "artifact_path": str(artifact_path),
        "ownership_map_path": str(ownership_map_path),
        "lease_lifecycle_path": str(lifecycle_path),
        "trace_graph_path": str(trace_graph_path),
        "receipt_bundle_path": str(receipt_bundle_path),
        "ownership_conflict_count": len(ownership_map.get("conflicts", [])),
        "transition_receipt_count": len(transition_receipt_paths),
        "transition_receipt_paths": [str(path) for path in transition_receipt_paths],
        "constraint_inheritance_verified": True,
        "worker_execution_enabled": False,
        "worker_activation_enabled": False,
    }
    receipts_dir = runtime_dir / "receipts" / "audit"
    filename = f"swarm_worker_lease_issuance__{ts.strftime('%Y%m%d_%H%M%S')}.json"
    return _write_json_atomic(receipts_dir / filename, payload)


def issue_static_worker_leases(
    envelope: WorkEnvelope | dict[str, Any],
    runtime_dir: Path,
    *,
    issued_at_utc: str | None = None,
    work_envelope_ref: str | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    Path,
    Path,
    Path,
    Path,
    Path,
    Path,
    list[Path],
]:
    valid, errors, lease_artifact, ownership_map = validate_static_worker_lease_set(
        envelope,
        issued_at_utc=issued_at_utc,
    )
    if not valid:
        raise ValueError("invalid_swarm_lease_set: " + "; ".join(errors))
    lifecycle, transition_events = build_initial_lease_lifecycle(
        lease_artifact,
        evidence_refs=[f"work_envelope:{lease_artifact['work_envelope_id']}"],
    )
    artifact_path: Path | None = None
    ownership_map_path: Path | None = None
    lifecycle_path: Path | None = None
    trace_graph_path: Path | None = None
    receipt_bundle_path: Path | None = None
    receipt_path: Path | None = None
    transition_receipt_paths: list[Path] = []
    trace_graph: dict[str, Any] | None = None
    receipt_bundle: dict[str, Any] | None = None
    try:
        artifact_path = write_worker_leases_artifact(runtime_dir, lease_artifact)
        ownership_map_path = write_worker_ownership_map(runtime_dir, ownership_map)
        lifecycle_path = write_lease_lifecycle(runtime_dir, lifecycle)
        for event in transition_events:
            transition_receipt_paths.append(_emit_swarm_lease_transition_receipt(runtime_dir, event))
        trace_graph = build_initial_trace_graph(
            lease_artifact=lease_artifact,
            lifecycle=lifecycle,
            transition_receipt_paths=transition_receipt_paths,
            work_envelope_ref=work_envelope_ref or f"work_envelope:{lease_artifact['work_envelope_id']}",
        )
        trace_graph_path = write_trace_graph(runtime_dir, trace_graph)
        receipt_bundle = build_swarm_receipt_bundle(
            swarm_run_id=lease_artifact["swarm_run_id"],
            work_envelope_id=lease_artifact["work_envelope_id"],
            work_envelope_ref=work_envelope_ref or f"work_envelope:{lease_artifact['work_envelope_id']}",
            lease_artifact=lease_artifact,
            lifecycle=lifecycle,
            trace_graph=trace_graph,
            worker_leases_path=artifact_path,
            ownership_map_path=ownership_map_path,
            lifecycle_path=lifecycle_path,
            trace_graph_path=trace_graph_path,
            transition_receipt_paths=transition_receipt_paths,
            anomalies=ownership_map.get("conflicts", []),
        )
        receipt_bundle_path = write_swarm_receipt_bundle(runtime_dir, receipt_bundle)
        receipt_path = write_static_lease_issuance_receipt(
            runtime_dir,
            lease_artifact,
            artifact_path=artifact_path,
            ownership_map=ownership_map,
            ownership_map_path=ownership_map_path,
            lifecycle_path=lifecycle_path,
            trace_graph_path=trace_graph_path,
            receipt_bundle_path=receipt_bundle_path,
            transition_receipt_paths=transition_receipt_paths,
        )
    except Exception:
        if receipt_path and receipt_path.exists():
            receipt_path.unlink()
        if receipt_bundle_path and receipt_bundle_path.exists():
            receipt_bundle_path.unlink()
        if trace_graph_path and trace_graph_path.exists():
            trace_graph_path.unlink()
        for path in transition_receipt_paths:
            if path.exists():
                path.unlink()
        if lifecycle_path and lifecycle_path.exists():
            lifecycle_path.unlink()
        if ownership_map_path and ownership_map_path.exists():
            ownership_map_path.unlink()
        if artifact_path and artifact_path.exists():
            artifact_path.unlink()
        raise
    return (
        lease_artifact,
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
    )


def _validate_ownership_scope(scope: Any, *, label: str) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    if not isinstance(scope, dict):
        return [f"{label} must be a mapping"], {}
    missing = sorted(field for field in REQUIRED_OWNERSHIP_SCOPE_FIELDS if field not in scope)
    if missing:
        errors.append(f"{label} missing required fields: {', '.join(missing)}")
    normalized: dict[str, list[str]] = {}
    for field in sorted(REQUIRED_OWNERSHIP_SCOPE_FIELDS):
        values = _as_unique_string_list(scope.get(field))
        if not values and field in REQUIRED_OWNERSHIP_SCOPE_FIELDS:
            errors.append(f"{label}.{field} must be a non-empty list")
        normalized[field] = values
    return errors, normalized


def _validate_allowed_tool_classes(value: Any, *, label: str) -> tuple[list[str], list[str]]:
    values = _as_unique_string_list(value)
    errors: list[str] = []
    if not values:
        errors.append(f"{label} must be a non-empty list")
        return errors, values
    unknown = sorted(item for item in values if item not in ALLOWED_TOOL_CLASSES)
    if unknown:
        errors.append(f"{label} contains undeclared tool classes: {', '.join(unknown)}")
    return errors, values


def _validate_success_criteria(value: Any, *, label: str) -> tuple[list[str], list[str]]:
    values = _as_unique_string_list(value)
    if not values:
        return [f"{label} must be a non-empty list"], values
    return [], values


def validate_worker_lease(
    lease: dict[str, Any],
    *,
    envelope_scope_swarm: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(lease, dict):
        return False, ["worker_lease must be a mapping"]

    missing = sorted(field for field in REQUIRED_WORKER_LEASE_FIELDS if field not in lease)
    if missing:
        errors.append(f"worker_lease missing required fields: {', '.join(missing)}")
        return False, errors

    if lease.get("schema") != WORKER_LEASE_SCHEMA:
        errors.append(f"worker_lease.schema must equal '{WORKER_LEASE_SCHEMA}'")
    if lease.get("schema_version") != WORKER_LEASE_SCHEMA_VERSION:
        errors.append(f"worker_lease.schema_version must equal '{WORKER_LEASE_SCHEMA_VERSION}'")
    for field in ("swarm_run_id", "work_envelope_id", "lease_id", "worker_id"):
        if not _is_non_empty_string(lease.get(field)):
            errors.append(f"worker_lease.{field} must be a non-empty string")
    if lease.get("lease_state") not in ALLOWED_LEASE_STATES:
        errors.append(
            "worker_lease.lease_state must be one of: "
            + ", ".join(sorted(ALLOWED_LEASE_STATES))
        )

    issued_at = _parse_iso(lease.get("issued_at_utc"))
    expires_at = _parse_iso(lease.get("expires_at_utc"))
    if issued_at is None:
        errors.append("worker_lease.issued_at_utc must be a valid ISO-8601 timestamp")
    if expires_at is None:
        errors.append("worker_lease.expires_at_utc must be a valid ISO-8601 timestamp")
    if issued_at is not None and expires_at is not None and expires_at <= issued_at:
        errors.append("worker_lease.expires_at_utc must be later than issued_at_utc")

    max_runtime_sec = lease.get("max_runtime_sec")
    if not isinstance(max_runtime_sec, int) or max_runtime_sec <= 0:
        errors.append("worker_lease.max_runtime_sec must be a positive integer")
    if lease.get("token_budget") is None:
        errors.append("worker_lease.token_budget must be present")
    if lease.get("compute_budget") is None:
        errors.append("worker_lease.compute_budget must be present")
    if not isinstance(lease.get("approval_context"), dict):
        errors.append("worker_lease.approval_context must be a mapping")
    if not isinstance(lease.get("revocation_reason"), (str, type(None))):
        errors.append("worker_lease.revocation_reason must be a string or null")
    if not isinstance(lease.get("notes"), (str, type(None))):
        errors.append("worker_lease.notes must be a string or null")

    ownership_errors, ownership_scope = _validate_ownership_scope(
        lease.get("ownership_scope"),
        label="worker_lease.ownership_scope",
    )
    errors.extend(ownership_errors)
    tool_errors, allowed_tool_classes = _validate_allowed_tool_classes(
        lease.get("allowed_tool_classes"),
        label="worker_lease.allowed_tool_classes",
    )
    errors.extend(tool_errors)
    network_errors, network_scope = validate_network_scope(
        lease.get("network_scope"),
        label="worker_lease.network_scope",
    )
    errors.extend(network_errors)
    success_errors, _ = _validate_success_criteria(
        lease.get("success_criteria"),
        label="worker_lease.success_criteria",
    )
    errors.extend(success_errors)

    if envelope_scope_swarm is not None and not errors:
        envelope_swarm_run_id = envelope_scope_swarm.get("swarm_run_id")
        if envelope_swarm_run_id and lease.get("swarm_run_id") != envelope_swarm_run_id:
            errors.append("worker_lease.swarm_run_id must match scope.swarm.swarm_run_id")
        file_scope = envelope_scope_swarm.get("file_scope") or {}
        readable = set(_as_unique_string_list(file_scope.get("read_paths"))) | set(
            _as_unique_string_list(file_scope.get("write_paths"))
        )
        writable = set(_as_unique_string_list(file_scope.get("write_paths")))
        lease_read = set(ownership_scope.get("read_paths", []))
        lease_write = set(ownership_scope.get("write_paths", []))
        if lease_read and not lease_read.issubset(readable):
            errors.append("worker_lease.ownership_scope.read_paths exceed envelope scope")
        if lease_write and not lease_write.issubset(writable):
            errors.append("worker_lease.ownership_scope.write_paths exceed envelope scope")

        envelope_tool_scope = set(_as_unique_string_list(envelope_scope_swarm.get("tool_scope")))
        if set(allowed_tool_classes) and not set(allowed_tool_classes).issubset(envelope_tool_scope):
            errors.append("worker_lease.allowed_tool_classes exceed envelope tool_scope")

        envelope_network_errors, envelope_network_scope = validate_network_scope(
            envelope_scope_swarm.get("network_scope"),
            label="scope.swarm.network_scope",
        )
        if envelope_network_errors:
            errors.append("worker_lease cannot be validated against an invalid envelope network_scope")
        else:
            envelope_mode = envelope_network_scope.get("mode")
            envelope_allowlist = set(envelope_network_scope.get("allowlist", []))
            lease_mode = network_scope.get("mode")
            lease_allowlist = set(network_scope.get("allowlist", []))
            if envelope_mode == "deny" and lease_mode != "deny":
                errors.append("worker_lease.network_scope cannot widen envelope deny posture")
            if envelope_mode == "allowlist":
                if lease_mode == "allowlist" and not lease_allowlist.issubset(envelope_allowlist):
                    errors.append("worker_lease.network_scope.allowlist exceeds envelope network_scope")
    return len(errors) == 0, errors
