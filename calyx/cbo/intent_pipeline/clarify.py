"""Clarify: check intent readiness, request clarification, update artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import load_intent_artifact, load_status, save_status, append_clarification


def needs_clarification(artifact: dict[str, Any], status: dict[str, Any] | None) -> bool:
    """True if intent is ambiguous or missing required fields for planning."""
    if status and status.get("status") == "ready":
        return False
    intent = (artifact.get("intent") or "").strip()
    if not intent or len(intent) < 2:
        return True
    task_type = artifact.get("task_type")
    if not task_type:
        return True
    return False


def mark_ready(intent_id: str, runtime_dir: Path) -> Path:
    """Mark intent as ready for planning."""
    return save_status(
        intent_id,
        runtime_dir,
        {"status": "ready"},
    )


def request_clarification(intent_id: str, runtime_dir: Path, message: str) -> Path:
    """Append clarification request to artifact."""
    from datetime import datetime, timezone
    return append_clarification(
        intent_id,
        runtime_dir,
        {"ts_utc": datetime.now(timezone.utc).isoformat(), "request": message},
    )
