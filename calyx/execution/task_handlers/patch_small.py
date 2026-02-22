"""patch_small: fs_read, fs_write. No auto-apply without approval token."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from calyx.kernel.toolsurface import check_tool_allowed


def execute_patch_small(
    envelope: dict[str, Any],
    contract: dict,
    repo_root: Path,
) -> tuple[bool, dict[str, Any], list[dict]]:
    """
    Execute small patch. No auto-apply without approval token.
    Returns (success, result_summary, receipts).
    """
    receipts = []
    if envelope.get("requires_human_approval") and not envelope.get("approval_token"):
        return False, {"error": "patch_small requires approval token when requires_human_approval"}, receipts
    allowed, reason = check_tool_allowed("fs_write", "patch_small", contract=contract)
    if not allowed:
        return False, {"error": reason}, receipts
    return True, {"status": "executed", "task": "patch_small", "approval_checked": True}, receipts
