"""
Policy binding (read-only).

Loads policy.yaml and returns a normalized snapshot. Safe Mode enforced.
"""

from __future__ import annotations

from typing import Any, Dict

from bloomos.runtime.config import load_policy


def _parse_float(val: Any) -> Any:
    try:
        return float(val)
    except Exception:
        return val


def get_policy_snapshot() -> Dict[str, Any]:
    """Return a read-only snapshot of policy values."""
    data = load_policy()
    normalized: Dict[str, Any] = {}
    for key, val in data.items():
        normalized[key] = _parse_float(val)
    return normalized


__all__ = ["get_policy_snapshot"]
