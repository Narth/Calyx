# -*- coding: utf-8 -*-
"""
Hash Chain Alignment Tests
==========================

Tests for canonical envelope_hash chain validation.

Covers:
1. Envelope hash stable across environments
2. Chain creation with correct prev_hash linking
3. Multi-envelope chain acceptance
4. Broken chain rejection
5. Regression: "first accepted, subsequent rejected" scenario
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone

from station_calyx.schemas.evidence_envelope_v1 import (
    EvidenceEnvelopeV1,
    create_envelope,
    validate_envelope,
    validate_chain,
    compute_payload_hash,
    compute_envelope_hash_from_dict,
    canonical_json,
    CHAIN_HASH_FIELDS,
)


class TestCanonicalJson:
    """Test deterministic JSON serialization."""
    
    def test_sorted_keys(self):
        """Keys are sorted alphabetically."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(obj)
        assert result == '{"a":2,"m":3,"z":1}'
    
    def test_no_whitespace(self):
        """No whitespace in output."""
        obj = {"key": "value", "list": [1, 2, 3]}
        result = canonical_json(obj)
        assert " " not in result
        assert "\n" not in result
    
    def test_nested_sorted(self):
        """Nested objects also sorted."""
        obj = {"outer": {"z": 1, "a": 2}}
        result = canonical_json(obj)
        assert result == '{"outer":{"a":2,"z":1}}'
    
    def test_stable_across_calls(self):
        """Same input produces same output."""
        obj = {"cpu": 25.5, "memory": {"used": 1024, "free": 2048}}
        result1 = canonical_json(obj)
        result2 = canonical_json(obj)
        assert result1 == result2


class TestEnvelopeHash:
    """Test envelope hash computation."""
    
    def test_envelope_hash_computed(self):
        """create_envelope computes envelope_hash."""
        env = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"data": "test"},
            collector_version="v1.7.0",
        )
        assert env.envelope_hash is not None
        assert len(env.envelope_hash) == 64  # SHA256 hex
    
    def test_envelope_hash_stable(self):
        """Same envelope produces same hash."""
        payload = {"cpu": 25.5, "memory": 42.0}
        
        env1 = create_envelope(
            node_id="stable-test",
            seq=0,
            event_type="SNAPSHOT",
            payload=payload,
            collector_version="v1.7.0",
            captured_at=datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        env2 = create_envelope(
            node_id="stable-test",
            seq=0,
            event_type="SNAPSHOT",
            payload=payload,
            collector_version="v1.7.0",
            captured_at=datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
        )
        
        assert env1.envelope_hash == env2.envelope_hash
    
    def test_envelope_hash_excludes_self(self):
        """envelope_hash does not include itself in computation."""
        env = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        # Manually compute from dict without envelope_hash
        d = env.to_dict()
        del d["envelope_hash"]
        del d["signature"]
        
        manual_hash = compute_envelope_hash_from_dict(d)
        assert env.envelope_hash == manual_hash
    
    def test_verify_envelope_hash(self):
        """verify_envelope_hash returns True for valid hash."""
        env = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={"key": "value"},
            collector_version="v1.0.0",
        )
        
        assert env.verify_envelope_hash() is True
    
    def test_verify_envelope_hash_tampered(self):
        """verify_envelope_hash returns False for tampered envelope."""
        env = create_envelope(
            node_id="test",
            seq=0,
            event_type="TEST",
            payload={"key": "value"},
            collector_version="v1.0.0",
        )
        
        # Tamper with payload after hash computed
        env.payload["key"] = "tampered"
        
        # payload_hash will also be wrong
        assert env.verify_envelope_hash() is False


class TestChainCreation:
    """Test chain creation with prev_hash linking."""
    
    def test_first_envelope_no_prev_hash(self):
        """First envelope (seq=0) has no prev_hash."""
        env = create_envelope(
            node_id="chain-test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        assert env.prev_hash is None
    
    def test_chain_link_correct(self):
        """Second envelope prev_hash matches first envelope_hash."""
        env1 = create_envelope(
            node_id="chain-test",
            seq=0,
            event_type="TEST",
            payload={"seq": 0},
            collector_version="v1.0.0",
        )
        
        env2 = create_envelope(
            node_id="chain-test",
            seq=1,
            event_type="TEST",
            payload={"seq": 1},
            collector_version="v1.0.0",
            prev_hash=env1.envelope_hash,
        )
        
        assert env2.prev_hash == env1.envelope_hash
    
    def test_chain_three_envelopes(self):
        """Three-envelope chain has correct linking."""
        envs = []
        prev = None
        
        for i in range(3):
            env = create_envelope(
                node_id="chain-3",
                seq=i,
                event_type="TEST",
                payload={"seq": i},
                collector_version="v1.0.0",
                prev_hash=prev,
            )
            envs.append(env)
            prev = env.envelope_hash
        
        # Verify chain
        assert envs[0].prev_hash is None
        assert envs[1].prev_hash == envs[0].envelope_hash
        assert envs[2].prev_hash == envs[1].envelope_hash


class TestChainValidation:
    """Test validate_chain function."""
    
    def test_valid_chain(self):
        """Valid chain passes validation."""
        envs = []
        prev = None
        
        for i in range(5):
            env = create_envelope(
                node_id="valid-chain",
                seq=i,
                event_type="TEST",
                payload={"i": i},
                collector_version="v1.0.0",
                prev_hash=prev,
            )
            envs.append(env)
            prev = env.envelope_hash
        
        valid, errors = validate_chain(envs)
        assert valid is True
        assert len(errors) == 0
    
    def test_broken_chain_wrong_prev_hash(self):
        """Broken chain (wrong prev_hash) fails validation."""
        env1 = create_envelope(
            node_id="broken",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        # Wrong prev_hash
        env2 = create_envelope(
            node_id="broken",
            seq=1,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash="wrong_hash_value",
        )
        
        valid, errors = validate_chain([env1, env2])
        assert valid is False
        assert any("chain broken" in e.lower() for e in errors)
    
    def test_non_monotonic_seq(self):
        """Non-monotonic sequence fails validation."""
        env1 = create_envelope(
            node_id="seq-test",
            seq=5,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        env2 = create_envelope(
            node_id="seq-test",
            seq=3,  # Less than previous
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash=env1.envelope_hash,
        )
        
        valid, errors = validate_chain([env1, env2])
        assert valid is False
        assert any("monotonic" in e.lower() for e in errors)


class TestIngestChain:
    """Test store ingest with chain validation."""
    
    @pytest.fixture
    def temp_evidence_dir(self, tmp_path, monkeypatch):
        """Create temp evidence directory."""
        evidence_dir = tmp_path / "logs" / "evidence"
        evidence_dir.mkdir(parents=True)
        
        def mock_get_evidence_dir():
            return evidence_dir
        
        monkeypatch.setattr(
            "station_calyx.evidence.store.get_evidence_dir",
            mock_get_evidence_dir
        )
        
        return evidence_dir
    
    def test_multi_envelope_chain_accepted(self, temp_evidence_dir):
        """Multi-envelope chain is fully accepted."""
        from station_calyx.evidence.store import ingest_batch, load_ingest_state
        
        envs = []
        prev = None
        
        for i in range(5):
            env = create_envelope(
                node_id="ingest-chain",
                seq=i,
                event_type="TEST",
                payload={"i": i},
                collector_version="v1.0.0",
                prev_hash=prev,
            )
            envs.append(env)
            prev = env.envelope_hash
        
        summary = ingest_batch([e.to_dict() for e in envs])
        
        assert summary.accepted_count == 5
        assert summary.rejected_count == 0
        
        # Verify state
        state = load_ingest_state("ingest-chain")
        assert state.last_seq == 4
        assert state.last_hash == envs[-1].envelope_hash
    
    def test_broken_chain_rejected_after_first(self, temp_evidence_dir):
        """Broken chain: first accepted, rest rejected."""
        from station_calyx.evidence.store import ingest_batch, load_ingest_state
        
        env1 = create_envelope(
            node_id="broken-ingest",
            seq=0,
            event_type="TEST",
            payload={"i": 0},
            collector_version="v1.0.0",
        )
        
        # Second envelope has WRONG prev_hash
        env2 = create_envelope(
            node_id="broken-ingest",
            seq=1,
            event_type="TEST",
            payload={"i": 1},
            collector_version="v1.0.0",
            prev_hash="deliberately_wrong_hash",
        )
        
        env3 = create_envelope(
            node_id="broken-ingest",
            seq=2,
            event_type="TEST",
            payload={"i": 2},
            collector_version="v1.0.0",
            prev_hash=env2.envelope_hash,
        )
        
        summary = ingest_batch([e.to_dict() for e in [env1, env2, env3]])
        
        # Only first should be accepted
        assert summary.accepted_count == 1
        assert summary.rejected_count == 2
        
        # State should reflect only first envelope
        state = load_ingest_state("broken-ingest")
        assert state.last_seq == 0
        assert state.last_hash == env1.envelope_hash
    
    def test_regression_first_accepted_subsequent_rejected(self, temp_evidence_dir):
        """
        REGRESSION TEST: Ensure "first accepted, subsequent rejected" 
        is due to actual chain breaks, not hash computation mismatch.
        """
        from station_calyx.evidence.store import ingest_batch, load_ingest_state
        
        # Create valid chain
        envs = []
        prev = None
        
        for i in range(3):
            env = create_envelope(
                node_id="regression-test",
                seq=i,
                event_type="SNAPSHOT",
                payload={"cpu": 25.0 + i, "memory": 40.0 + i},
                collector_version="v1.7.0",
                prev_hash=prev,
            )
            envs.append(env)
            prev = env.envelope_hash
        
        # Verify each envelope has envelope_hash set
        for env in envs:
            assert env.envelope_hash is not None, f"seq={env.seq} missing envelope_hash"
        
        # Verify chain links
        assert envs[0].prev_hash is None
        assert envs[1].prev_hash == envs[0].envelope_hash
        assert envs[2].prev_hash == envs[1].envelope_hash
        
        # Ingest
        summary = ingest_batch([e.to_dict() for e in envs])
        
        # ALL should be accepted (not just first)
        assert summary.accepted_count == 3, (
            f"Expected 3 accepted, got {summary.accepted_count}. "
            f"Rejections: {summary.rejection_reasons}"
        )
        assert summary.rejected_count == 0
        
        # Final state
        state = load_ingest_state("regression-test")
        assert state.last_seq == 2
        assert state.last_hash == envs[2].envelope_hash


class TestEnvelopeHashFromDict:
    """Test compute_envelope_hash_from_dict helper."""
    
    def test_matches_envelope_method(self):
        """compute_envelope_hash_from_dict matches envelope.compute_envelope_hash()."""
        env = create_envelope(
            node_id="dict-test",
            seq=0,
            event_type="TEST",
            payload={"key": "value"},
            collector_version="v1.0.0",
        )
        
        from_dict = compute_envelope_hash_from_dict(env.to_dict())
        from_method = env.compute_envelope_hash()
        
        assert from_dict == from_method
    
    def test_excludes_envelope_hash_and_signature(self):
        """Hash excludes envelope_hash and signature fields."""
        d = {
            "envelope_version": "v1",
            "node_id": "test",
            "seq": 0,
            "event_type": "TEST",
            "payload": {},
            "payload_hash": "abc",
            "collector_version": "v1.0.0",
            "captured_at_iso": "2026-01-10T00:00:00+00:00",
            "envelope_hash": "should_be_ignored",
            "signature": "should_be_ignored",
        }
        
        hash1 = compute_envelope_hash_from_dict(d)
        
        # Same dict without excluded fields
        d2 = dict(d)
        del d2["envelope_hash"]
        del d2["signature"]
        
        hash2 = compute_envelope_hash_from_dict(d2)
        
        assert hash1 == hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
