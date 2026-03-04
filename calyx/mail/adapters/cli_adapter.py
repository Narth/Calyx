"""CLI adapter: convert CLI args to Mail Envelope and route to CBO ingest."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..router import deliver_to_cbo_ingest


def cli_args_to_mail_envelope(
    *,
    intent: str,
    task_type: str = "doc_update",
    scope: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    source: str = "cli",
) -> dict[str, Any]:
    """
    Build a Mail Envelope from CLI arguments. Does not write; caller must call deliver_to_cbo_ingest.
    """
    envelope_id = str(uuid.uuid4())
    ts_utc = datetime.now(timezone.utc).isoformat()
    scope = scope or {"paths": ["**"]}
    constraints = constraints or {"timeout_seconds": 300}
    return {
        "envelope_id": envelope_id,
        "ts_utc": ts_utc,
        "source": source,
        "author": "cli",
        "channel_id": "",
        "message_id": "",
        "intent": intent,
        "task_type": task_type,
        "risk_hint": "low",
        "scope": scope,
        "constraints": constraints,
        "requires_human_approval": False,
        "approval_token": None,
        "evidence_requirements": {"harness_lanes": [], "checks": [], "receipt_types": []},
        "signature": None,
    }


def deliver_cli_mail_to_cbo_ingest(envelope: dict[str, Any], runtime_dir: Path) -> Path:
    """Route Mail Envelope to CBO ingest only."""
    return deliver_to_cbo_ingest(envelope, runtime_dir)
