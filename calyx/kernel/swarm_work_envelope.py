"""Swarm work-envelope extension validation for governed Phase 0 schema enforcement."""

from __future__ import annotations

from typing import Any


SWARM_ENVELOPE_SCHEMA = "station.swarm.work_envelope.v1"
SWARM_ENVELOPE_SCHEMA_VERSION = "1.0.0"

REQUIRED_SWARM_SCOPE_FIELDS = frozenset(
    {
        "swarm_run_id",
        "task_intent",
        "file_scope",
        "tool_scope",
        "network_scope",
        "success_criteria",
        "worker_plan",
    }
)
REQUIRED_SWARM_CONSTRAINT_FIELDS = frozenset(
    {
        "ownership_policy",
        "overlapping_write_scope_declared",
        "requires_receipt_bundle",
        "requires_trace_graph",
        "reconciliation_required",
    }
)
REQUIRED_FILE_SCOPE_FIELDS = frozenset({"read_paths", "write_paths"})
REQUIRED_OWNERSHIP_SCOPE_FIELDS = frozenset({"read_paths", "write_paths", "deny_paths"})
REQUIRED_WORKER_PLAN_FIELDS = frozenset(
    {
        "worker_id",
        "task_intent",
        "ownership_scope",
        "allowed_tool_classes",
        "network_scope",
        "success_criteria",
    }
)
ALLOWED_OWNERSHIP_POLICIES = frozenset({"exclusive_write_scope"})
ALLOWED_NETWORK_MODES = frozenset({"deny", "allowlist"})
ALLOWED_TOOL_CLASSES = frozenset(
    {
        "read_files",
        "write_files",
        "run_shell",
        "run_tests",
        "inspect_process",
        "vcs_metadata",
        "network_access",
    }
)


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _as_unique_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if not _is_non_empty_string(item):
            continue
        text = item.strip()
        if text not in out:
            out.append(text)
    return out


def _format_path_set(values: list[str]) -> str:
    return ", ".join(sorted(values))


def _validate_path_scope(
    scope: Any,
    *,
    required_fields: frozenset[str],
    label: str,
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    if not isinstance(scope, dict):
        return [f"{label} must be a mapping"], {}
    missing = sorted(field for field in required_fields if field not in scope)
    if missing:
        errors.append(f"{label} missing required fields: {', '.join(missing)}")
    normalized: dict[str, list[str]] = {}
    for field in sorted(required_fields | {"deny_paths"}):
        if field not in scope:
            if field == "deny_paths":
                normalized[field] = []
            continue
        values = _as_unique_string_list(scope.get(field))
        if not values and field in required_fields:
            errors.append(f"{label}.{field} must be a non-empty list of paths")
        normalized[field] = values
    return errors, normalized


def validate_network_scope(network_scope: Any, *, label: str) -> tuple[list[str], dict[str, Any]]:
    if not isinstance(network_scope, dict):
        return [f"{label} must be a mapping"], {}
    errors: list[str] = []
    mode = network_scope.get("mode")
    allowlist = _as_unique_string_list(network_scope.get("allowlist", []))
    if mode not in ALLOWED_NETWORK_MODES:
        errors.append(f"{label}.mode must be one of: {', '.join(sorted(ALLOWED_NETWORK_MODES))}")
    if mode == "deny" and allowlist:
        errors.append(f"{label}.allowlist must be empty when mode=deny")
    if mode == "allowlist" and not allowlist:
        errors.append(f"{label}.allowlist must be non-empty when mode=allowlist")
    return errors, {"mode": mode, "allowlist": allowlist}


def _validate_tool_scope(tool_scope: Any, *, label: str) -> tuple[list[str], list[str]]:
    values = _as_unique_string_list(tool_scope)
    errors: list[str] = []
    if not values:
        errors.append(f"{label} must be a non-empty list of allowed tool classes")
        return errors, values
    unknown = sorted(value for value in values if value not in ALLOWED_TOOL_CLASSES)
    if unknown:
        errors.append(f"{label} contains undeclared tool classes: {', '.join(unknown)}")
    return errors, values


def _validate_success_criteria(value: Any, *, label: str) -> tuple[list[str], list[str]]:
    values = _as_unique_string_list(value)
    if not values:
        return [f"{label} must be a non-empty list"], values
    return [], values


def _validate_worker_plan(
    worker_plan: Any,
    *,
    root_file_scope: dict[str, list[str]],
    root_tool_scope: list[str],
    root_network_scope: dict[str, Any],
    overlapping_write_scope_declared: bool,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(worker_plan, list) or not worker_plan:
        return ["scope.swarm.worker_plan must be a non-empty list"]

    seen_worker_ids: set[str] = set()
    write_owner: dict[str, str] = {}
    root_readable = set(root_file_scope.get("read_paths", [])) | set(root_file_scope.get("write_paths", []))
    root_writable = set(root_file_scope.get("write_paths", []))
    root_tool_scope_set = set(root_tool_scope)
    root_network_mode = root_network_scope.get("mode")
    root_network_allowlist = set(root_network_scope.get("allowlist", []))

    for index, entry in enumerate(worker_plan):
        label = f"scope.swarm.worker_plan[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be a mapping")
            continue
        missing = sorted(field for field in REQUIRED_WORKER_PLAN_FIELDS if field not in entry)
        if missing:
            errors.append(f"{label} missing required fields: {', '.join(missing)}")
            continue
        worker_id = entry.get("worker_id")
        if not _is_non_empty_string(worker_id):
            errors.append(f"{label}.worker_id must be a non-empty string")
        else:
            normalized_worker_id = worker_id.strip()
            if normalized_worker_id in seen_worker_ids:
                errors.append(f"{label}.worker_id duplicates existing worker_id '{normalized_worker_id}'")
            seen_worker_ids.add(normalized_worker_id)
        if not _is_non_empty_string(entry.get("task_intent")):
            errors.append(f"{label}.task_intent must be a non-empty string")

        ownership_errors, ownership_scope = _validate_path_scope(
            entry.get("ownership_scope"),
            required_fields=REQUIRED_OWNERSHIP_SCOPE_FIELDS,
            label=f"{label}.ownership_scope",
        )
        errors.extend(ownership_errors)
        read_paths = set(ownership_scope.get("read_paths", []))
        write_paths = set(ownership_scope.get("write_paths", []))
        if read_paths and not read_paths.issubset(root_readable):
            errors.append(
                f"{label}.ownership_scope.read_paths exceed envelope file_scope: "
                f"{_format_path_set(sorted(read_paths - root_readable))}"
            )
        if write_paths and not write_paths.issubset(root_writable):
            errors.append(
                f"{label}.ownership_scope.write_paths exceed envelope file_scope: "
                f"{_format_path_set(sorted(write_paths - root_writable))}"
            )
        if not overlapping_write_scope_declared:
            for path in sorted(write_paths):
                prior_owner = write_owner.get(path)
                if prior_owner and prior_owner != worker_id:
                    errors.append(
                        f"{label}.ownership_scope.write_paths overlaps with worker '{prior_owner}' on path '{path}'"
                    )
                else:
                    write_owner[path] = worker_id

        tool_errors, allowed_tool_classes = _validate_tool_scope(
            entry.get("allowed_tool_classes"),
            label=f"{label}.allowed_tool_classes",
        )
        errors.extend(tool_errors)
        tool_set = set(allowed_tool_classes)
        if tool_set and not tool_set.issubset(root_tool_scope_set):
            errors.append(
                f"{label}.allowed_tool_classes exceed envelope tool_scope: "
                f"{', '.join(sorted(tool_set - root_tool_scope_set))}"
            )

        network_errors, worker_network_scope = validate_network_scope(
            entry.get("network_scope"),
            label=f"{label}.network_scope",
        )
        errors.extend(network_errors)
        worker_mode = worker_network_scope.get("mode")
        worker_allowlist = set(worker_network_scope.get("allowlist", []))
        if root_network_mode == "deny" and worker_mode != "deny":
            errors.append(f"{label}.network_scope cannot widen root deny posture")
        if root_network_mode == "allowlist":
            if worker_mode == "deny":
                pass
            elif not worker_allowlist.issubset(root_network_allowlist):
                errors.append(
                    f"{label}.network_scope.allowlist exceeds envelope network_scope: "
                    f"{', '.join(sorted(worker_allowlist - root_network_allowlist))}"
                )

        success_errors, _ = _validate_success_criteria(
            entry.get("success_criteria"),
            label=f"{label}.success_criteria",
        )
        errors.extend(success_errors)
    return errors


def validate_swarm_extensions(scope: dict[str, Any], constraints: dict[str, Any]) -> tuple[bool, list[str]]:
    scope_swarm = (scope or {}).get("swarm")
    constraints_swarm = (constraints or {}).get("swarm")
    if scope_swarm is None and constraints_swarm is None:
        return True, []

    errors: list[str] = []
    if scope_swarm is None or constraints_swarm is None:
        return False, ["scope.swarm and constraints.swarm must either both be present or both be absent"]
    if not isinstance(scope_swarm, dict):
        errors.append("scope.swarm must be a mapping")
        return False, errors
    if not isinstance(constraints_swarm, dict):
        errors.append("constraints.swarm must be a mapping")
        return False, errors

    missing_scope = sorted(field for field in REQUIRED_SWARM_SCOPE_FIELDS if field not in scope_swarm)
    if missing_scope:
        errors.append(f"scope.swarm missing required fields: {', '.join(missing_scope)}")
    missing_constraints = sorted(field for field in REQUIRED_SWARM_CONSTRAINT_FIELDS if field not in constraints_swarm)
    if missing_constraints:
        errors.append(f"constraints.swarm missing required fields: {', '.join(missing_constraints)}")

    if not _is_non_empty_string(scope_swarm.get("swarm_run_id")):
        errors.append("scope.swarm.swarm_run_id must be a non-empty string")
    if not _is_non_empty_string(scope_swarm.get("task_intent")):
        errors.append("scope.swarm.task_intent must be a non-empty string")

    file_scope_errors, file_scope = _validate_path_scope(
        scope_swarm.get("file_scope"),
        required_fields=REQUIRED_FILE_SCOPE_FIELDS,
        label="scope.swarm.file_scope",
    )
    errors.extend(file_scope_errors)
    tool_errors, root_tool_scope = _validate_tool_scope(scope_swarm.get("tool_scope"), label="scope.swarm.tool_scope")
    errors.extend(tool_errors)
    network_errors, root_network_scope = validate_network_scope(
        scope_swarm.get("network_scope"),
        label="scope.swarm.network_scope",
    )
    errors.extend(network_errors)
    success_errors, _ = _validate_success_criteria(
        scope_swarm.get("success_criteria"),
        label="scope.swarm.success_criteria",
    )
    errors.extend(success_errors)

    ownership_policy = constraints_swarm.get("ownership_policy")
    if ownership_policy not in ALLOWED_OWNERSHIP_POLICIES:
        errors.append(
            "constraints.swarm.ownership_policy must be one of: "
            + ", ".join(sorted(ALLOWED_OWNERSHIP_POLICIES))
        )
    overlap_declared = constraints_swarm.get("overlapping_write_scope_declared")
    for field in (
        "overlapping_write_scope_declared",
        "requires_receipt_bundle",
        "requires_trace_graph",
        "reconciliation_required",
    ):
        if not isinstance(constraints_swarm.get(field), bool):
            errors.append(f"constraints.swarm.{field} must be a boolean")

    if not errors:
        errors.extend(
            _validate_worker_plan(
                scope_swarm.get("worker_plan"),
                root_file_scope=file_scope,
                root_tool_scope=root_tool_scope,
                root_network_scope=root_network_scope,
                overlapping_write_scope_declared=bool(overlap_declared),
            )
        )
    return len(errors) == 0, errors
