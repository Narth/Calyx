"""Approval request utilities for Station Calyx."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[2]
APPROVALS_PATH = ROOT / "calyx" / "cbo" / "approvals.jsonl"
APPROVALS_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class ApprovalRecord:
    approval_id: str
    summary: str
    details: str = ""
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, object] = field(default_factory=dict)
    actor: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "approval_id": self.approval_id,
            "summary": self.summary,
            "details": self.details,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "actor": self.actor,
            "notes": self.notes,
        }


def _read_records() -> List[ApprovalRecord]:
    records: List[ApprovalRecord] = []
    if not APPROVALS_PATH.exists():
        return records
    with APPROVALS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(
                    ApprovalRecord(
                        approval_id=data.get("approval_id") or data.get("id") or str(uuid.uuid4()),
                        summary=data.get("summary", ""),
                        details=data.get("details", ""),
                        status=data.get("status", "pending"),
                        created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                        updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                        metadata=data.get("metadata") or {},
                        actor=data.get("actor"),
                        notes=data.get("notes"),
                    )
                )
            except json.JSONDecodeError:
                continue
    return records


def _write_records(records: Iterable[ApprovalRecord]) -> None:
    with APPROVALS_PATH.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict()) + "\n")


def request_approval(summary: str, *, details: str = "", metadata: Optional[Dict[str, object]] = None) -> str:
    approval_id = str(uuid.uuid4())
    record = ApprovalRecord(
        approval_id=approval_id,
        summary=summary,
        details=details,
        metadata=metadata or {},
    )
    records = _read_records()
    records.append(record)
    _write_records(records)
    return approval_id


def list_requests(*, include_resolved: bool = False) -> List[ApprovalRecord]:
    records = _read_records()
    if include_resolved:
        return records
    return [r for r in records if r.status == "pending"]


def set_status(approval_id: str, status: str, *, actor: str, notes: str = "") -> bool:
    updated = False
    records = _read_records()
    now = datetime.now(timezone.utc).isoformat()
    for record in records:
        if record.approval_id == approval_id:
            record.status = status
            record.actor = actor
            record.notes = notes or record.notes
            record.updated_at = now
            updated = True
            break
    if updated:
        _write_records(records)
    return updated


__all__ = [
    "ApprovalRecord",
    "request_approval",
    "list_requests",
    "set_status",
]
