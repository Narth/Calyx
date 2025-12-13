"""
BloomOS configuration loader (read-only).

Safe Mode: ON by default. No side effects on import.
"""

from __future__ import annotations

import os
from typing import Any, Dict

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None

POLICY_PATH = os.path.join("calyx", "core", "policy.yaml")
IDENTITY_CONFIG_PATH = os.path.join("bloomos", "identity", "config.yaml")


def _load_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    text = open(path, "r", encoding="utf-8").read()
    if yaml:
        try:
            data = yaml.safe_load(text) or {}
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Fallback naive parser for simple key: value
    result: Dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        result[key.strip()] = val.strip()
    return result


def load_policy() -> Dict[str, Any]:
    """Return a read-only snapshot of policy.yaml."""
    return _load_yaml(POLICY_PATH)


def load_identity_config() -> Dict[str, Any]:
    """Return optional BloomOS identity config if present."""
    return _load_yaml(IDENTITY_CONFIG_PATH)


__all__ = ["load_policy", "load_identity_config"]
