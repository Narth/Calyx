"""Phase III critique checkpoint construction and deterministic evaluation."""

from __future__ import annotations

from typing import Any


CRITIQUE_PHASE_GRAPH = ["execute", "critique", "validate", "finalize"]
NON_CRITIQUE_PHASE_GRAPH = ["execute", "finalize"]

_DEFAULT_TOOL_SURFACE: dict[str, list[str]] = {
    "code_review": ["fs_read", "repo_grep", "fs_list"],
    "lint_fix": ["fs_read", "fs_write", "repo_grep"],
    "test_run": ["fs_read", "run_test_harness"],
    "doc_update": ["fs_read", "fs_write"],
    "refactor_scope": ["fs_read", "fs_write", "repo_grep", "fs_list"],
    "benchmark_run": ["fs_read", "run_benchmark_harness"],
    "schema_validation": ["fs_read", "validate_schema"],
    "receipt_generation": ["fs_read", "fs_write"],
    "repo_readonly_review": ["fs_read", "repo_grep", "fs_list"],
    "test_run_safe": ["fs_read", "run_test_harness"],
    "patch_small": ["fs_read", "fs_write"],
}


def _dedupe_strings(values: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
    return out


def derive_tool_allowlist(task_type: str, contract: dict[str, Any] | None = None) -> list[str]:
    """Return the known tool allowlist for the task type."""
    if contract:
        surface = (contract.get("tool_surface") or {}).get(task_type) or {}
        tools = surface.get("allowed_tools") or []
        if tools:
            return _dedupe_strings(list(tools))
    return _dedupe_strings(_DEFAULT_TOOL_SURFACE.get(task_type, []))


def build_critique_checkpoint(
    *,
    task_type: str,
    risk_tier: str,
    tool_allowlist: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, Any]:
    """Build a deterministic critique checkpoint declaration."""
    tools = _dedupe_strings(list(tool_allowlist or derive_tool_allowlist(task_type)))
    triggers: list[str] = []
    risk = (risk_tier or "low").strip().lower()
    if risk in ("med", "high"):
        triggers.append(f"risk_tier:{risk}")
    if len(tools) > 1:
        triggers.append("multi_step_workflow")
        triggers.append("cross_tool_execution")
    required = bool(triggers)
    return {
        "required": required,
        "task_type": task_type,
        "risk_tier": risk or "low",
        "triggers": triggers,
        "phase_graph": CRITIQUE_PHASE_GRAPH[:] if required else NON_CRITIQUE_PHASE_GRAPH[:],
        "tool_allowlist": tools,
        "status": "pending" if required else "not_required",
    }


def validate_critique_checkpoint(
    checkpoint: dict[str, Any] | None,
    *,
    task_type: str,
    risk_tier: str,
    tool_allowlist: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate declared checkpoint against deterministic expectations."""
    expected = build_critique_checkpoint(
        task_type=task_type,
        risk_tier=risk_tier,
        tool_allowlist=tool_allowlist,
    )
    current = checkpoint if isinstance(checkpoint, dict) else {}
    errors: list[str] = []
    if expected["required"]:
        if not current:
            errors.append("critique_checkpoint_missing")
        if current.get("required") is not True:
            errors.append("critique_required_flag_missing")
        if current.get("phase_graph") != CRITIQUE_PHASE_GRAPH:
            errors.append("critique_phase_graph_invalid")
        current_triggers = _dedupe_strings(current.get("triggers") or [])
        for trigger in expected["triggers"]:
            if trigger not in current_triggers:
                errors.append(f"critique_trigger_missing:{trigger}")
    return len(errors) == 0, errors, expected


def evaluate_critique_checkpoint(
    *,
    checkpoint: dict[str, Any],
    expected: dict[str, Any],
    execution_success: bool,
    result: dict[str, Any] | Any,
    receipts: list[dict[str, Any]] | Any,
    requires_human_approval: bool,
    approval_token: str | None,
) -> dict[str, Any]:
    """Evaluate the post-execution critique and validation gates."""
    required = bool(expected.get("required"))
    tools = _dedupe_strings(expected.get("tool_allowlist") or [])
    result_dict = result if isinstance(result, dict) else {}
    receipt_list = receipts if isinstance(receipts, list) else []
    critique_checks = [
        {
            "name": "execution_success",
            "passed": bool(execution_success),
            "detail": "handler returned success",
        },
        {
            "name": "result_payload_present",
            "passed": bool(result_dict),
            "detail": "result summary is non-empty",
        },
    ]
    validation_checks = [
        {
            "name": "phase_graph_declared",
            "passed": checkpoint.get("phase_graph") == expected.get("phase_graph"),
            "detail": "phase graph matches execute->critique->validate->finalize",
        },
        {
            "name": "receipts_list_shape",
            "passed": isinstance(receipt_list, list),
            "detail": "handler receipts value is list-shaped",
        },
    ]
    if "cross_tool_execution" in expected.get("triggers", []):
        validation_checks.append(
            {
                "name": "cross_tool_surface_declared",
                "passed": len(tools) > 1,
                "detail": "tool allowlist declares multiple tools",
            }
        )
    if expected.get("risk_tier") == "high":
        critique_checks.append(
            {
                "name": "high_risk_approval_bound",
                "passed": bool(requires_human_approval and approval_token),
                "detail": "high-risk execution retains approval binding",
            }
        )
    critique_passed = all(check["passed"] for check in critique_checks)
    validation_passed = all(check["passed"] for check in validation_checks)
    return {
        "required": required,
        "task_type": expected.get("task_type", ""),
        "risk_tier": expected.get("risk_tier", "low"),
        "triggers": expected.get("triggers", []),
        "phase_graph": checkpoint.get("phase_graph") or expected.get("phase_graph"),
        "tool_allowlist": tools,
        "execution_summary": {
            "success": bool(execution_success),
            "result_keys": sorted(result_dict.keys()),
            "receipt_count": len(receipt_list),
        },
        "critique_checks": critique_checks,
        "validation_checks": validation_checks,
        "critique_status": "passed" if critique_passed else ("not_required" if not required else "failed"),
        "validation_status": "passed" if validation_passed else ("not_required" if not required else "failed"),
        "finalization_allowed": (critique_passed and validation_passed) if required else True,
    }
