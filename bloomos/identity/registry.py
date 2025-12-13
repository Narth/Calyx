"""
BloomOS identity registry (read-only).

Reads existing Aster lineage artifacts and exposes a read-only identity view.
Safe Mode: ON. No side effects on import.
"""

from __future__ import annotations

import os
from typing import Dict, List

LINEAGE_DIR = os.path.join("identity", "lineage")


def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except Exception:
        return ""


def get_identity() -> Dict[str, List[Dict[str, str]]]:
    """
    Return a read-only view of lineage artifacts.

    Structure:
    {
      "lineage_files": [
         {"name": "...", "content": "..."},
      ]
    }
    """
    files: List[Dict[str, str]] = []
    if os.path.isdir(LINEAGE_DIR):
        for name in sorted(os.listdir(LINEAGE_DIR)):
            path = os.path.join(LINEAGE_DIR, name)
            if os.path.isfile(path) and name.lower().endswith((".md", ".json", ".jsonl")):
                files.append({"name": name, "content": _read_file(path)})
    return {"lineage_files": files}


__all__ = ["get_identity"]
