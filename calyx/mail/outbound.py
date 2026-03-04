"""
Outbound: deterministic queue for CBO → Mail Envelope → adapter (Discord or simulated).
Delivery receipt written; failed delivery logged for retry.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_mail_outbox_path(runtime_dir: Path) -> Path:
    """Canonical path for outbound mail queue."""
    path = runtime_dir / "cbo" / "mail_outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def enqueue_outbound(
    envelope: dict[str, Any],
    runtime_dir: Path,
    *,
    delivery_type: str = "clarification",
) -> Path:
    """
    Enqueue outbound Mail Envelope. Atomic write. Returns path.
    Caller or consumer writes delivery receipt on send; failed delivery logged for retry.
    """
    outbox = get_mail_outbox_path(runtime_dir)
    eid = envelope.get("envelope_id") or envelope.get("msg_id") or ""
    if not eid:
        eid = f"out_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in eid)
    payload = {"_delivery_type": delivery_type, **envelope}
    filepath = outbox / f"{safe_id}.json"
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=outbox, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, filepath)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return filepath


def write_delivery_receipt(
    envelope_id: str,
    status: str,
    runtime_dir: Path,
    error: str | None = None,
) -> Path:
    """Write delivery receipt (delivered / failed)."""
    receipts_dir = runtime_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = receipts_dir / f"outbound_delivery__{ts}.jsonl"
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "outbound",
        "status": status,
        "receipt_type": "delivery",
        "envelope_id": envelope_id,
        "error": error,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
