"""
Pure stubs for benchmark tools. No real side effects, no network.
Used by the harness to simulate tool execution for metrics only.
"""
from __future__ import annotations


def stub_fs_read(path: str) -> dict:
    """Stub: always returns a fixed snippet."""
    return {"snippet": "<stub>", "lines": 0}


def stub_fs_list(path: str, max_items: int | None = None) -> dict:
    """Stub: always returns empty list."""
    return {"items": [], "count": 0}


def stub_repo_grep(pattern: str, file_ext: list | None = None) -> dict:
    """Stub: always returns no matches."""
    return {"matches": [], "count": 0}


def execute_stub(tool_name: str, args: dict | None = None) -> dict:
    """
    Execute a stub for the given tool. No real side effects.
    Returns a dict result for logging.
    """
    args = args or {}
    if tool_name == "fs_read":
        return stub_fs_read(args.get("path", ""))
    if tool_name == "fs_list":
        return stub_fs_list(args.get("path", ""), args.get("max_items"))
    if tool_name == "repo_grep":
        return stub_repo_grep(args.get("pattern", ""), args.get("file_ext"))
    return {"stub": True, "tool": tool_name, "message": "no_op"}
