# -*- coding: utf-8 -*-
"""
Evidence Export - Bundle Creation for Relay Transfer
=====================================================

Creates exportable evidence bundles for manual transfer between nodes.

ROLE: evidence/export
SCOPE: Evidence bundle creation and export tracking

CONSTRAINTS:
- Read-only access to local evidence
- Creates portable JSONL bundles
- Tracks export state to avoid duplicates
- No network operations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..schemas.evidence_envelope_v1 import (
    EvidenceEnvelopeV1,
    create_envelope,
    canonical_json,
    compute_payload_hash,
)
from ..core.config import get_config
from ..core.evidence import load_recent_events


COMPONENT_ROLE = "evidence_export"


@dataclass
class ExportState:
    """Tracks what has been exported."""
    node_id: str
    last_exported_seq: int = -1
    last_exported_event_count: int = 0  # Track how many events were exported
    last_export_at: Optional[str] = None
    total_exports: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExportState":
        return cls(
            node_id=data["node_id"],
            last_exported_seq=data.get("last_exported_seq", -1),
            last_exported_event_count=data.get("last_exported_event_count", 0),
            last_export_at=data.get("last_export_at"),
            total_exports=data.get("total_exports", 0),
        )


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    bundle_path: Optional[Path] = None
    envelope_count: int = 0
    seq_range: tuple[int, int] = (-1, -1)
    error: Optional[str] = None


def get_export_dir() -> Path:
    """Get directory for export bundles."""
    config = get_config()
    return config.data_dir / "exports"


def get_node_identity() -> tuple[str, str]:
    """
    Get or create stable node identity.
    
    Returns:
        Tuple of (node_id, node_name)
    """
    config = get_config()
    identity_path = config.data_dir / "node_identity.json"
    
    if identity_path.exists():
        try:
            with open(identity_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("node_id", "unknown"), data.get("node_name", "Unknown Node")
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Generate new identity
    import uuid
    import socket
    
    node_id = str(uuid.uuid4())[:12]
    try:
        node_name = socket.gethostname()
    except:
        node_name = "Station-Calyx-Node"
    
    # Save identity
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    with open(identity_path, "w", encoding="utf-8") as f:
        json.dump({"node_id": node_id, "node_name": node_name}, f, indent=2)
    
    return node_id, node_name


def load_export_state() -> ExportState:
    """Load export state for this node."""
    node_id, _ = get_node_identity()
    config = get_config()
    state_path = config.data_dir / "export_state.json"
    
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return ExportState.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError):
            pass
    
    return ExportState(node_id=node_id)


def save_export_state(state: ExportState) -> None:
    """Save export state."""
    config = get_config()
    state_path = config.data_dir / "export_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2)


def get_collector_version() -> str:
    """Get current collector version."""
    return "v1.7.0"


def convert_event_to_envelope(
    event: dict[str, Any],
    node_id: str,
    node_name: str,
    seq: int,
    prev_hash: Optional[str],
) -> EvidenceEnvelopeV1:
    """
    Convert a local event to an evidence envelope.
    
    Wraps existing event data in the relay envelope format.
    """
    # Extract timestamp
    captured_at = event.get("ts", datetime.now(timezone.utc).isoformat())
    
    # Build payload from event
    payload = {
        "original_event_type": event.get("event_type", "UNKNOWN"),
        "original_ts": event.get("ts"),
        "summary": event.get("summary", ""),
        "data": event.get("payload", {}),
        "tags": event.get("tags", []),
    }
    
    return create_envelope(
        node_id=node_id,
        seq=seq,
        event_type=event.get("event_type", "EXPORTED_EVENT"),
        payload=payload,
        collector_version=get_collector_version(),
        node_name=node_name,
        prev_hash=prev_hash,
    )


def export_evidence(
    recent: int = 1000,
    include_all: bool = False,
) -> ExportResult:
    """
    Export local evidence to a portable bundle.
    
    Args:
        recent: Number of recent events to consider
        include_all: If True, export all events; if False, only new since last export
        
    Returns:
        ExportResult with bundle path and statistics
    """
    node_id, node_name = get_node_identity()
    state = load_export_state()
    
    # Load local events
    events = load_recent_events(recent)
    
    if not events:
        return ExportResult(
            success=False,
            error="No events found to export",
        )
    
    # Filter to exportable event types
    exportable_types = {
        "SYSTEM_SNAPSHOT",
        "SCHEDULED_SNAPSHOT",
        "REFLECTION_GENERATED",
        "ADVISORY_GENERATED",
        "TEMPORAL_ANALYSIS_COMPLETED",
        "TREND_DETECTED",
        "DRIFT_WARNING",
        "PATTERN_RECURRING",
    }
    
    exportable = [e for e in events if e.get("event_type") in exportable_types]
    
    if not exportable:
        return ExportResult(
            success=False,
            error="No exportable events found",
        )
    
    # Determine which events to export
    if include_all:
        events_to_export = exportable
        start_seq = 0
    else:
        # Skip events that were already exported
        skip_count = state.last_exported_event_count
        events_to_export = exportable[skip_count:]
        start_seq = state.last_exported_seq + 1
    
    if not events_to_export:
        return ExportResult(
            success=False,
            error="No new events to export since last export",
        )
    
    # Create export directory
    export_dir = get_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate bundle filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"evidence_bundle_{node_id}_{timestamp}.jsonl"
    bundle_path = export_dir / bundle_name
    
    # Create envelopes
    envelopes = []
    prev_hash = None
    seq = start_seq
    
    for event in events_to_export:
        envelope = convert_event_to_envelope(
            event=event,
            node_id=node_id,
            node_name=node_name,
            seq=seq,
            prev_hash=prev_hash,
        )
        envelopes.append(envelope)
        prev_hash = envelope.compute_envelope_hash()
        seq += 1
    
    # Write bundle
    with open(bundle_path, "w", encoding="utf-8") as f:
        for env in envelopes:
            f.write(canonical_json(env.to_dict()) + "\n")
    
    # Update state
    state.last_exported_seq = seq - 1
    state.last_exported_event_count = len(exportable)  # Total exportable events seen
    state.last_export_at = datetime.now(timezone.utc).isoformat()
    state.total_exports += 1
    save_export_state(state)
    
    return ExportResult(
        success=True,
        bundle_path=bundle_path,
        envelope_count=len(envelopes),
        seq_range=(start_seq, seq - 1),
    )


def get_export_status() -> dict[str, Any]:
    """Get current export status."""
    node_id, node_name = get_node_identity()
    state = load_export_state()
    
    return {
        "node_id": node_id,
        "node_name": node_name,
        "last_exported_seq": state.last_exported_seq,
        "last_export_at": state.last_export_at,
        "total_exports": state.total_exports,
        "export_dir": str(get_export_dir()),
    }


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Evidence Export Module")
    print()
    status = get_export_status()
    print(f"Node ID: {status['node_id']}")
    print(f"Node Name: {status['node_name']}")
    print(f"Last Export: {status['last_export_at'] or 'Never'}")
    print(f"Export Dir: {status['export_dir']}")
