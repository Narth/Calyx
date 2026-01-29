# -*- coding: utf-8 -*-
"""
Evidence Envelope Schema v1
===========================

Shared contract for Node Evidence Relay.

PURPOSE:
- Define the evidence envelope structure for inter-node relay
- Provide deterministic serialization for hash verification
- Enable tamper-evident, append-only evidence exchange

CONSTRAINTS (NON-NEGOTIABLE):
- Advisory-only: No execution authority
- Deterministic logic only
- Append-only evidence storage
- No LLM usage in this layer
- No implied "control" of another node
- Receiver must verify envelope integrity before ingesting

ENVELOPE FIELDS:
- envelope_version: Schema version identifier
- node_id: Unique identifier for the originating node
- node_name: Human-readable node name (optional)
- captured_at_iso: ISO8601 timestamp of capture
- seq: Monotonic sequence number per node
- event_type: Type of event (SYSTEM_SNAPSHOT, etc.)
- payload: The actual event data
- payload_hash: SHA256 of canonical JSON payload
- prev_hash: Hash of previous envelope's envelope_hash (null if first)
- envelope_hash: SHA256 of this envelope (for chain linking)
- signature: Cryptographic signature (null in v0)
- collector_version: Version of collecting software

HASH CHAIN SEMANTICS:
- envelope_hash is computed from CHAIN_HASH_FIELDS only (deterministic)
- prev_hash must equal the previous envelope's envelope_hash
- payload_hash is an additional integrity check (not chain anchor)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


ENVELOPE_VERSION = "v1"

# Fields included in envelope_hash computation (deterministic, non-ephemeral)
# Order matters for documentation but canonical_json sorts alphabetically
CHAIN_HASH_FIELDS = [
    "envelope_version",
    "node_id",
    "node_name",
    "captured_at_iso",
    "seq",
    "event_type",
    "payload",
    "payload_hash",
    "prev_hash",
    "collector_version",
]

# Fields EXCLUDED from envelope_hash (ephemeral or computed)
EXCLUDED_FROM_HASH = [
    "envelope_hash",  # Self-referential, cannot include
    "signature",      # Added after hash computation
]


@dataclass
class EvidenceEnvelopeV1:
    """
    Evidence envelope for inter-node relay.
    
    This is the canonical structure for evidence exchange between Station Calyx nodes.
    All fields are immutable after creation.
    
    CHAIN SEMANTICS:
    - envelope_hash = sha256(canonical_json(chain_fields))
    - prev_hash = previous envelope's envelope_hash
    """
    
    # Required fields
    envelope_version: str
    node_id: str
    captured_at_iso: str
    seq: int
    event_type: str
    payload: dict[str, Any]
    payload_hash: str
    collector_version: str
    
    # Optional fields
    node_name: Optional[str] = None
    prev_hash: Optional[str] = None
    envelope_hash: Optional[str] = None  # Computed, included in serialization
    signature: Optional[str] = None  # Reserved for v1 signing
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)
    
    def to_canonical_json(self) -> str:
        """
        Serialize to canonical JSON for hashing/signing.
        
        Canonical form ensures deterministic output:
        - Keys sorted alphabetically
        - No whitespace
        - ASCII-safe encoding
        """
        return canonical_json(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceEnvelopeV1":
        """Create envelope from dictionary."""
        return cls(
            envelope_version=data["envelope_version"],
            node_id=data["node_id"],
            node_name=data.get("node_name"),
            captured_at_iso=data["captured_at_iso"],
            seq=data["seq"],
            event_type=data["event_type"],
            payload=data["payload"],
            payload_hash=data["payload_hash"],
            prev_hash=data.get("prev_hash"),
            envelope_hash=data.get("envelope_hash"),
            signature=data.get("signature"),
            collector_version=data["collector_version"],
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "EvidenceEnvelopeV1":
        """Create envelope from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def verify_payload_hash(self) -> bool:
        """Verify that payload_hash matches computed hash of payload."""
        computed = compute_payload_hash(self.payload)
        return computed == self.payload_hash
    
    def compute_envelope_hash(self) -> str:
        """
        Compute canonical envelope_hash for chain linking.
        
        INCLUDES: All fields in CHAIN_HASH_FIELDS
        EXCLUDES: envelope_hash (self), signature (ephemeral)
        
        This is the canonical chain anchor used for prev_hash linking.
        """
        return compute_envelope_hash_from_dict(self.to_dict())
    
    def verify_envelope_hash(self) -> bool:
        """
        Verify that envelope_hash matches computed value.
        
        Returns True if:
        - envelope_hash is None (legacy, will be computed)
        - envelope_hash matches computed value
        """
        if self.envelope_hash is None:
            return True  # Legacy envelope, hash will be computed
        computed = self.compute_envelope_hash()
        return computed == self.envelope_hash
    
    def get_chain_hash(self) -> str:
        """
        Get the hash to use for chain linking.
        
        If envelope_hash is set and valid, use it.
        Otherwise compute it.
        """
        if self.envelope_hash and self.verify_envelope_hash():
            return self.envelope_hash
        return self.compute_envelope_hash()


def canonical_json(obj: Any) -> str:
    """
    Serialize object to canonical JSON.
    
    Properties:
    - Keys sorted alphabetically (recursive)
    - No whitespace between elements
    - Consistent float representation
    - ASCII-safe (non-ASCII escaped)
    
    This ensures the same logical data always produces the same byte sequence,
    which is required for deterministic hashing.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,  # Handle datetime, Path, etc.
    )


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """
    Compute SHA256 hash of payload using canonical JSON.
    
    Args:
        payload: The event payload dictionary
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    canonical = canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_envelope_hash_from_dict(envelope_dict: dict[str, Any]) -> str:
    """
    Compute canonical envelope_hash from dictionary.
    
    This is the authoritative hash computation used for chain linking.
    
    INCLUDES: All fields in CHAIN_HASH_FIELDS
    EXCLUDES: envelope_hash, signature
    
    Args:
        envelope_dict: Envelope as dictionary
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    # Build hash input with only chain fields
    hash_input = {}
    for field in CHAIN_HASH_FIELDS:
        if field in envelope_dict:
            hash_input[field] = envelope_dict[field]
    
    # Compute hash
    canonical = canonical_json(hash_input)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_envelope(
    node_id: str,
    seq: int,
    event_type: str,
    payload: dict[str, Any],
    collector_version: str,
    node_name: Optional[str] = None,
    prev_hash: Optional[str] = None,
    captured_at: Optional[datetime] = None,
) -> EvidenceEnvelopeV1:
    """
    Create a new evidence envelope with computed hashes.
    
    Args:
        node_id: Unique identifier for this node
        seq: Monotonic sequence number (must increment per node)
        event_type: Type of event being wrapped
        payload: The actual event data
        collector_version: Version of the collecting software
        node_name: Optional human-readable node name
        prev_hash: envelope_hash of previous envelope (for chain integrity)
        captured_at: Capture timestamp (defaults to now)
        
    Returns:
        New EvidenceEnvelopeV1 instance with computed envelope_hash
    """
    if captured_at is None:
        captured_at = datetime.now(timezone.utc)
    
    payload_hash = compute_payload_hash(payload)
    
    # Create envelope without envelope_hash first
    envelope = EvidenceEnvelopeV1(
        envelope_version=ENVELOPE_VERSION,
        node_id=node_id,
        node_name=node_name,
        captured_at_iso=captured_at.isoformat(),
        seq=seq,
        event_type=event_type,
        payload=payload,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        envelope_hash=None,
        signature=None,
        collector_version=collector_version,
    )
    
    # Compute and set envelope_hash
    envelope.envelope_hash = envelope.compute_envelope_hash()
    
    return envelope


def validate_envelope(envelope: EvidenceEnvelopeV1) -> tuple[bool, list[str]]:
    """
    Validate an evidence envelope.
    
    Checks:
    - Required fields present
    - Envelope version is supported
    - Payload hash matches
    - Envelope hash matches (if present)
    - Sequence is non-negative
    - Timestamp is valid ISO8601
    
    Args:
        envelope: The envelope to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Version check
    if envelope.envelope_version != ENVELOPE_VERSION:
        errors.append(f"Unsupported envelope version: {envelope.envelope_version}")
    
    # Required field checks
    if not envelope.node_id:
        errors.append("Missing required field: node_id")
    
    if not envelope.captured_at_iso:
        errors.append("Missing required field: captured_at_iso")
    
    if envelope.seq < 0:
        errors.append(f"Invalid sequence number: {envelope.seq} (must be >= 0)")
    
    if not envelope.event_type:
        errors.append("Missing required field: event_type")
    
    if not envelope.payload_hash:
        errors.append("Missing required field: payload_hash")
    
    if not envelope.collector_version:
        errors.append("Missing required field: collector_version")
    
    # Payload hash verification
    if envelope.payload_hash:
        if not envelope.verify_payload_hash():
            errors.append("Payload hash mismatch: envelope may be tampered")
    
    # Envelope hash verification (if present)
    if envelope.envelope_hash:
        if not envelope.verify_envelope_hash():
            errors.append("Envelope hash mismatch: envelope may be tampered")
    
    # Timestamp validation
    if envelope.captured_at_iso:
        try:
            datetime.fromisoformat(envelope.captured_at_iso.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"Invalid timestamp format: {envelope.captured_at_iso}")
    
    return (len(errors) == 0, errors)


def validate_chain(envelopes: list[EvidenceEnvelopeV1]) -> tuple[bool, list[str]]:
    """
    Validate a chain of evidence envelopes.
    
    Checks:
    - Each envelope is individually valid
    - Sequence numbers are monotonically increasing
    - prev_hash links match envelope_hash chain
    - All envelopes are from the same node
    
    Args:
        envelopes: List of envelopes in sequence order
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not envelopes:
        return (True, [])
    
    # Check each envelope
    for i, env in enumerate(envelopes):
        valid, env_errors = validate_envelope(env)
        if not valid:
            errors.extend([f"Envelope {i}: {e}" for e in env_errors])
    
    # Check node consistency
    node_ids = set(e.node_id for e in envelopes)
    if len(node_ids) > 1:
        errors.append(f"Chain contains multiple node_ids: {node_ids}")
    
    # Check sequence monotonicity
    for i in range(1, len(envelopes)):
        if envelopes[i].seq <= envelopes[i-1].seq:
            errors.append(
                f"Non-monotonic sequence at index {i}: "
                f"{envelopes[i-1].seq} -> {envelopes[i].seq}"
            )
    
    # Check hash chain integrity using envelope_hash
    for i in range(1, len(envelopes)):
        expected_prev = envelopes[i-1].get_chain_hash()
        actual_prev = envelopes[i].prev_hash
        
        if actual_prev != expected_prev:
            errors.append(
                f"Hash chain broken at index {i}: "
                f"expected prev_hash {expected_prev[:16]}..., "
                f"got {actual_prev[:16] if actual_prev else 'null'}..."
            )
    
    return (len(errors) == 0, errors)


# Required fields for schema validation
REQUIRED_FIELDS = [
    "envelope_version",
    "node_id",
    "captured_at_iso",
    "seq",
    "event_type",
    "payload",
    "payload_hash",
    "collector_version",
]

OPTIONAL_FIELDS = [
    "node_name",
    "prev_hash",
    "envelope_hash",
    "signature",
]


if __name__ == "__main__":
    # Quick demonstration
    print("Evidence Envelope Schema v1")
    print("=" * 40)
    print(f"Required fields: {REQUIRED_FIELDS}")
    print(f"Optional fields: {OPTIONAL_FIELDS}")
    print(f"Chain hash fields: {CHAIN_HASH_FIELDS}")
    print()
    
    # Create sample envelope
    sample_payload = {"cpu_percent": 25.5, "memory_percent": 42.0}
    envelope = create_envelope(
        node_id="node-001",
        seq=1,
        event_type="SYSTEM_SNAPSHOT",
        payload=sample_payload,
        collector_version="v1.7.0",
        node_name="Laptop-Observer",
    )
    
    print("Sample envelope:")
    print(json.dumps(envelope.to_dict(), indent=2))
    print()
    print(f"Payload hash: {envelope.payload_hash}")
    print(f"Envelope hash: {envelope.envelope_hash}")
    print(f"Computed hash: {envelope.compute_envelope_hash()}")
    print(f"Hash match: {envelope.verify_envelope_hash()}")
    print(f"Valid: {validate_envelope(envelope)}")
