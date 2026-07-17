"""
Canonical action schema for autonomous execution.
Used throughout plan, policy evaluation, and execution.
"""
from __future__ import annotations

import json
from typing import Any


def canonical_action(action_id: str, tool_name: str, arguments: dict, order: int) -> dict:
    """
    Build canonical action object.
    """
    return {
        "action_id": action_id,
        "tool_name": str(tool_name),
        "arguments": dict(arguments) if arguments else {},
        "order": int(order),
    }


def normalize_action(action: dict) -> dict:
    """
    Normalize action dict to canonical schema.
    Ensures action_id, tool_name, arguments, order present.
    """
    return canonical_action(
        action_id=str(action.get("action_id", "")),
        tool_name=action.get("tool_name", ""),
        arguments=action.get("arguments") or {},
        order=int(action.get("order", 0)),
    )
