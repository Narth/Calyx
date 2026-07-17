"""Sandbox schema, read-only preparation, and lifecycle validation for governed swarm containment."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .swarm_lease import validate_worker_lease
from .swarm_trace import get_swarm_run_dir
from .swarm_work_envelope import validate_network_scope


SWARM_SANDBOX_MANIFEST_SCHEMA = "station.swarm.sandbox_manifest.v1"
SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION = "1.0.0"
SWARM_SNAPSHOT_RECORD_SCHEMA = "station.swarm.snapshot_record.v1"
SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION = "1.0.0"
SWARM_POST_EXECUTION_DIFF_SCHEMA = "station.swarm.post_execution_diff.v1"
SWARM_POST_EXECUTION_DIFF_SCHEMA_VERSION = "1.0.0"
SWARM_CONTAINMENT_FAILURE_SCHEMA = "station.swarm.containment_failure.v1"
SWARM_CONTAINMENT_FAILURE_SCHEMA_VERSION = "1.0.0"

ALLOWED_SANDBOX_ISOLATION_MODES = frozenset(
    {"git_worktree", "branch_overlay", "directory_overlay", "read_only_probe"}
)
ALLOWED_SANDBOX_STATES = frozenset({"prepared", "active", "sealed", "quarantined", "released"})
ALLOWED_SANDBOX_TRANSITIONS: dict[str, frozenset[str]] = {
    "prepared": frozenset({"active"}),
    "active": frozenset({"sealed", "quarantined"}),
    "sealed": frozenset({"released"}),
    "quarantined": frozenset({"released"}),
    "released": frozenset(),
}
ALLOWED_SNAPSHOT_STAGES = frozenset({"pre_execution", "post_execution"})
ALLOWED_CONTAINMENT_FAILURE_CLASSES = frozenset(
    {
        "ownership_violation",
        "sandbox_escape_attempt",
        "network_scope_violation",
        "orphan_worker_detected",
        "stale_lock_detected",
        "snapshot_missing",
        "rollback_unavailable",
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
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_segment(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in value)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _scope_patterns_from_manifest(manifest: dict[str, Any]) -> list[str]:
    patterns = _as_unique_string_list(manifest.get("read_paths"))
    for item in _as_unique_string_list(manifest.get("write_paths")):
        if item not in patterns:
            patterns.append(item)
    return patterns


def _match_declared_paths(repo_root: Path, patterns: list[str], deny_patterns: list[str]) -> list[Path]:
    matched: list[Path] = []
    deny_set = set(deny_patterns)
    for pattern in patterns:
        try:
            candidates = list(repo_root.glob(pattern))
        except (OSError, ValueError):
            continue
        for candidate in candidates:
            if not candidate.is_file():
                continue
            rel_path = candidate.relative_to(repo_root).as_posix()
            if any(Path(rel_path).match(deny) for deny in deny_set):
                continue
            if candidate not in matched:
                matched.append(candidate)
    matched.sort(key=lambda item: item.as_posix().lower())
    return matched


def _build_inventory_payload(
    *,
    repo_root: Path,
    manifest: dict[str, Any],
    captured_at_utc: str,
) -> tuple[dict[str, Any], str]:
    scope_patterns = _scope_patterns_from_manifest(manifest)
    deny_patterns = _as_unique_string_list(manifest.get("deny_paths"))
    matched_files = _match_declared_paths(repo_root, scope_patterns, deny_patterns)
    entries: list[dict[str, Any]] = []
    for path in matched_files:
        stat = path.stat()
        entries.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "size_bytes": stat.st_size,
                "mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )
    hash_payload = {
        "scope_patterns": scope_patterns,
        "deny_patterns": deny_patterns,
        "entries": entries,
    }
    scope_hash = "sha256:" + hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    inventory = {
        "schema": "station.swarm.snapshot_inventory.v1",
        "schema_version": "1.0.0",
        "snapshot_id": manifest["pre_execution_snapshot_id"],
        "swarm_run_id": manifest["swarm_run_id"],
        "lease_id": manifest["lease_id"],
        "worker_id": manifest["worker_id"],
        "captured_at_utc": captured_at_utc,
        "scope_patterns": scope_patterns,
        "deny_patterns": deny_patterns,
        "files": entries,
        "summary": {
            "declared_pattern_count": len(scope_patterns),
            "matched_file_count": len(entries),
        },
        "scope_hash": scope_hash,
    }
    return inventory, scope_hash


def get_sandbox_manifest_path(runtime_dir: Path, swarm_run_id: str, sandbox_id: str) -> Path:
    return (
        get_swarm_run_dir(runtime_dir, swarm_run_id)
        / "sandboxes"
        / _safe_segment(sandbox_id)
        / "manifest.json"
    )


def get_snapshot_record_path(runtime_dir: Path, swarm_run_id: str, snapshot_id: str) -> Path:
    return get_swarm_run_dir(runtime_dir, swarm_run_id) / "snapshots" / f"{_safe_segment(snapshot_id)}.json"


def get_snapshot_inventory_path(runtime_dir: Path, swarm_run_id: str, snapshot_id: str) -> Path:
    return (
        get_swarm_run_dir(runtime_dir, swarm_run_id)
        / "snapshots"
        / f"{_safe_segment(snapshot_id)}__inventory.json"
    )


def build_read_only_probe_sandbox_manifest(
    worker_lease: dict[str, Any],
    *,
    runtime_dir: Path,
) -> dict[str, Any]:
    lease_valid, lease_errors = validate_worker_lease(worker_lease)
    if not lease_valid:
        raise ValueError("invalid_worker_lease_for_sandbox_prepare: " + "; ".join(lease_errors))

    scope = worker_lease.get("ownership_scope") or {}
    sandbox_id = f"sandbox::{worker_lease['lease_id']}"
    snapshot_id = f"snapshot::{worker_lease['lease_id']}::pre"
    sandbox_root = get_sandbox_manifest_path(
        runtime_dir,
        worker_lease["swarm_run_id"],
        sandbox_id,
    ).parent
    read_paths = _as_unique_string_list(scope.get("read_paths"))
    for item in _as_unique_string_list(scope.get("write_paths")):
        if item not in read_paths:
            read_paths.append(item)

    manifest = {
        "schema": SWARM_SANDBOX_MANIFEST_SCHEMA,
        "schema_version": SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION,
        "sandbox_id": sandbox_id,
        "swarm_run_id": worker_lease["swarm_run_id"],
        "work_envelope_id": worker_lease["work_envelope_id"],
        "lease_id": worker_lease["lease_id"],
        "worker_id": worker_lease["worker_id"],
        "isolation_mode": "read_only_probe",
        "sandbox_root": str(sandbox_root),
        "read_paths": read_paths,
        "write_paths": _as_unique_string_list(scope.get("write_paths")),
        "deny_paths": _as_unique_string_list(scope.get("deny_paths")),
        "allowed_tool_classes": _as_unique_string_list(worker_lease.get("allowed_tool_classes")),
        "network_scope": worker_lease.get("network_scope"),
        "pre_execution_snapshot_id": snapshot_id,
        "post_execution_diff_id": None,
        "sandbox_state": "prepared",
        "notes": "Read-only probe sandbox prepared without execution enforcement",
    }
    valid, errors = validate_sandbox_manifest(manifest, worker_lease=worker_lease)
    if not valid:
        raise ValueError("invalid_sandbox_manifest_from_worker_lease: " + "; ".join(errors))
    return manifest


def build_pre_execution_snapshot_record(
    sandbox_manifest: dict[str, Any],
    *,
    repo_root: Path,
    runtime_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_valid, manifest_errors = validate_sandbox_manifest(sandbox_manifest)
    if not manifest_valid:
        raise ValueError("invalid_sandbox_manifest_for_snapshot: " + "; ".join(manifest_errors))

    captured_at_utc = _utc_now_iso()
    inventory_payload, scope_hash = _build_inventory_payload(
        repo_root=repo_root,
        manifest=sandbox_manifest,
        captured_at_utc=captured_at_utc,
    )
    inventory_path = get_snapshot_inventory_path(
        runtime_dir,
        sandbox_manifest["swarm_run_id"],
        sandbox_manifest["pre_execution_snapshot_id"],
    )
    record = {
        "schema": SWARM_SNAPSHOT_RECORD_SCHEMA,
        "schema_version": SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION,
        "snapshot_id": sandbox_manifest["pre_execution_snapshot_id"],
        "swarm_run_id": sandbox_manifest["swarm_run_id"],
        "lease_id": sandbox_manifest["lease_id"],
        "worker_id": sandbox_manifest["worker_id"],
        "snapshot_stage": "pre_execution",
        "snapshot_method": "read_only_scope_inventory_v1",
        "captured_at_utc": captured_at_utc,
        "scope_hash": scope_hash,
        "artifact_paths": [str(inventory_path)],
        "rollback_method": "declared_unavailable_phase1",
        "notes": "Read-only pre-execution scope inventory for staged sandbox preparation",
    }
    valid, errors = validate_snapshot_record(record, sandbox_manifest=sandbox_manifest)
    if not valid:
        raise ValueError("invalid_snapshot_record: " + "; ".join(errors))
    return record, inventory_payload


def materialize_prepared_sandbox(
    *,
    runtime_dir: Path,
    repo_root: Path,
    sandbox_manifest: dict[str, Any],
    worker_lease: dict[str, Any],
) -> tuple[dict[str, Any], Path, dict[str, Any], Path]:
    if worker_lease is None:
        raise ValueError("sandbox_prepare requires a valid worker_lease")
    manifest_valid, manifest_errors = validate_sandbox_manifest(
        sandbox_manifest,
        worker_lease=worker_lease,
    )
    if not manifest_valid:
        raise ValueError("invalid_sandbox_identity_binding: " + "; ".join(manifest_errors))

    manifest_path = get_sandbox_manifest_path(
        runtime_dir,
        sandbox_manifest["swarm_run_id"],
        sandbox_manifest["sandbox_id"],
    )
    snapshot_record, inventory_payload = build_pre_execution_snapshot_record(
        sandbox_manifest,
        repo_root=repo_root,
        runtime_dir=runtime_dir,
    )
    snapshot_path = get_snapshot_record_path(
        runtime_dir,
        sandbox_manifest["swarm_run_id"],
        snapshot_record["snapshot_id"],
    )
    inventory_path = Path(snapshot_record["artifact_paths"][0])
    _write_json_atomic(manifest_path, sandbox_manifest)
    _write_json_atomic(inventory_path, inventory_payload)
    _write_json_atomic(snapshot_path, snapshot_record)
    return sandbox_manifest, manifest_path, snapshot_record, snapshot_path


def prepare_read_only_probe_sandbox(
    worker_lease: dict[str, Any] | None,
    *,
    runtime_dir: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], Path, dict[str, Any], Path]:
    if worker_lease is None:
        raise ValueError("sandbox_prepare requires a valid worker_lease")
    manifest = build_read_only_probe_sandbox_manifest(worker_lease, runtime_dir=runtime_dir)
    return materialize_prepared_sandbox(
        runtime_dir=runtime_dir,
        repo_root=repo_root,
        sandbox_manifest=manifest,
        worker_lease=worker_lease,
    )


def prepare_read_only_probe_sandboxes(
    lease_artifact: dict[str, Any],
    *,
    runtime_dir: Path,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[Path], list[dict[str, Any]], list[Path]]:
    manifests: list[dict[str, Any]] = []
    manifest_paths: list[Path] = []
    snapshots: list[dict[str, Any]] = []
    snapshot_paths: list[Path] = []
    leases = lease_artifact.get("leases", []) if isinstance(lease_artifact, dict) else []
    for worker_lease in leases:
        manifest, manifest_path, snapshot, snapshot_path = prepare_read_only_probe_sandbox(
            worker_lease,
            runtime_dir=runtime_dir,
            repo_root=repo_root,
        )
        manifests.append(manifest)
        manifest_paths.append(manifest_path)
        snapshots.append(snapshot)
        snapshot_paths.append(snapshot_path)
    return manifests, manifest_paths, snapshots, snapshot_paths


def validate_sandbox_state_transition(previous_state: str, new_state: str) -> tuple[bool, list[str]]:
    if previous_state not in ALLOWED_SANDBOX_STATES:
        return False, [
            "previous sandbox_state must be one of: " + ", ".join(sorted(ALLOWED_SANDBOX_STATES))
        ]
    if new_state not in ALLOWED_SANDBOX_STATES:
        return False, [
            "new sandbox_state must be one of: " + ", ".join(sorted(ALLOWED_SANDBOX_STATES))
        ]
    if new_state not in ALLOWED_SANDBOX_TRANSITIONS.get(previous_state, frozenset()):
        return False, [f"invalid_sandbox_transition:{previous_state}->{new_state}"]
    return True, []


def validate_sandbox_manifest(
    manifest: dict[str, Any],
    *,
    worker_lease: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return False, ["sandbox_manifest must be a mapping"]

    required = (
        "schema",
        "schema_version",
        "sandbox_id",
        "swarm_run_id",
        "work_envelope_id",
        "lease_id",
        "worker_id",
        "isolation_mode",
        "sandbox_root",
        "read_paths",
        "write_paths",
        "deny_paths",
        "allowed_tool_classes",
        "network_scope",
        "pre_execution_snapshot_id",
        "post_execution_diff_id",
        "sandbox_state",
    )
    missing = [field for field in required if field not in manifest]
    if missing:
        return False, [f"sandbox_manifest missing required fields: {', '.join(missing)}"]

    if manifest.get("schema") != SWARM_SANDBOX_MANIFEST_SCHEMA:
        errors.append(f"sandbox_manifest.schema must equal '{SWARM_SANDBOX_MANIFEST_SCHEMA}'")
    if manifest.get("schema_version") != SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"sandbox_manifest.schema_version must equal '{SWARM_SANDBOX_MANIFEST_SCHEMA_VERSION}'"
        )
    for field in ("sandbox_id", "swarm_run_id", "work_envelope_id", "lease_id", "worker_id", "sandbox_root"):
        if not _is_non_empty_string(manifest.get(field)):
            errors.append(f"sandbox_manifest.{field} must be a non-empty string")

    if manifest.get("isolation_mode") not in ALLOWED_SANDBOX_ISOLATION_MODES:
        errors.append(
            "sandbox_manifest.isolation_mode must be one of: "
            + ", ".join(sorted(ALLOWED_SANDBOX_ISOLATION_MODES))
        )
    if manifest.get("sandbox_state") not in ALLOWED_SANDBOX_STATES:
        errors.append(
            "sandbox_manifest.sandbox_state must be one of: "
            + ", ".join(sorted(ALLOWED_SANDBOX_STATES))
        )

    for field in ("read_paths", "write_paths", "deny_paths", "allowed_tool_classes"):
        values = _as_unique_string_list(manifest.get(field))
        if not values:
            errors.append(f"sandbox_manifest.{field} must be a non-empty list")

    network_errors, network_scope = validate_network_scope(
        manifest.get("network_scope"),
        label="sandbox_manifest.network_scope",
    )
    errors.extend(network_errors)

    if not isinstance(manifest.get("pre_execution_snapshot_id"), (str, type(None))):
        errors.append("sandbox_manifest.pre_execution_snapshot_id must be a string or null")
    if not isinstance(manifest.get("post_execution_diff_id"), (str, type(None))):
        errors.append("sandbox_manifest.post_execution_diff_id must be a string or null")
    if not isinstance(manifest.get("notes"), (str, type(None))):
        errors.append("sandbox_manifest.notes must be a string or null")

    if worker_lease is not None:
        lease_valid, lease_errors = validate_worker_lease(worker_lease)
        if not lease_valid:
            errors.append("sandbox_manifest cannot align against invalid worker_lease: " + "; ".join(lease_errors))
        else:
            for field in ("swarm_run_id", "work_envelope_id", "lease_id", "worker_id"):
                if manifest.get(field) != worker_lease.get(field):
                    errors.append(f"sandbox_manifest.{field} must match worker_lease.{field}")
            lease_scope = worker_lease.get("ownership_scope") or {}
            lease_read = set(_as_unique_string_list(lease_scope.get("read_paths")))
            lease_write = set(_as_unique_string_list(lease_scope.get("write_paths")))
            lease_deny = set(_as_unique_string_list(lease_scope.get("deny_paths")))
            manifest_read = set(_as_unique_string_list(manifest.get("read_paths")))
            manifest_write = set(_as_unique_string_list(manifest.get("write_paths")))
            manifest_deny = set(_as_unique_string_list(manifest.get("deny_paths")))
            if not manifest_read.issubset(lease_read | lease_write):
                errors.append("sandbox_manifest.read_paths exceed worker_lease ownership scope")
            if not manifest_write.issubset(lease_write):
                errors.append("sandbox_manifest.write_paths exceed worker_lease write scope")
            if not manifest_deny.issuperset(lease_deny):
                errors.append("sandbox_manifest.deny_paths must include all worker_lease deny_paths")

            lease_tools = set(_as_unique_string_list(worker_lease.get("allowed_tool_classes")))
            manifest_tools = set(_as_unique_string_list(manifest.get("allowed_tool_classes")))
            if not manifest_tools.issubset(lease_tools):
                errors.append("sandbox_manifest.allowed_tool_classes exceed worker_lease allowed_tool_classes")

            lease_network_errors, lease_network_scope = validate_network_scope(
                worker_lease.get("network_scope"),
                label="worker_lease.network_scope",
            )
            if lease_network_errors:
                errors.append("sandbox_manifest cannot align against invalid worker_lease network_scope")
            else:
                lease_mode = lease_network_scope.get("mode")
                lease_allowlist = set(lease_network_scope.get("allowlist", []))
                manifest_mode = network_scope.get("mode")
                manifest_allowlist = set(network_scope.get("allowlist", []))
                if lease_mode == "deny" and manifest_mode != "deny":
                    errors.append("sandbox_manifest.network_scope cannot widen worker_lease deny posture")
                if lease_mode == "allowlist" and manifest_mode == "allowlist":
                    if not manifest_allowlist.issubset(lease_allowlist):
                        errors.append(
                            "sandbox_manifest.network_scope.allowlist exceeds worker_lease network_scope"
                        )
    return len(errors) == 0, errors


def validate_snapshot_record(
    record: dict[str, Any],
    *,
    sandbox_manifest: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return False, ["snapshot_record must be a mapping"]
    required = (
        "schema",
        "schema_version",
        "snapshot_id",
        "swarm_run_id",
        "lease_id",
        "worker_id",
        "snapshot_stage",
        "snapshot_method",
        "captured_at_utc",
        "scope_hash",
        "artifact_paths",
        "rollback_method",
    )
    missing = [field for field in required if field not in record]
    if missing:
        return False, [f"snapshot_record missing required fields: {', '.join(missing)}"]

    if record.get("schema") != SWARM_SNAPSHOT_RECORD_SCHEMA:
        errors.append(f"snapshot_record.schema must equal '{SWARM_SNAPSHOT_RECORD_SCHEMA}'")
    if record.get("schema_version") != SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION:
        errors.append(
            f"snapshot_record.schema_version must equal '{SWARM_SNAPSHOT_RECORD_SCHEMA_VERSION}'"
        )
    for field in ("snapshot_id", "swarm_run_id", "lease_id", "worker_id", "snapshot_method", "scope_hash", "rollback_method"):
        if not _is_non_empty_string(record.get(field)):
            errors.append(f"snapshot_record.{field} must be a non-empty string")
    if record.get("snapshot_stage") not in ALLOWED_SNAPSHOT_STAGES:
        errors.append(
            "snapshot_record.snapshot_stage must be one of: "
            + ", ".join(sorted(ALLOWED_SNAPSHOT_STAGES))
        )
    if _parse_iso(record.get("captured_at_utc")) is None:
        errors.append("snapshot_record.captured_at_utc must be a valid ISO-8601 timestamp")
    artifact_paths = _as_unique_string_list(record.get("artifact_paths"))
    if not artifact_paths:
        errors.append("snapshot_record.artifact_paths must be a non-empty list")
    if not isinstance(record.get("notes"), (str, type(None))):
        errors.append("snapshot_record.notes must be a string or null")

    if sandbox_manifest is not None:
        manifest_valid, manifest_errors = validate_sandbox_manifest(sandbox_manifest)
        if not manifest_valid:
            errors.append(
                "snapshot_record cannot align against invalid sandbox_manifest: " + "; ".join(manifest_errors)
            )
        else:
            for field in ("swarm_run_id", "lease_id", "worker_id"):
                if record.get(field) != sandbox_manifest.get(field):
                    errors.append(f"snapshot_record.{field} must match sandbox_manifest.{field}")
    return len(errors) == 0, errors


def validate_post_execution_diff(
    diff: dict[str, Any],
    *,
    sandbox_manifest: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(diff, dict):
        return False, ["post_execution_diff must be a mapping"]
    required = (
        "schema",
        "schema_version",
        "diff_id",
        "swarm_run_id",
        "lease_id",
        "worker_id",
        "changed_paths",
        "added_paths",
        "deleted_paths",
        "ownership_violations",
        "generated_artifacts",
        "diff_summary",
    )
    missing = [field for field in required if field not in diff]
    if missing:
        return False, [f"post_execution_diff missing required fields: {', '.join(missing)}"]

    if diff.get("schema") != SWARM_POST_EXECUTION_DIFF_SCHEMA:
        errors.append(f"post_execution_diff.schema must equal '{SWARM_POST_EXECUTION_DIFF_SCHEMA}'")
    if diff.get("schema_version") != SWARM_POST_EXECUTION_DIFF_SCHEMA_VERSION:
        errors.append(
            f"post_execution_diff.schema_version must equal '{SWARM_POST_EXECUTION_DIFF_SCHEMA_VERSION}'"
        )
    for field in ("diff_id", "swarm_run_id", "lease_id", "worker_id"):
        if not _is_non_empty_string(diff.get(field)):
            errors.append(f"post_execution_diff.{field} must be a non-empty string")
    for field in ("changed_paths", "added_paths", "deleted_paths", "generated_artifacts"):
        if not isinstance(diff.get(field), list):
            errors.append(f"post_execution_diff.{field} must be a list")
    if not isinstance(diff.get("ownership_violations"), list):
        errors.append("post_execution_diff.ownership_violations must be a list")
    if not isinstance(diff.get("diff_summary"), dict):
        errors.append("post_execution_diff.diff_summary must be a mapping")

    if sandbox_manifest is not None:
        manifest_valid, manifest_errors = validate_sandbox_manifest(sandbox_manifest)
        if not manifest_valid:
            errors.append(
                "post_execution_diff cannot align against invalid sandbox_manifest: "
                + "; ".join(manifest_errors)
            )
        else:
            for field in ("swarm_run_id", "lease_id", "worker_id"):
                if diff.get(field) != sandbox_manifest.get(field):
                    errors.append(f"post_execution_diff.{field} must match sandbox_manifest.{field}")
            allowed_write_paths = set(_as_unique_string_list(sandbox_manifest.get("write_paths")))
            for path in _as_unique_string_list(diff.get("changed_paths")):
                if path not in allowed_write_paths:
                    errors.append(
                        f"post_execution_diff.changed_paths contains '{path}' outside sandbox_manifest.write_paths"
                    )
    return len(errors) == 0, errors


def validate_containment_failure_record(
    record: dict[str, Any],
    *,
    sandbox_manifest: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return False, ["containment_failure_record must be a mapping"]
    required = (
        "schema",
        "schema_version",
        "failure_class",
        "swarm_run_id",
        "lease_id",
        "worker_id",
        "sandbox_id",
        "detected_at_utc",
        "detail",
        "artifact_refs",
    )
    missing = [field for field in required if field not in record]
    if missing:
        return False, [f"containment_failure_record missing required fields: {', '.join(missing)}"]

    if record.get("schema") != SWARM_CONTAINMENT_FAILURE_SCHEMA:
        errors.append(f"containment_failure_record.schema must equal '{SWARM_CONTAINMENT_FAILURE_SCHEMA}'")
    if record.get("schema_version") != SWARM_CONTAINMENT_FAILURE_SCHEMA_VERSION:
        errors.append(
            f"containment_failure_record.schema_version must equal '{SWARM_CONTAINMENT_FAILURE_SCHEMA_VERSION}'"
        )
    if record.get("failure_class") not in ALLOWED_CONTAINMENT_FAILURE_CLASSES:
        errors.append(
            "containment_failure_record.failure_class must be one of: "
            + ", ".join(sorted(ALLOWED_CONTAINMENT_FAILURE_CLASSES))
        )
    for field in ("swarm_run_id", "lease_id", "worker_id", "sandbox_id", "detail"):
        if not _is_non_empty_string(record.get(field)):
            errors.append(f"containment_failure_record.{field} must be a non-empty string")
    if _parse_iso(record.get("detected_at_utc")) is None:
        errors.append("containment_failure_record.detected_at_utc must be a valid ISO-8601 timestamp")
    if not isinstance(record.get("artifact_refs"), list):
        errors.append("containment_failure_record.artifact_refs must be a list")

    if sandbox_manifest is not None:
        manifest_valid, manifest_errors = validate_sandbox_manifest(sandbox_manifest)
        if not manifest_valid:
            errors.append(
                "containment_failure_record cannot align against invalid sandbox_manifest: "
                + "; ".join(manifest_errors)
            )
        else:
            for field in ("swarm_run_id", "lease_id", "worker_id", "sandbox_id"):
                if record.get(field) != sandbox_manifest.get(field):
                    errors.append(f"containment_failure_record.{field} must match sandbox_manifest.{field}")
    return len(errors) == 0, errors
