"""Discord adapter: convert Discord message to Mail Envelope and route to CBO ingest. No direct outbox write."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..router import deliver_to_cbo_ingest


def discord_message_to_mail_envelope(
    *,
    author_id: str,
    channel_id: str,
    message_id: str,
    content: str,
    task_type: str = "doc_update",
    scope: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    risk_hint: str | None = None,
    requires_human_approval: bool = False,
    approval_token: str | None = None,
) -> dict[str, Any]:
    """
    Build a Mail Envelope (ingest payload) from Discord message metadata.
    Does not write anywhere; caller must call deliver_to_cbo_ingest.
    """
    envelope_id = str(uuid.uuid4())
    ts_utc = datetime.now(timezone.utc).isoformat()
    scope = scope or {"paths": ["**"]}
    constraints = constraints or {"timeout_seconds": 300}
    return {
        "envelope_id": envelope_id,
        "ts_utc": ts_utc,
        "source": "discord",
        "author": author_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "intent": content,
        "task_type": task_type,
        "risk_hint": risk_hint,
        "scope": scope,
        "constraints": constraints,
        "requires_human_approval": requires_human_approval,
        "approval_token": approval_token,
        "evidence_requirements": {"harness_lanes": [], "checks": [], "receipt_types": []},
        "signature": None,
    }


def deliver_discord_mail_to_cbo_ingest(envelope: dict[str, Any], runtime_dir: Path) -> Path | None:
    """Route Mail Envelope to CBO ingest only. Returns None if replay rejected."""
    return deliver_to_cbo_ingest(envelope, runtime_dir)
