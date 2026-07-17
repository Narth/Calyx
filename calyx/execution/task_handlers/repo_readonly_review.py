"""repo_readonly_review: read-only fs_read, repo_grep, fs_list. No writes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calyx.kernel.toolsurface import check_tool_allowed


def execute_repo_readonly_review(
    envelope: dict[str, Any],
    contract: dict,
    repo_root: Path,
) -> tuple[bool, dict[str, Any], list[dict]]:
    """
    Execute read-only review. Returns (success, result_summary, receipts).
    No file writes; tools: fs_read, repo_grep, fs_list.
    """
    receipts = []
    scope_paths = (envelope.get("scope") or {}).get("paths") or ["**"]
    # Stub: no actual tool calls; real impl would call allowlisted tools only
    for path in scope_paths[:3]:
        allowed, reason = check_tool_allowed("fs_read", "repo_readonly_review", contract=contract)
        if not allowed:
            return False, {"error": reason, "tool": "fs_read"}, receipts
    return True, {"status": "executed", "scope_paths": scope_paths, "read_only": True}, receipts
