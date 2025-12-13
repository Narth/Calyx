"""
Lifecycle controller (manual, Safe Mode).

States: SEED, SEEDLING_REFLECTION_ONLY.
Transitions require an explicit Architect seal file. No dispatch/agent runs/policy changes.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

STATE_FILE = os.path.join("logs", "bloomos", "lifecycle_state.json")
VALID_STATES = {"SEED", "SEEDLING_REFLECTION_ONLY"}


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


def get_state() -> str:
    if not os.path.exists(STATE_FILE):
        return "SEED"
    try:
        data = json.load(open(STATE_FILE, "r", encoding="utf-8"))
        state = data.get("state")
        if state in VALID_STATES:
            return state
    except Exception:
        pass
    return "SEED"


def set_state(new_state: str, architect_seal_path: str) -> Dict[str, Any]:
    """
    Attempt to set lifecycle state. Requires Architect seal file existence.
    Safe Mode: no automatic actions, no dispatch.
    """
    if new_state not in VALID_STATES:
        return {"ok": False, "reason": "invalid_state"}
    if not architect_seal_path or not os.path.exists(architect_seal_path):
        return {"ok": False, "reason": "architect_seal_missing"}
    _ensure_dir()
    record = {"state": new_state, "seal_path": architect_seal_path}
    with open(STATE_FILE, "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    return {"ok": True, "state": new_state}


__all__ = ["get_state", "set_state"]
