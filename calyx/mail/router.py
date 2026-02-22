"""Router: deliver Mail Envelopes to CBO ingest. Replay protection; atomic write. No execution."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from calyx.kernel.integrity_gate import spine_operation_lease, SystemIntegrityError

from .ingest_ledger import add_seen_envelope, has_seen_envelope, write_rejection_receipt


def get_cbo_mail_inbox_path(runtime_dir: Path) -> Path:
    """Canonical path for CBO mail ingest inbox. All inbound Mail Envelopes land here."""
    path = runtime_dir / "cbo" / "mail_inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def deliver_to_cbo_ingest(
    envelope: dict[str, Any],
    runtime_dir: Path,
    *,
    replay_ledger: bool = True,
) -> Path | None:
    """
    Deliver a Mail Envelope to CBO ingest mailbox. Atomic write. Replay rejected and receipted.
    Returns path to written file, or None if rejected (replay, integrity failure, or lease held by another coordinator).
    """
    repo_root = runtime_dir.parent
    with spine_operation_lease(runtime_dir, repo_root, include_execution_path=False, skip_if_env=True) as ok:
        if not ok:
            eid = envelope.get("envelope_id") or envelope.get("msg_id") or "unknown"
            write_rejection_receipt(str(eid), "integrity_or_lease_failed", "ingest_integrity", runtime_dir)
            return None

        eid = envelope.get("envelope_id") or envelope.get("msg_id") or ""
        if not eid or eid == "unknown":
            return None
        if replay_ledger and has_seen_envelope(eid, runtime_dir):
            write_rejection_receipt(eid, "replay", "ingest_replay", runtime_dir)
            return None
        inbox = get_cbo_mail_inbox_path(runtime_dir)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in eid)
        filepath = inbox / f"{safe_id}.json"
        content = json.dumps(envelope, indent=2, ensure_ascii=False)
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(dir=inbox, prefix=".", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, filepath)
            tmp = None
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        if replay_ledger:
            add_seen_envelope(eid, runtime_dir, envelope.get("ts_utc", ""))
        return filepath
