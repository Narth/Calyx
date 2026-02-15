"""
Stabilization engine for autonomous execution.
Phase 2B: Produces modified actions for allow_modified policy decisions.
Deterministic, rule-based. Every modification logged before execution.
"""
from __future__ import annotations

from pathlib import Path

from .policy_eval import DEFAULT_WRITE_CONTENT_MAX


def _normalize_path_to_sandbox_rel(path_str: str) -> str:
    """Normalize path to sandbox-relative form (forward slashes, no leading /)."""
    if not path_str or not isinstance(path_str, str):
        return ""
    p = path_str.strip().replace("\\", "/").lstrip("/")
    while "//" in p:
        p = p.replace("//", "/")
    return p or "."


def stabilize_action(
    action: dict,
    policy_result: dict,
    sandbox_root: Path,
    *,
    write_content_max: int = DEFAULT_WRITE_CONTENT_MAX,
) -> tuple[str, dict | None, str, str]:
    """
    Stabilize an action that received allow_modified.
    Returns: (decision_type, modified_action, stabilization_mechanism, stabilization_reason)

    - block: modified_action is None, no execution
    - allow_modified: modified_action is non-None, execute modified_action
    """
    sandbox_root = Path(sandbox_root).resolve()
    action_id = action.get("action_id", "")
    tool_name = action.get("tool_name", "")
    args = action.get("arguments") or {}
    policy_reason = policy_result.get("policy_reason", "")

    # Unsafe: must remain block
    if policy_result.get("decision_type") == "block":
        return ("block", None, "full_block", policy_reason)

    # allow_modified cases
    if "delete_file_overly_broad_path" in policy_reason:
        # A) Scope reduction: replace with write to trash/<action_id>.noop
        # Creates explainable sandbox change without deleting anything
        modified = {
            "action_id": action_id,
            "tool_name": "write_file",
            "arguments": {
                "path": f"trash/{action_id}.noop",
                "content": f"stabilization: delete_file_overly_broad_path; original path={args.get('path', '')}; scope_reduction to no-op marker",
            },
            "order": action.get("order", 0),
        }
        return (
            "allow_modified",
            modified,
            "scope_reduction",
            "delete_file_overly_broad_path: replaced with no-op marker write",
        )

    if "write_file_content_exceeds_threshold" in policy_reason or "write_file_content_too_large" in policy_reason:
        # B) Scope reduction: truncate content to threshold + "[TRUNCATED]"
        content = args.get("content", "")
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > write_content_max:
                # Truncate at byte boundary; ensure valid UTF-8
                truncated = content_bytes[:write_content_max].decode("utf-8", errors="ignore")
                truncated += "[TRUNCATED]"
                modified = {
                    "action_id": action_id,
                    "tool_name": "write_file",
                    "arguments": {
                        "path": args.get("path", ""),
                        "content": truncated,
                    },
                    "order": action.get("order", 0),
                }
                return (
                    "allow_modified",
                    modified,
                    "scope_reduction",
                    f"write_file content truncated to {write_content_max} bytes",
                )
        return ("block", None, "mechanism_error", "write_file stabilization failed: invalid content")

    # Path coercion: normalize path to sandbox-relative
    path = args.get("path", "")
    if path and isinstance(path, str):
        normalized = _normalize_path_to_sandbox_rel(path)
        if normalized != path.strip().replace("\\", "/").lstrip("/"):
            modified = {**action, "arguments": {**args, "path": normalized}}
            return (
                "allow_modified",
                modified,
                "argument_sanitization",
                "path normalized to sandbox-relative form",
            )

    return ("block", None, "mechanism_error", f"no stabilization for policy_reason={policy_reason}")
