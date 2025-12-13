"""
Safety harness skeleton (advisory-only).

check_action(action_descriptor) evaluates against the forbidden-action matrix
and Safe Mode defaults. It is NOT wired to any dispatch or agent paths.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any

FORBIDDEN_MATRIX_PATH = os.path.join("bloomos", "kernel", "boundary", "FORBIDDEN_ACTION_MATRIX.json")


def _load_forbidden() -> Dict[str, bool]:
    if not os.path.exists(FORBIDDEN_MATRIX_PATH):
        return {}
    try:
        with open(FORBIDDEN_MATRIX_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            forbidden = {
                item.get("action"): bool(item.get("absolute", False))
                for item in data.get("forbidden_actions", [])
                if item.get("action")
            }
            return forbidden
    except Exception:
        return {}


def check_action(action_descriptor: str) -> Dict[str, Any]:
    """
    Advisory-only safety check.

    Returns: {"allowed": bool, "reason": str, "safe_mode": True}
    Safe Mode is ON by default, so non-listed actions are also denied.
    """
    forbidden = _load_forbidden()
    if action_descriptor in forbidden:
        return {"allowed": False, "reason": f"Forbidden by matrix: {action_descriptor}", "safe_mode": True}
    return {"allowed": False, "reason": "Safe Mode denies all runtime actions", "safe_mode": True}


__all__ = ["check_action"]
