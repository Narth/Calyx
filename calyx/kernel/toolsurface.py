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
            return False, "no_contract"
        contract, _ = load_contract(contract_path)
    tool = (tool_name or "").strip()
    if not tool:
        return False, "empty_tool_name"
    if tool in FORBIDDEN_TOOLS:
        return False, "forbidden_tool"
    allowed = get_tool_allowlist(contract, task_type)
    if tool in allowed:
        return True, "allowlisted"
    return False, "deny_by_default"


def get_allowed_tools_for_envelope(envelope: WorkEnvelope, contract: dict) -> list[str]:
    """Return the allowlisted tools for the envelope's task_type."""
    return get_tool_allowlist(contract, envelope.task_type)
