"""Work Envelope: CBO-minted execution envelope with canonical serialization and deterministic hashing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class WorkEnvelope:
    """
    The only envelope type that may trigger execution. Minted solely by CBO from a clarified Intent Artifact.
    """
    envelope_id: str
    intent_id: str
    task_type: str
    scope: dict[str, Any]
    constraints: dict[str, Any]
    ts_utc: str
    source: str
    requires_human_approval: bool
    approval_token: str | None
    risk_tier: str = "low"
    critique_checkpoint: dict[str, Any] = field(default_factory=dict)

    def to_canonical_dict(self) -> dict[str, Any]:
        """Stable key order for deterministic serialization."""
        payload = {
            "envelope_id": self.envelope_id,
            "intent_id": self.intent_id,
            "task_type": self.task_type,
            "scope": self.scope,
            "constraints": self.constraints,
            "ts_utc": self.ts_utc,
            "source": self.source,
            "requires_human_approval": self.requires_human_approval,
            "approval_token": self.approval_token,
            "risk_tier": self.risk_tier,
        }
        if self.critique_checkpoint:
            payload["critique_checkpoint"] = self.critique_checkpoint
        return payload

    def to_canonical_json(self) -> bytes:
        """Canonical JSON (sorted keys, no whitespace)."""
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def deterministic_hash(self) -> str:
        """SHA256 of canonical JSON. Same envelope -> same hash."""
        return hashlib.sha256(self.to_canonical_json()).hexdigest()

    def has_swarm_extensions(self) -> bool:
        """Return True when governed swarm extension fields are present."""
        return "swarm" in (self.scope or {}) or "swarm" in (self.constraints or {})

    def validate_swarm_extensions(self) -> tuple[bool, list[str]]:
        """Validate governed swarm extension fields if present."""
        from .swarm_work_envelope import validate_swarm_extensions

        return validate_swarm_extensions(self.scope or {}, self.constraints or {})

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkEnvelope:
        return cls(
            envelope_id=d["envelope_id"],
            intent_id=d["intent_id"],
            task_type=d["task_type"],
            scope=d.get("scope") or {},
            constraints=d.get("constraints") or {},
            ts_utc=d["ts_utc"],
            source=d.get("source", "discord"),
            requires_human_approval=d.get("requires_human_approval", False),
            approval_token=d.get("approval_token"),
            risk_tier=d.get("risk_tier", "low"),
            critique_checkpoint=d.get("critique_checkpoint") or {},
        )
