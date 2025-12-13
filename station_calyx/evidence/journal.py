#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evidence Journal - Append-only local evidence writer with hash chaining.

[CBO Governance]: The evidence journal is the authoritative local record
of all evidence captured by this node. It implements:
- Append-only semantics (no modification, no deletion)
- Automatic hash chaining (prev_hash from last written envelope)
- Monotonic sequence enforcement
- Directory organization by node_id

Writes EvidenceEnvelopeV1 to node-specific JSONL files at:
    logs/evidence/<node_id>/evidence.jsonl

Usage:
    from station_calyx.evidence import EvidenceJournal, append_evidence
    
    # Option 1: Use global singleton (recommended for most cases)
    append_evidence(evidence_type=EvidenceType.TELEMETRY_SNAPSHOT, payload={...})
    
    # Option 2: Create explicit journal instance
    journal = EvidenceJournal()
    journal.append(evidence_type=EvidenceType.TELEMETRY_SNAPSHOT, payload={...})
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schemas import EvidenceEnvelopeV1, EvidenceType
from ..node import get_node_identity, SequenceManager

ROOT = Path(__file__).resolve().parents[2]
JOURNAL_BASE = ROOT / "logs" / "evidence"


class EvidenceJournal:
    """
    Append-only evidence journal with hash chaining.

    [CBO Governance]: This class is the sole writer to the evidence journal.
    All writes are:
    - Atomic (via file append)
    - Chained (prev_hash linked to last envelope)
    - Sequenced (monotonic seq from SequenceManager)
    - Thread-safe (within single process)
    """
    
    def __init__(self, node_id: Optional[str] = None, base_dir: Optional[Path] = None):
        """
        Initialize evidence journal.
        
        Args:
            node_id: Node identifier (defaults to auto-detected from NodeIdentity)
            base_dir: Base directory for journals (default: logs/evidence)
        """
        self._identity = get_node_identity()
        self.node_id = node_id or self._identity.node_id
        self.base_dir = base_dir or JOURNAL_BASE
        self.journal_dir = self.base_dir / self.node_id
        self.journal_path = self.journal_dir / "evidence.jsonl"
        
        # Sequence and state management
        self.seq_manager = SequenceManager()
        self._lock = threading.Lock()
        self._last_hash: Optional[str] = None
        self._envelope_count: int = 0
        
        # Ensure directory exists
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        
        # Load last hash and count from journal
        self._load_journal_state()
    
    def _load_journal_state(self) -> None:
        """Load hash of last written envelope and count from journal."""
        if not self.journal_path.exists():
            self._last_hash = None
            self._envelope_count = 0
            return
        
        try:
            count = 0
            last_line = None
            
            with open(self.journal_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
                        count += 1
            
            self._envelope_count = count
            
            if last_line:
                last_envelope = json.loads(last_line)
                self._last_hash = last_envelope.get("envelope_hash")
        except Exception as e:
            print(f"[WARN] Failed to load journal state: {e}")
            self._last_hash = None
            self._envelope_count = 0
    
    def append(
        self,
        envelope: Optional[EvidenceEnvelopeV1] = None,
        evidence_type: Optional[EvidenceType] = None,
        payload: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> EvidenceEnvelopeV1:
        """
        Append evidence envelope to journal.

        [CBO Governance]: This is the ONLY method that writes to the journal.
        It guarantees hash chaining and sequence monotonicity.
        
        Args:
            envelope: Pre-constructed envelope (if provided, other args ignored
                     except prev_hash which is set automatically)
            evidence_type: Type of evidence (required if envelope not provided)
            payload: Evidence payload (required if envelope not provided)
            tags: Optional tags for categorization
            source: Optional source identifier
        
        Returns:
            Written envelope with computed hash
        
        Raises:
            ValueError: If neither envelope nor (evidence_type + payload) provided
        """
        with self._lock:
            if envelope is None:
                if evidence_type is None or payload is None:
                    raise ValueError("Must provide either envelope or (evidence_type + payload)")
                
                # Create new envelope with next sequence
                seq = self.seq_manager.next()
                envelope = EvidenceEnvelopeV1.create(
                    node_id=self.node_id,
                    seq=seq,
                    evidence_type=evidence_type,
                    payload=payload,
                    prev_hash=self._last_hash,
                    tags=tags or [],
                    source=source,
                )
            else:
                # Ensure envelope has prev_hash set for chaining
                if envelope.prev_hash is None and self._last_hash is not None:
                    envelope.prev_hash = self._last_hash
                    envelope.finalize()
            
            # Append to JSONL file (atomic line write)
            with open(self.journal_path, "a", encoding="utf-8") as f:
                f.write(envelope.to_json() + "\n")
            
            # Update state
            self._last_hash = envelope.envelope_hash
            self._envelope_count += 1
            
            return envelope
    
    def read_all(self) -> List[EvidenceEnvelopeV1]:
        """
        Read all envelopes from journal.
        
        Returns:
            List of envelopes in chronological order
        """
        if not self.journal_path.exists():
            return []
        
        envelopes = []
        with open(self.journal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        envelopes.append(EvidenceEnvelopeV1.from_json(line))
                    except Exception as e:
                        print(f"[WARN] Failed to parse envelope: {e}")
        
        return envelopes
    
    def read_since(self, after_seq: int) -> List[EvidenceEnvelopeV1]:
        """
        Read envelopes with seq > after_seq.
        
        Args:
            after_seq: Return envelopes with sequence greater than this
        
        Returns:
            List of envelopes after the given sequence
        """
        all_envelopes = self.read_all()
        return [e for e in all_envelopes if e.seq > after_seq]
    
    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify hash chain integrity.

        [CBO Governance]: Chain verification ensures no tampering or
        corruption has occurred. Run periodically or before export.

        Returns:
            (is_valid, error_message) - error_message is None if valid
        """
        envelopes = self.read_all()
        if not envelopes:
            return (True, None)
        
        prev_hash = None
        for i, envelope in enumerate(envelopes):
            # Check prev_hash linkage
            if envelope.prev_hash != prev_hash:
                return (False, f"Chain break at seq {envelope.seq}: expected prev_hash={prev_hash}, got {envelope.prev_hash}")
            
            # Verify envelope_hash computation
            if not envelope.verify():
                computed = envelope.compute_hash()
                return (False, f"Hash mismatch at seq {envelope.seq}: stored={envelope.envelope_hash}, computed={computed}")
            
            prev_hash = envelope.envelope_hash
        
        return (True, None)
    
    def count(self) -> int:
        """Return number of envelopes in journal."""
        return self._envelope_count
    
    def last_hash(self) -> Optional[str]:
        """Return hash of last written envelope."""
        return self._last_hash


# Global singleton instance
_global_journal: Optional[EvidenceJournal] = None
_journal_lock = threading.Lock()


def get_journal() -> EvidenceJournal:
    """Get or create global journal singleton."""
    global _global_journal
    
    with _journal_lock:
        if _global_journal is None:
            _global_journal = EvidenceJournal()
    
    return _global_journal


def append_evidence(
    evidence_type: EvidenceType,
    payload: Dict[str, Any],
    tags: Optional[List[str]] = None,
    source: Optional[str] = None,
) -> EvidenceEnvelopeV1:
    """
    Append evidence to global journal (convenience function).

    [CBO Governance]: Use this function for simple evidence appending.
    It uses the global singleton journal and handles all chaining automatically.
    
    Args:
        evidence_type: Type of evidence (from EvidenceType enum)
        payload: Evidence payload (arbitrary JSON-serializable dict)
        tags: Optional tags for categorization
        source: Optional source identifier
    
    Returns:
        Written envelope with computed hash
    """
    journal = get_journal()
    return journal.append(
        evidence_type=evidence_type,
        payload=payload,
        tags=tags,
        source=source,
    )


if __name__ == "__main__":
    # Test journal writing and verification
    import sys
    
    print("=== EvidenceJournal Test ===\n")
    
    journal = EvidenceJournal()
    print(f"Journal path: {journal.journal_path}")
    print(f"Node ID: {journal.node_id}")
    print(f"Initial count: {journal.count()}")
    
    # Write test envelopes
    print("\nWriting 5 test envelopes...")
    for i in range(5):
        envelope = journal.append(
            evidence_type=EvidenceType.METRIC_SAMPLE,
            payload={"test_iteration": i, "value": i * 10},
            tags=["test"],
            source="journal_test",
        )
        print(f"  Written: seq={envelope.seq}, hash={envelope.envelope_hash[:16]}...")
    
    print(f"\nFinal count: {journal.count()}")
    
    # Verify chain
    print("\nVerifying chain integrity...")
    is_valid, error = journal.verify_chain()
    if is_valid:
        print("? Chain verification PASSED")
    else:
        print(f"? Chain verification FAILED: {error}")
        sys.exit(1)
    
    # Read back and show summary
    envelopes = journal.read_all()
    print(f"\nRead {len(envelopes)} envelopes from journal")
    
    if len(envelopes) >= 2:
        print(f"\nChain linkage check:")
        print(f"  env[0].hash: {envelopes[0].envelope_hash[:16]}...")
        print(f"  env[1].prev_hash: {envelopes[1].prev_hash[:16] if envelopes[1].prev_hash else 'None'}...")
        print(f"  Match: {envelopes[0].envelope_hash == envelopes[1].prev_hash}")
