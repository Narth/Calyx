"""System mode guard for safe test runs

Provides a global safe-mode flag and helpers that emit SYSTEM_MODE_SET
and block execution attempts with evidence events.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from .evidence import create_event, append_event

_safe_mode_state = {
    "safe_mode": False,
    "deny_execution": False,
    "reason": None,
    "set_at": None,
}

# Execution policy name/version active when live
_execution_policy = {"name": None, "version": None}


class ExecutionBlocked(Exception):
    pass


def set_system_mode(*, safe_mode: bool, deny_execution: bool, reason: str) -> None:
    """Set global system mode and emit SYSTEM_MODE_SET evidence event once."""
    global _safe_mode_state
    # Idempotent: if already set to same values, do nothing
    if _safe_mode_state["safe_mode"] == safe_mode and _safe_mode_state["deny_execution"] == deny_execution:
        return

    _safe_mode_state["safe_mode"] = bool(safe_mode)
    _safe_mode_state["deny_execution"] = bool(deny_execution)
    _safe_mode_state["reason"] = reason
    _safe_mode_state["set_at"] = datetime.now(timezone.utc).isoformat()

    try:
        evt = create_event(
            event_type="SYSTEM_MODE_SET",
            node_role="system_mode",
            summary="System mode applied",
            payload={
                "safe_mode": _safe_mode_state["safe_mode"],
                "deny_execution": _safe_mode_state["deny_execution"],
                "reason": _safe_mode_state["reason"],
                "set_at": _safe_mode_state["set_at"],
            },
            tags=["system", "mode"],
            session_id=None,
        )
        append_event(evt)
    except Exception:
        pass


def get_system_mode() -> Dict[str, Any]:
    d = dict(_safe_mode_state)
    d.update({"execution_policy": _execution_policy})
    return d


def set_execution_policy(name: str, version: str) -> None:
    _execution_policy["name"] = name
    _execution_policy["version"] = version


def check_execution_allowed(caller: str = "unknown") -> None:
    """Raise ExecutionBlocked if deny_execution enabled and emit evidence event.

    Call this from any execution path to ensure safe-mode enforcement.
    """
    if _safe_mode_state.get("deny_execution"):
        try:
            evt = create_event(
                event_type="EXECUTION_BLOCKED_SAFE_MODE",
                node_role="system_mode",
                summary=f"Execution blocked in safe mode: {caller}",
                payload={"caller": caller, "reason": _safe_mode_state.get("reason")},
                tags=["execution", "blocked", "safe_mode"],
                session_id=None,
            )
            append_event(evt)
        except Exception:
            pass
        raise ExecutionBlocked(f"Execution blocked by safe mode: {caller}")
