"""Deny-by-default tool routing. Explicit allowlist from contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import load_contract, get_tool_allowlist
from .envelope import WorkEnvelope

FORBIDDEN_TOOLS = frozenset({"eval", "exec", "subprocess", "run_shell", "discord_send", "send_email", "http_request"})


def check_tool_allowed(
    tool_name: str,
    task_type: str,
    contract: dict | None = None,
    contract_path: Path | str | None = None,
) -> tuple[bool, str]:
    """
    Check if a tool is allowed for the given task_type. Deny-by-default.
    Returns (allowed: bool, reason: str).
    Either contract dict or contract_path must be provided.
    """
    if contract is None:
        if contract_path is None:
            try:
                from .event_ledger import emit
                emit("WARN", "kernel", "toolcall.denied", "No contract", data={"tool": tool_name or "", "reason": "no_contract"})
            except Exception:
                pass
            return False, "no_contract"
        contract, _ = load_contract(contract_path)
    tool = (tool_name or "").strip()
    if not tool:
        return False, "empty_tool_name"
    if tool in FORBIDDEN_TOOLS:
        try:
            from .event_ledger import emit
            emit("WARN", "kernel", "toolcall.denied", f"Forbidden tool: {tool}", data={"tool": tool, "reason": "forbidden_tool"})
        except Exception:
            pass
        return False, "forbidden_tool"
    allowed = get_tool_allowlist(contract, task_type)
    if tool in allowed:
        return True, "allowlisted"
    try:
        from .event_ledger import emit
        emit("WARN", "kernel", "toolcall.denied", f"Deny by default: {tool}", data={"tool": tool, "task_type": task_type, "reason": "deny_by_default"})
    except Exception:
        pass
    return False, "deny_by_default"


def get_allowed_tools_for_envelope(envelope: WorkEnvelope, contract: dict) -> list[str]:
    """Return the allowlisted tools for the envelope's task_type."""
    return get_tool_allowlist(contract, envelope.task_type)
