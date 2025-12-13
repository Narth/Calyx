#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evidence Envelope Schema - Shared schema for Node Evidence Relay v0.

[CBO Governance]: EvidenceEnvelopeV1 is the canonical format for evidence
across all Station Calyx nodes. It provides:
- Deterministic hash computation (SHA-256)
- Chain integrity via prev_hash linkage
- Node attribution via node_id
- Temporal ordering via monotonic seq

The schema is designed to be:
- Serializable to single-line JSON (JSONL compatible)
- Verifiable (hash can be recomputed from content)
- Chain-able (prev_hash creates linked list)

Usage:
    from station_calyx.evidence import EvidenceEnvelopeV1, EvidenceType
    
    envelope = EvidenceEnvelopeV1.create(
        node_id="node_calyx_a3f8c2d1",
        seq=42,
        evidence_type=EvidenceType.TELEMETRY_SNAPSHOT,
        payload={"agents": {...}, "drift": {...}},
        prev_hash="abc123...",
        tags=["telemetry", "agent_health"]
    )
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceType(Enum):
    """
    Evidence types for Node Evidence Relay.

    [CBO Governance]: New evidence types should be added here as the
    system evolves. Each type should have clear semantics for what
    payload structure is expected.
    """
    
    TELEMETRY_SNAPSHOT = "telemetry_snapshot"
    AGENT_HEARTBEAT = "agent_heartbeat"
    SYSTEM_EVENT = "system_event"
    AUDIT_LOG = "audit_log"
    TASK_COMPLETION = "task_completion"
    METRIC_SAMPLE = "metric_sample"
    ERROR_TRACE = "error_trace"
    CBO_DIRECTIVE = "cbo_directive"
    CHAIN_ANCHOR = "chain_anchor"  # Genesis/checkpoint envelopes


@dataclass
class EvidenceEnvelopeV1:
    """
    Evidence envelope schema v1.

    [CBO Governance]: This is the immutable truth format for Station Calyx.
    Once written, envelopes are NEVER modified. Chain integrity is maintained
    via prev_hash linkage and envelope_hash verification.

    Hash computation covers: node_id, seq, timestamp, evidence_type, payload, prev_hash
    (excludes envelope_hash to avoid circular dependency)
    """
    
    # Identity & ordering
    node_id: str
    seq: int
    timestamp: str  # ISO 8601 format
    
    # Evidence content
    evidence_type: str  # EvidenceType value
    payload: Dict[str, Any]
    
    # Chain integrity
    prev_hash: Optional[str] = None
    envelope_hash: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None  # e.g., "compute_telemetry", "agent_scheduler"
    version: str = "v1"
    
    def compute_hash(self) -> str:
        """
        Compute deterministic SHA-256 hash of envelope content.

        [CBO Governance]: Hash computation is DETERMINISTIC and covers
        all content fields except envelope_hash itself. This allows
        verification by recomputing the hash from stored data.
        """
        hash_input = {
            "node_id": self.node_id,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "evidence_type": self.evidence_type,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }
        
        # Deterministic JSON serialization (sorted keys, minimal separators)
        canonical = json.dumps(hash_input, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    def finalize(self) -> EvidenceEnvelopeV1:
        """
        Compute and set envelope_hash.

        [CBO Governance]: Call this before writing to journal.
        After finalization, the envelope should be treated as immutable.
        """
        self.envelope_hash = self.compute_hash()
        return self
    
    def verify(self) -> bool:
        """
        Verify envelope_hash matches recomputed hash.
        
        Returns:
            True if hash is valid, False if tampered or corrupted
        """
        if self.envelope_hash is None:
            return False
        return self.envelope_hash == self.compute_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "evidence_type": self.evidence_type,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "envelope_hash": self.envelope_hash,
            "tags": self.tags,
            "source": self.source,
            "version": self.version,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string (one-line for JSONL)."""
        return json.dumps(self.to_dict(), separators=(",", ":"))
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceEnvelopeV1:
        """Deserialize from dictionary."""
        return cls(
            node_id=data["node_id"],
            seq=data["seq"],
            timestamp=data["timestamp"],
            evidence_type=data["evidence_type"],
            payload=data["payload"],
            prev_hash=data.get("prev_hash"),
            envelope_hash=data.get("envelope_hash"),
            tags=data.get("tags", []),
            source=data.get("source"),
            version=data.get("version", "v1"),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> EvidenceEnvelopeV1:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def create(
        cls,
        node_id: str,
        seq: int,
        evidence_type: EvidenceType,
        payload: Dict[str, Any],
        prev_hash: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> EvidenceEnvelopeV1:
        """
        Factory method for creating finalized envelopes.

        [CBO Governance]: Use this method for all envelope creation.
        It ensures proper finalization (hash computation) before return.
        
        Args:
            node_id: Node identifier (from NodeIdentity)
            seq: Monotonic sequence number (from SequenceManager)
            evidence_type: Type of evidence (from EvidenceType enum)
            payload: Evidence payload data (arbitrary JSON-serializable dict)
            prev_hash: Hash of previous envelope (for chaining)
            tags: Optional tags for categorization
            source: Optional source identifier (e.g., script name)
            timestamp: Optional explicit timestamp (defaults to now)
        
        Returns:
            Finalized EvidenceEnvelopeV1 with computed hash
        """
        envelope = cls(
            node_id=node_id,
            seq=seq,
            timestamp=timestamp or datetime.now().isoformat(),
            evidence_type=evidence_type.value if isinstance(evidence_type, EvidenceType) else evidence_type,
            payload=payload,
            prev_hash=prev_hash,
            tags=tags or [],
            source=source,
        )
        return envelope.finalize()
    
    @classmethod
    def create_anchor(
        cls,
        node_id: str,
        seq: int,
        message: str = "Chain anchor - genesis envelope",
        prev_hash: Optional[str] = None,
    ) -> EvidenceEnvelopeV1:
        """
        Create a chain anchor envelope (genesis or checkpoint).

        [CBO Governance]: Anchors establish chain starting points or
        checkpoints for verification. Use sparingly.
        """
        return cls.create(
            node_id=node_id,
            seq=seq,
            evidence_type=EvidenceType.CHAIN_ANCHOR,
            payload={"message": message, "anchor_type": "genesis" if prev_hash is None else "checkpoint"},
            prev_hash=prev_hash,
            tags=["anchor", "chain"],
            source="cbo_governance",
        )


if __name__ == "__main__":
    # Test envelope creation and serialization
    print("=== EvidenceEnvelopeV1 Test ===\n")
    
    # Create first envelope (genesis - no prev_hash)
    env1 = EvidenceEnvelopeV1.create(
        node_id="node_calyx_test1234",
        seq=1,
        evidence_type=EvidenceType.TELEMETRY_SNAPSHOT,
        payload={"active_count": 5, "drift": {"latest": 0.42}},
        tags=["test", "telemetry"],
        source="test_script",
    )
    
    print(f"Envelope 1 (genesis):")
    print(f"  seq: {env1.seq}")
    print(f"  hash: {env1.envelope_hash}")
    print(f"  prev_hash: {env1.prev_hash}")
    print(f"  verify: {env1.verify()}")
    
    # Create chained envelope
    env2 = EvidenceEnvelopeV1.create(
        node_id="node_calyx_test1234",
        seq=2,
        evidence_type=EvidenceType.AGENT_HEARTBEAT,
        payload={"agent": "agent1", "status": "running"},
        prev_hash=env1.envelope_hash,
        tags=["test", "heartbeat"],
        source="test_script",
    )
    
    print(f"\nEnvelope 2 (chained):")
    print(f"  seq: {env2.seq}")
    print(f"  hash: {env2.envelope_hash}")
    print(f"  prev_hash: {env2.prev_hash}")
    print(f"  chain valid: {env2.prev_hash == env1.envelope_hash}")
    
    # Show JSON format
    print(f"\nJSON (truncated):")
    json_str = env2.to_json()
    print(f"  {json_str[:100]}...")
