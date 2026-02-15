"""
Deny-by-default policy gate + allowlist.
No network; no dynamic execution. Pure function of (tool_name, args) -> (allowed, reason).
"""
from __future__ import annotations

# Allowlisted tools: only these may execute in "calyx" variant.
ALLOWLIST = frozenset({"fs_read", "fs_list", "repo_grep"})

# Tools that are never allowed (explicit deny).
FORBIDDEN = frozenset({"eval", "exec", "subprocess", "run_shell", "discord_send", "send_email", "http_request"})


def check_tool(tool_name: str, args: dict | None = None) -> tuple[bool, str]:
    """
    Check if a tool call is allowed under Calyx deny-by-default policy.
    Returns (allowed: bool, reason: str).
    """
    if args is None:
        args = {}
    tool = (tool_name or "").strip()
    if not tool:
        return False, "empty_tool_name"
    if tool in FORBIDDEN:
        return False, "forbidden_tool"
    if tool in ALLOWLIST:
        return True, "allowlisted"
    return False, "deny_by_default"
