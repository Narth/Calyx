# -*- coding: utf-8 -*-
"""
Unit Tests for Evidence Envelope Schema v1
==========================================

Tests:
1. Deterministic hashing (same payload => same hash)
2. Schema required fields validation
3. Chain integrity validation
4. Envelope creation and serialization
"""

import json
import pytest
from datetime import datetime, timezone

from station_calyx.schemas.evidence_envelope_v1 import (
    EvidenceEnvelopeV1,
    ENVELOPE_VERSION,
    REQUIRED_FIELDS,
    canonical_json,
    compute_payload_hash,
    create_envelope,
    validate_envelope,
    validate_chain,
)


class TestCanonicalJson:
    """Tests for deterministic JSON serialization."""
    
    def test_same_dict_same_output(self):
        """Same dictionary always produces same JSON string."""
        payload = {"cpu": 25.5, "memory": 42.0, "disk": 88.6}
        
        result1 = canonical_json(payload)
        result2 = canonical_json(payload)
        
        assert result1 == result2
    
    def test_key_order_independent(self):
        """Key order in input dict doesn't affect output."""
        payload1 = {"a": 1, "b": 2, "c": 3}
        payload2 = {"c": 3, "a": 1, "b": 2}
        payload3 = {"b": 2, "c": 3, "a": 1}
        
        result1 = canonical_json(payload1)
        result2 = canonical_json(payload2)
        result3 = canonical_json(payload3)
        
        assert result1 == result2 == result3
    
    def test_nested_dict_sorted(self):
        """Nested dictionaries are also sorted."""
        payload = {
            "outer_z": {"inner_b": 2, "inner_a": 1},
            "outer_a": {"inner_y": 4, "inner_x": 3}
        }
        
        result = canonical_json(payload)
        
        # Keys should appear in alphabetical order
        assert result.index('"outer_a"') < result.index('"outer_z"')
        assert result.index('"inner_x"') < result.index('"inner_y"')
    
    def test_no_whitespace(self):
        """Output has no unnecessary whitespace."""
        payload = {"key": "value", "number": 42}
        
        result = canonical_json(payload)
        
        assert " " not in result
        assert "\n" not in result
        assert "\t" not in result
    
    def test_ascii_safe(self):
        """Non-ASCII characters are escaped."""
        # Use unicode escapes to avoid encoding issues
        payload = {"message": "H\u00e9llo W\u00f6rld \u65e5\u672c\u8a9e"}
        
        result = canonical_json(payload)
        
        # Should be pure ASCII
        assert result.isascii()


class TestPayloadHash:
    """Tests for deterministic payload hashing."""
    
    def test_same_payload_same_hash(self):
        """Identical payloads produce identical hashes."""
        payload = {"cpu_percent": 25.5, "memory_percent": 42.0}
        
        hash1 = compute_payload_hash(payload)
        hash2 = compute_payload_hash(payload)
        
        assert hash1 == hash2
    
    def test_different_payload_different_hash(self):
        """Different payloads produce different hashes."""
        payload1 = {"cpu_percent": 25.5}
        payload2 = {"cpu_percent": 25.6}
        
        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)
        
        assert hash1 != hash2
    
    def test_key_order_same_hash(self):
        """Same data with different key order produces same hash."""
        payload1 = {"a": 1, "b": 2}
        payload2 = {"b": 2, "a": 1}
        
        hash1 = compute_payload_hash(payload1)
        hash2 = compute_payload_hash(payload2)
        
        assert hash1 == hash2
    
    def test_hash_is_sha256_hex(self):
        """Hash is a 64-character hexadecimal string (SHA256)."""
        payload = {"test": "data"}
        
        hash_result = compute_payload_hash(payload)
        
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)
    
    def test_empty_payload_has_hash(self):
        """Empty payload still produces a valid hash."""
        payload = {}
        
        hash_result = compute_payload_hash(payload)
        
        assert len(hash_result) == 64


class TestEnvelopeCreation:
    """Tests for envelope creation."""
    
    def test_create_minimal_envelope(self):
        """Create envelope with minimum required fields."""
        envelope = create_envelope(
            node_id="test-node-001",
            seq=0,
            event_type="SYSTEM_SNAPSHOT",
            payload={"cpu": 25.0},
            collector_version="v1.0.0",
        )
        
        assert envelope.envelope_version == ENVELOPE_VERSION
        assert envelope.node_id == "test-node-001"
        assert envelope.seq == 0
        assert envelope.event_type == "SYSTEM_SNAPSHOT"
        assert envelope.payload == {"cpu": 25.0}
        assert envelope.collector_version == "v1.0.0"
        assert envelope.payload_hash is not None
        assert envelope.prev_hash is None
        assert envelope.signature is None
    
    def test_create_envelope_with_optional_fields(self):
        """Create envelope with all optional fields."""
        envelope = create_envelope(
            node_id="test-node-001",
            seq=1,
            event_type="SYSTEM_SNAPSHOT",
            payload={"cpu": 25.0},
            collector_version="v1.0.0",
            node_name="Test Node",
            prev_hash="abc123",
        )
        
        assert envelope.node_name == "Test Node"
        assert envelope.prev_hash == "abc123"
    
    def test_payload_hash_computed_correctly(self):
        """Payload hash matches expected computation."""
        payload = {"cpu": 25.0, "memory": 42.0}
        
        envelope = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload=payload,
            collector_version="v1.0.0",
        )
        
        expected_hash = compute_payload_hash(payload)
        assert envelope.payload_hash == expected_hash
    
    def test_verify_payload_hash_success(self):
        """Payload hash verification succeeds for valid envelope."""
        envelope = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"data": "test"},
            collector_version="v1.0.0",
        )
        
        assert envelope.verify_payload_hash() is True
    
    def test_verify_payload_hash_failure(self):
        """Payload hash verification fails for tampered envelope."""
        envelope = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"data": "test"},
            collector_version="v1.0.0",
        )
        
        # Tamper with payload
        envelope.payload["data"] = "tampered"
        
        assert envelope.verify_payload_hash() is False


class TestEnvelopeSerialization:
    """Tests for envelope serialization."""
    
    def test_to_dict_roundtrip(self):
        """Envelope survives dict roundtrip."""
        original = create_envelope(
            node_id="test-node",
            seq=5,
            event_type="SNAPSHOT",
            payload={"x": 1},
            collector_version="v1.0.0",
            node_name="Test",
        )
        
        dict_form = original.to_dict()
        restored = EvidenceEnvelopeV1.from_dict(dict_form)
        
        assert restored.node_id == original.node_id
        assert restored.seq == original.seq
        assert restored.payload == original.payload
        assert restored.payload_hash == original.payload_hash
    
    def test_to_json_roundtrip(self):
        """Envelope survives JSON roundtrip."""
        original = create_envelope(
            node_id="test-node",
            seq=10,
            event_type="TEST",
            payload={"nested": {"data": [1, 2, 3]}},
            collector_version="v1.0.0",
        )
        
        json_str = original.to_canonical_json()
        dict_form = json.loads(json_str)
        restored = EvidenceEnvelopeV1.from_dict(dict_form)
        
        assert restored.payload == original.payload


class TestEnvelopeValidation:
    """Tests for envelope validation."""
    
    def test_valid_envelope_passes(self):
        """Valid envelope passes validation."""
        envelope = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"data": 1},
            collector_version="v1.0.0",
        )
        
        is_valid, errors = validate_envelope(envelope)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_node_id_fails(self):
        """Envelope with missing node_id fails validation."""
        envelope = create_envelope(
            node_id="",  # Empty
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        is_valid, errors = validate_envelope(envelope)
        
        assert is_valid is False
        assert any("node_id" in e for e in errors)
    
    def test_negative_seq_fails(self):
        """Envelope with negative seq fails validation."""
        envelope = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        envelope.seq = -1
        
        is_valid, errors = validate_envelope(envelope)
        
        assert is_valid is False
        assert any("sequence" in e.lower() for e in errors)
    
    def test_tampered_payload_fails(self):
        """Envelope with tampered payload fails validation."""
        envelope = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={"original": True},
            collector_version="v1.0.0",
        )
        
        # Tamper
        envelope.payload["original"] = False
        
        is_valid, errors = validate_envelope(envelope)
        
        assert is_valid is False
        assert any("hash" in e.lower() or "tamper" in e.lower() for e in errors)


class TestChainValidation:
    """Tests for chain validation."""
    
    def test_valid_chain_passes(self):
        """Valid chain of envelopes passes validation."""
        env0 = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"seq": 0},
            collector_version="v1.0.0",
            prev_hash=None,
        )
        
        env1 = create_envelope(
            node_id="test-node",
            seq=1,
            event_type="TEST",
            payload={"seq": 1},
            collector_version="v1.0.0",
            prev_hash=env0.compute_envelope_hash(),
        )
        
        env2 = create_envelope(
            node_id="test-node",
            seq=2,
            event_type="TEST",
            payload={"seq": 2},
            collector_version="v1.0.0",
            prev_hash=env1.compute_envelope_hash(),
        )
        
        is_valid, errors = validate_chain([env0, env1, env2])
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_non_monotonic_seq_fails(self):
        """Chain with non-monotonic seq fails validation."""
        env0 = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        env1 = create_envelope(
            node_id="test-node",
            seq=0,  # Same as env0 - not monotonic!
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash=env0.compute_envelope_hash(),
        )
        
        is_valid, errors = validate_chain([env0, env1])
        
        assert is_valid is False
        assert any("monotonic" in e.lower() for e in errors)
    
    def test_broken_hash_chain_fails(self):
        """Chain with broken hash link fails validation."""
        env0 = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        env1 = create_envelope(
            node_id="test-node",
            seq=1,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash="wrong_hash",  # Invalid!
        )
        
        is_valid, errors = validate_chain([env0, env1])
        
        assert is_valid is False
        assert any("chain" in e.lower() or "hash" in e.lower() for e in errors)
    
    def test_mixed_nodes_fails(self):
        """Chain with multiple node_ids fails validation."""
        env0 = create_envelope(
            node_id="node-A",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        env1 = create_envelope(
            node_id="node-B",  # Different node!
            seq=1,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash=env0.compute_envelope_hash(),
        )
        
        is_valid, errors = validate_chain([env0, env1])
        
        assert is_valid is False
        assert any("node_id" in e.lower() for e in errors)
    
    def test_empty_chain_valid(self):
        """Empty chain is valid."""
        is_valid, errors = validate_chain([])
        
        assert is_valid is True
        assert len(errors) == 0


class TestRequiredFields:
    """Tests for schema field requirements."""
    
    def test_required_fields_defined(self):
        """All required fields are defined in schema."""
        expected = [
            "envelope_version",
            "node_id",
            "captured_at_iso",
            "seq",
            "event_type",
            "payload",
            "payload_hash",
            "collector_version",
        ]
        
        assert set(REQUIRED_FIELDS) == set(expected)
    
    def test_envelope_has_all_required_fields(self):
        """Created envelope has all required fields."""
        envelope = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        envelope_dict = envelope.to_dict()
        
        for field in REQUIRED_FIELDS:
            assert field in envelope_dict, f"Missing required field: {field}"
            assert envelope_dict[field] is not None, f"Required field is None: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
