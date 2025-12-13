"""BloomOS Capability Registry v0.1 loader and annotator (read-only)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

REGISTRY_PATH = Path("config") / "bloomos_capabilities_v0.1.json"
REGISTRY_SCHEMA_VERSION = "capability_registry_v0.1"


class CapabilityRegistryError(Exception):
    """Raised when capability registry is missing or invalid."""


@lru_cache(maxsize=1)
def load_registry() -> Dict[str, Any]:
    """Load and validate the capability registry."""
    if not REGISTRY_PATH.exists():
        raise CapabilityRegistryError(f"Capability registry not found at {REGISTRY_PATH}")
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise CapabilityRegistryError(
            f"Unexpected registry schema_version: {data.get('schema_version')}"
        )
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict):
        raise CapabilityRegistryError("Registry capabilities must be an object mapping.")
    return data


def get_capability(name: str) -> Optional[Dict[str, Any]]:
    """Return capability entry or None if unknown."""
    registry = load_registry()
    return registry.get("capabilities", {}).get(name)


def annotate_action_request(action_request: Dict[str, Any]) -> Dict[str, Any]:
    """Return registry metadata for the given action request capability."""
    cap_name = action_request.get("capability")
    entry = get_capability(cap_name) if cap_name else None
    if entry:
        default_policy = entry.get("default_policy", {})
        return {
            "name": entry.get("name"),
            "domain": entry.get("domain"),
            "risk_level": entry.get("risk_level"),
            "default_allowed": bool(default_policy.get("allowed", False)),
            "policy_version": default_policy.get("policy_version"),
            "telemetry_tags": entry.get("telemetry_tags", []),
        }
    # Fallback for unregistered capability
    return {
        "name": cap_name,
        "domain": "unknown",
        "risk_level": "unknown",
        "default_allowed": False,
        "policy_version": "deny_all_policy_v0.1",
        "telemetry_tags": ["unregistered_capability"],
    }


__all__ = [
    "REGISTRY_PATH",
    "REGISTRY_SCHEMA_VERSION",
    "CapabilityRegistryError",
    "load_registry",
    "get_capability",
    "annotate_action_request",
]
