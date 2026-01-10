# -*- coding: utf-8 -*-
"""
Ingest Audit Logging
====================

Append-only audit log for evidence ingest operations.

ROLE: evidence/audit
SCOPE: Audit trail for network ingest operations

CONSTRAINTS:
- Append-only writes
- No modification of existing entries
- Structured JSON lines format
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config


COMPONENT_ROLE = "ingest_audit"


def get_audit_path() -> Path:
    """Get path to audit log file."""
    config = get_config()
    return config.data_dir / "logs" / "ingest" / "audit.jsonl"


def log_ingest_event(
    remote_addr: str,
    node_id: Optional[str],
    accepted_count: int,
    rejected_count: int,
    last_seq_after: int,
    auth_status: str = "authenticated",
    rejection_reasons: Optional[list[str]] = None,
    request_size_bytes: int = 0,
    envelope_count_received: int = 0,
) -> None:
    """
    Log an ingest event to the audit trail.
    
    Args:
        remote_addr: IP address of the requester
        node_id: Node ID from the envelopes (if available)
        accepted_count: Number of envelopes accepted
        rejected_count: Number of envelopes rejected
        last_seq_after: Last sequence number after ingest
        auth_status: Authentication status (authenticated, rejected, missing_token)
        rejection_reasons: List of rejection reasons (bounded)
        request_size_bytes: Size of request body
        envelope_count_received: Number of envelopes in request
    """
    audit_path = get_audit_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    
    event = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "remote_addr": remote_addr,
        "node_id": node_id,
        "auth_status": auth_status,
        "envelope_count_received": envelope_count_received,
        "request_size_bytes": request_size_bytes,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "last_seq_after": last_seq_after,
        "rejection_reasons": (rejection_reasons or [])[:5],  # Bounded
    }
    
    # Append to audit log
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def log_auth_failure(
    remote_addr: str,
    reason: str,
    request_size_bytes: int = 0,
) -> None:
    """Log an authentication failure."""
    log_ingest_event(
        remote_addr=remote_addr,
        node_id=None,
        accepted_count=0,
        rejected_count=0,
        last_seq_after=-1,
        auth_status=reason,
        request_size_bytes=request_size_bytes,
    )


def get_recent_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    """Read recent audit events (for diagnostics)."""
    audit_path = get_audit_path()
    
    if not audit_path.exists():
        return []
    
    events = []
    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    return events[-limit:]
