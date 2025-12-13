"""
BloomOS runtime storage substrate (append-only logging).

Safe Mode: ON by default. This module is reflection-focused and writes only
append-only records under logs/bloomos/. No side effects occur on import.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

LOG_DIR = os.path.join("logs", "bloomos")
LOG_FILE = os.path.join(LOG_DIR, "runtime.log")


def _ensure_log_dir() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)


def log_event(kind: str, payload: Dict[str, Any]) -> str:
    """
    Append an event to the BloomOS runtime log.

    This is append-only and Safe Mode compatible. Returns the log line.
    """
    _ensure_log_dir()
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "kind": kind,
        "payload": payload,
    }
    line = json.dumps(record, separators=(",", ":"))
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line


__all__ = ["log_event"]
