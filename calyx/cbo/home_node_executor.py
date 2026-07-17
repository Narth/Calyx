"""
Home Node Executor - Executes allowed tools on Station Calyx (home node).
Tools are executed locally; results are returned for use in CBO responses.
All tool calls are gated by policy.allowlist.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from benchmarks.harness.policy import check_tool


def _fs_read_real(path: str, repo_root: Path) -> dict[str, Any]:
    """Read file contents. Path is relative to repo_root."""
    try:
        full_path = (repo_root / path).resolve()
        if not str(full_path).startswith(str(repo_root.resolve())):
            return {"error": "path_outside_repo", "path": path}
        if not full_path.exists():
            return {"error": "file_not_found", "path": path}
        if not full_path.is_file():
            return {"error": "not_a_file", "path": path}
        content = full_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        return {
            "snippet": content[:2000],
            "lines": len(lines),
            "path": path,
            "truncated": len(content) > 2000,
        }
    except Exception as e:
        return {"error": str(e), "path": path}


def _fs_list_real(path: str, repo_root: Path, max_items: Optional[int] = 50) -> dict[str, Any]:
    """List directory contents."""
    try:
        full_path = (repo_root / path).resolve()
        if not str(full_path).startswith(str(repo_root.resolve())):
            return {"error": "path_outside_repo", "path": path, "items": []}
        if not full_path.exists():
            return {"error": "path_not_found", "path": path, "items": []}
        if not full_path.is_dir():
            return {"error": "not_a_directory", "path": path, "items": []}
        items = []
        for i, p in enumerate(sorted(full_path.iterdir())):
            if max_items and i >= max_items:
                break
            items.append({"name": p.name, "type": "dir" if p.is_dir() else "file"})
        return {"items": items, "count": len(items), "path": path}
    except Exception as e:
        return {"error": str(e), "path": path, "items": []}


def _repo_grep_real(pattern: str, repo_root: Path, file_ext: Optional[list] = None) -> dict[str, Any]:
    """Grep for pattern in repo (simplified: searches common text files)."""
    try:
        import re
        matches = []
        pattern_re = re.compile(pattern, re.IGNORECASE)
        ext_set = set(file_ext) if file_ext else None
        for path in repo_root.rglob("*"):
            if not path.is_file():
                continue
            if ext_set and path.suffix not in ext_set:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if pattern_re.search(line):
                    rel = path.relative_to(repo_root)
                    matches.append({"file": str(rel), "line": i, "match": line.strip()[:100]})
                    if len(matches) >= 20:
                        break
            if len(matches) >= 20:
                break
        return {"matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": str(e), "matches": [], "count": 0}


def _emit(event: str, msg: str, level: str = "INFO", data: dict | None = None) -> None:
    try:
        from calyx.kernel.event_ledger import emit
        emit(level=level, component="cbo", event=event, msg=msg, data=data or {})
    except Exception:
        pass


def execute_tool(
    tool_name: str,
    args: dict | None,
    repo_root: Path,
) -> tuple[bool, dict[str, Any]]:
    """
    Execute an allowed tool on the home node.
    Returns (success, result_dict). Only allowlisted tools execute.
    """
    args = args or {}
    _emit("toolcall.requested", f"Tool requested: {tool_name}", data={"tool": tool_name, "args_keys": list((args or {}).keys())})
    allowed, reason = check_tool(tool_name, args)
    if not allowed:
        _emit("toolcall.denied", f"Tool denied: {tool_name} reason={reason}", level="WARN", data={"tool": tool_name, "reason": reason})
        return False, {"error": f"denied: {reason}", "tool": tool_name}

    _emit("toolcall.allowed", f"Tool allowed: {tool_name}", data={"tool": tool_name})
    try:
        if tool_name == "fs_read":
            path = args.get("path", "")
            if not path or not isinstance(path, str):
                return False, {"error": "fs_read requires path (string)", "tool": tool_name}
            return True, _fs_read_real(path, repo_root)
        if tool_name == "fs_list":
            path = args.get("path", ".")
            max_items = args.get("max_items")
            return True, _fs_list_real(path, repo_root, max_items)
        if tool_name == "repo_grep":
            pattern = args.get("pattern", "")
            file_ext = args.get("file_ext")
            return True, _repo_grep_real(pattern, repo_root, file_ext)

        _emit("toolcall.denied", f"Unknown tool: {tool_name}", level="WARN", data={"tool": tool_name})
        return False, {"error": "unknown_tool", "tool": tool_name}
    except Exception as e:
        _emit("toolcall.error", f"Tool error: {tool_name} {e}", level="ERROR", data={"tool": tool_name, "error": str(e)[:200]})
        return False, {"error": str(e), "tool": tool_name}
