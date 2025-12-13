"""
BloomOS IPC abstraction (file-based, non-network).

Safe Mode: ON by default. No sockets or network. Non-operational placeholder.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


class FileChannel:
    """A simple file-based channel for read-only or append-only exchanges."""

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def write(self, message: Dict[str, Any]) -> None:
        """Append a message (append-only)."""
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(message) + "\n")

    def read_all(self) -> Optional[list]:
        """Read all messages; returns list or None if file missing."""
        if not os.path.exists(self.path):
            return None
        with open(self.path, "r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


__all__ = ["FileChannel"]
