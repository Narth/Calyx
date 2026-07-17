"""
Sandboxed Execution Adapter for autonomous runs.
Phase 1: Instrumentation only. No risk scoring, no blocking, no stabilization.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_sandbox_state_hash(sandbox_root: Path) -> str:
    """
    Compute canonical SHA256 hash of sandbox state.
    Walks directory in deterministic order; for each file records relative_path + sha256(content).
    Returns hash of canonical JSON snapshot.
    """
    sandbox_root = Path(sandbox_root).resolve()
    if not sandbox_root.exists():
        return hashlib.sha256(b"[]").hexdigest()

    entries: list[dict[str, str]] = []
    for p in sorted(sandbox_root.rglob("*")):
        if p.is_file():
            try:
                content = p.read_bytes()
                h = hashlib.sha256(content).hexdigest()
            except OSError:
                h = ""
            rp = str(p.relative_to(sandbox_root)).replace("\\", "/")
            entries.append({"relative_path": rp, "sha256": h})

    entries.sort(key=lambda e: e["relative_path"])
    canonical = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ExecutionAdapter:
    """
    Sandboxed adapter. All paths must resolve inside sandbox root.
    No network, no subprocess, no external filesystem.
    """

    ALLOWED_TOOLS = frozenset({"write_file", "read_file", "list_dir", "delete_file"})

    def __init__(self, sandbox_root: Path):
        self.sandbox_root = Path(sandbox_root).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path | None:
        """
        Resolve path relative to sandbox root. Reject traversal.
        Returns None if path escapes sandbox.
        """
        if not path or path == "/":
            return self.sandbox_root
        path = path.lstrip("/").replace("\\", "/")
        parts = path.split("/")
        resolved = self.sandbox_root
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                return None
            resolved = resolved / part
        try:
            resolved = resolved.resolve()
            resolved.relative_to(self.sandbox_root)
        except ValueError:
            return None
        return resolved

    def _resolve_file_path(self, path: str) -> Path | None:
        """Resolve path for a file operation. Parent dirs created for write."""
        r = self._resolve_path(path)
        if r is None:
            return None
        if r == self.sandbox_root:
            return None  # Need a file path, not root
        return r

    def execute(self, action: dict) -> dict:
        """
        Execute one action. Action format: {action_id, tool_name, arguments}.
        Returns {action_id, adapter_status, output_hash?}.
        Phase 1: no blocking; all allowed tools pass through.
        """
        action_id = action.get("action_id", "")
        tool_name = action.get("tool_name", "")
        args = action.get("arguments") or {}

        if tool_name not in self.ALLOWED_TOOLS:
            return {
                "action_id": action_id,
                "adapter_status": "error",
                "output_hash": None,
                "error": f"unknown_tool:{tool_name}",
            }

        try:
            if tool_name == "write_file":
                path = args.get("path", "")
                content = args.get("content", "")
                fp = self._resolve_file_path(path)
                if fp is None:
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "path_traversal_or_invalid",
                    }
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")
                out_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                return {"action_id": action_id, "adapter_status": "success", "output_hash": out_hash}

            elif tool_name == "read_file":
                path = args.get("path", "")
                fp = self._resolve_file_path(path)
                if fp is None:
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "path_traversal_or_invalid",
                    }
                if not fp.exists():
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "file_not_found",
                    }
                content = fp.read_text(encoding="utf-8")
                out_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                return {"action_id": action_id, "adapter_status": "success", "output_hash": out_hash}

            elif tool_name == "list_dir":
                path = args.get("path", ".") or "."
                rp = self._resolve_path(path)
                if rp is None:
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "path_traversal_or_invalid",
                    }
                if not rp.exists():
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "path_not_found",
                    }
                if not rp.is_dir():
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "not_a_directory",
                    }
                names = sorted(p.name for p in rp.iterdir())
                canonical = json.dumps(names, sort_keys=True, ensure_ascii=False)
                out_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                return {"action_id": action_id, "adapter_status": "success", "output_hash": out_hash}

            elif tool_name == "delete_file":
                path = args.get("path", "")
                fp = self._resolve_file_path(path)
                if fp is None:
                    return {
                        "action_id": action_id,
                        "adapter_status": "error",
                        "output_hash": None,
                        "error": "path_traversal_or_invalid",
                    }
                if not fp.exists():
                    return {"action_id": action_id, "adapter_status": "success", "output_hash": ""}
                fp.unlink()
                return {"action_id": action_id, "adapter_status": "success", "output_hash": ""}

        except OSError as e:
            return {
                "action_id": action_id,
                "adapter_status": "error",
                "output_hash": None,
                "error": str(e),
            }

        return {
            "action_id": action_id,
            "adapter_status": "error",
            "output_hash": None,
            "error": "unhandled",
        }
