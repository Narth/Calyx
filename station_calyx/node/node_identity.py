#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node Identity - Stable node_id generation and persistence.

Generates a unique, stable node_id for this Calyx Terminal instance.
Stores in local config to persist across restarts.

[CBO Governance]: Node identity is hardware-fingerprinted for chronological
continuity across all Station Calyx instances. The fingerprint ensures that
evidence envelopes can be traced back to their origin node deterministically.

Usage:
    from station_calyx.node import get_node_identity
    
    node = get_node_identity()
    print(node.node_id)  # e.g., "node_calyx_a3f8c2d1"
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
NODE_CONFIG_DIR = ROOT / "outgoing" / "node"
NODE_CONFIG_PATH = NODE_CONFIG_DIR / "identity.json"


@dataclass
class NodeIdentity:
    """Node identity container with hardware fingerprint."""
    
    node_id: str
    hostname: str
    platform_info: str
    created_at: str
    fingerprint: str
    station_name: str = "Station Calyx"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "platform": self.platform_info,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
            "station_name": self.station_name,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeIdentity:
        return cls(
            node_id=data["node_id"],
            hostname=data["hostname"],
            platform_info=data.get("platform", data.get("platform_info", "")),
            created_at=data["created_at"],
            fingerprint=data["fingerprint"],
            station_name=data.get("station_name", "Station Calyx"),
        )


def _generate_fingerprint() -> str:
    """
    Generate stable fingerprint from machine characteristics.
    
    Uses hostname, platform, machine type, and MAC address to create
    a deterministic identifier that survives reboots but changes if
    hardware is significantly altered.
    """
    hostname = socket.gethostname()
    platform_info = platform.platform()
    machine = platform.machine()
    
    # Use MAC address as stable hardware ID (first available interface)
    mac = uuid.getnode()
    
    # Create deterministic hash from components
    components = f"{hostname}:{platform_info}:{machine}:{mac}".encode("utf-8")
    return hashlib.sha256(components).hexdigest()[:16]


def _generate_node_id(fingerprint: str) -> str:
    """Generate human-friendly node_id from fingerprint."""
    # Use first 8 chars of fingerprint for readability
    return f"node_calyx_{fingerprint[:8]}"


def _load_identity() -> Optional[NodeIdentity]:
    """Load existing identity from config file."""
    if not NODE_CONFIG_PATH.exists():
        return None
    
    try:
        data = json.loads(NODE_CONFIG_PATH.read_text(encoding="utf-8"))
        return NodeIdentity.from_dict(data)
    except Exception as e:
        print(f"[WARN] Failed to load node identity: {e}")
        return None


def _save_identity(identity: NodeIdentity) -> None:
    """Persist identity to config file (append-only directory, atomic write)."""
    NODE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Atomic write via temp file
    temp_path = NODE_CONFIG_PATH.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(identity.to_dict(), indent=2),
        encoding="utf-8"
    )
    temp_path.replace(NODE_CONFIG_PATH)


def _load_station_name() -> str:
    """Load station name from config.yaml if available."""
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        return "Station Calyx"
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("station", {}).get("name", "Station Calyx")
    except Exception:
        return "Station Calyx"


def get_node_identity(force_regenerate: bool = False) -> NodeIdentity:
    """
    Get or create stable node identity.

    [CBO Governance]: Identity is generated once and persisted. The node_id
    is deterministic based on hardware fingerprint, ensuring chronological
    continuity across restarts and sessions.

    Args:
        force_regenerate: If True, generate new identity even if one exists
                         (use with caution - breaks chain continuity)

    Returns:
        NodeIdentity with stable node_id
    """
    if not force_regenerate:
        existing = _load_identity()
        if existing:
            return existing
    
    # Generate new identity
    fingerprint = _generate_fingerprint()
    node_id = _generate_node_id(fingerprint)
    station_name = _load_station_name()
    
    identity = NodeIdentity(
        node_id=node_id,
        hostname=socket.gethostname(),
        platform_info=platform.platform(),
        created_at=datetime.now().isoformat(),
        fingerprint=fingerprint,
        station_name=station_name,
    )
    
    _save_identity(identity)
    print(f"[INFO] Node identity created: {node_id}")
    return identity


if __name__ == "__main__":
    # CLI test
    node = get_node_identity()
    print(f"Node Identity: {node.node_id}")
    print(f"Hostname: {node.hostname}")
    print(f"Platform: {node.platform_info}")
    print(f"Station: {node.station_name}")
    print(f"Created: {node.created_at}")
    print(f"Fingerprint: {node.fingerprint}")
