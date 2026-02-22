"""
Ingest replay ledger: persist seen envelope_ids across restarts.
Reject duplicate submissions; write rejection receipt.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_ledger_path(runtime_dir: Path) -> Path:
    return runtime_dir / "cbo" / "ingest_replay_ledger.jsonl"


def _ensure_ledger_dir(runtime_dir: Path) -> Path:
    (runtime_dir / "cbo").mkdir(parents=True, exist_ok=True)
    return runtime_dir


def has_seen_envelope(envelope_id: str, runtime_dir: Path) -> bool:
    """True if envelope_id already in ledger (replay)."""
    ledger = get_ledger_path(runtime_dir)
    if not ledger.exists():
        return False
    try:
        with open(ledger, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get("envelope_id") == envelope_id:
                    return True
    except Exception:
        pass
    return False


def add_seen_envelope(envelope_id: str, runtime_dir: Path, ts_utc: str = "") -> None:
    """Append envelope_id to ledger (atomic append)."""
    _ensure_ledger_dir(runtime_dir)
    ledger = get_ledger_path(runtime_dir)
    ts = ts_utc or datetime.now(timezone.utc).isoformat()
    rec = {"envelope_id": envelope_id, "seen_at": ts}
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_rejection_receipt(
    envelope_id: str,
    reason: str,
    receipt_type: str,
    runtime_dir: Path,
) -> Path:
    """Write rejection receipt to runtime/receipts."""
    receipts_dir = runtime_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = receipts_dir / f"ingest_reject__{ts}.jsonl"
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "ingest",
        "status": "rejected",
        "receipt_type": receipt_type,
        "envelope_id": envelope_id,
        "reason": reason,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
