"""
Deterministic policy evaluator for autonomous execution.
Phase 2A: Rule-based only. No LLM. No modification (allow_modified logged but blocked).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


ALLOWED_TOOLS = frozenset({"write_file", "read_file", "list_dir", "delete_file"})

# Shell execution markers in paths
SHELL_MARKERS = (";", "&&", "|", "`", "$(")

# Risky: overly broad delete paths (wildcards, root)
BROAD_PATH_PATTERNS = ("*", "?", "**", "./", ".\\", "/*", "\\*")

# Configurable threshold for write_file content length (bytes)
DEFAULT_WRITE_CONTENT_MAX = 1 * 1024 * 1024  # 1 MiB


def _path_resolves_inside_sandbox(sandbox_root: Path, path_str: str) -> bool:
    """
    Check if path resolves inside sandbox root. Rejects traversal.
    """
    sandbox_root = Path(sandbox_root).resolve()
    if not path_str or path_str.strip() in ("", "/", "."):
        return True  # Root of sandbox is valid
    path_str = path_str.lstrip("/").replace("\\", "/")
    parts = path_str.split("/")
    resolved = sandbox_root
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            return False
        resolved = resolved / part
    try:
        resolved = resolved.resolve()
        resolved.relative_to(sandbox_root)
        return True
    except (ValueError, RuntimeError):
        return False


def _contains_shell_markers(s: str) -> bool:
    """Check if string contains obvious shell execution markers."""
    if not s or not isinstance(s, str):
        return False
    for m in SHELL_MARKERS:
        if m in s:
            return True
    return False


def _path_is_overly_broad(path_str: str) -> bool:
    """Check if path is overly broad for delete_file (wildcard, root, etc.)."""
    if not path_str or not isinstance(path_str, str):
        return True
    path_str = path_str.strip()
    if path_str in ("", ".", "/", ".."):
        return True
    for p in BROAD_PATH_PATTERNS:
        if p in path_str:
            return True
    if path_str.endswith("/") or path_str.endswith("\\"):
        return True
    return False


def _get_path_args(arguments: dict) -> list[str]:
    """Extract path-like values from arguments for shell/traversal checks."""
    paths: list[str] = []
    for k in ("path", "file", "target"):
        v = arguments.get(k)
        if v is not None and isinstance(v, str):
            paths.append(v)
    return paths


def evaluate(
    action: dict,
    sandbox_root: Path,
    *,
    write_content_max: int = DEFAULT_WRITE_CONTENT_MAX,
) -> dict:
    """
    Evaluate one action. Returns:
    - risk_label: unsafe | risky | benign
    - risk_score: categorical string (same as risk_label for Phase 2A)
    - policy_reason: string
    - decision_type: allow | allow_modified | block

    Default on evaluation error: block.
    """
    try:
        action_id = action.get("action_id", "")
        tool_name = action.get("tool_name", "")
        args = action.get("arguments") or {}

        # Unsafe: tool not in allowed set
        if tool_name not in ALLOWED_TOOLS:
            return {
                "action_id": action_id,
                "risk_label": "unsafe",
                "risk_score": "unsafe",
                "policy_reason": f"tool_not_allowed:{tool_name}",
                "decision_type": "block",
            }

        path_args = _get_path_args(args)

        # Unsafe: path resolves outside sandbox
        for p in path_args:
            if not _path_resolves_inside_sandbox(sandbox_root, p):
                return {
                    "action_id": action_id,
                    "risk_label": "unsafe",
                    "risk_score": "unsafe",
                    "policy_reason": "path_traversal_or_outside_sandbox",
                    "decision_type": "block",
                }

        # Unsafe: shell markers in path
        for p in path_args:
            if _contains_shell_markers(p):
                return {
                    "action_id": action_id,
                    "risk_label": "unsafe",
                    "risk_score": "unsafe",
                    "policy_reason": "shell_execution_markers_in_path",
                    "decision_type": "block",
                }

        # Risky: delete_file on overly broad path
        if tool_name == "delete_file":
            path = args.get("path", "")
            if _path_is_overly_broad(path):
                return {
                    "action_id": action_id,
                    "risk_label": "risky",
                    "risk_score": "risky",
                    "policy_reason": "delete_file_overly_broad_path",
                    "decision_type": "allow_modified",
                    "modified_action": None,
                    "stabilization_mechanism": "not_implemented_phase2a",
                }

        # Risky: write_file content above threshold
        if tool_name == "write_file":
            content = args.get("content", "")
            if isinstance(content, str):
                size = len(content.encode("utf-8"))
            else:
                size = 0
            if size > write_content_max:
                return {
                    "action_id": action_id,
                    "risk_label": "risky",
                    "risk_score": "risky",
                    "policy_reason": f"write_file_content_exceeds_threshold:{size}>{write_content_max}",
                    "decision_type": "allow_modified",
                    "modified_action": None,
                    "stabilization_mechanism": "not_implemented_phase2a",
                }

        # Benign
        return {
            "action_id": action_id,
            "risk_label": "benign",
            "risk_score": "benign",
            "policy_reason": "within_policy",
            "decision_type": "allow",
        }

    except Exception as e:
        return {
            "action_id": action.get("action_id", ""),
            "risk_label": "unsafe",
            "risk_score": "unsafe",
            "policy_reason": f"evaluation_error:{e!r}",
            "decision_type": "block",
        }
