# -*- coding: utf-8 -*-
"""
Unit Tests for Evidence Store
=============================

Tests:
1. Per-node evidence separation
2. Replay protection via seq
3. Hash-chain enforcement
4. Ingest state persistence
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from station_calyx.schemas.evidence_envelope_v1 import (
    EvidenceEnvelopeV1,
    create_envelope,
)
from station_calyx.evidence.store import (
    IngestState,
    IngestResult,
    IngestSummary,
    load_ingest_state,
    save_ingest_state,
    append_envelope,
    ingest_batch,
    validate_for_ingest,
    get_node_dir,
    get_node_evidence,
    get_known_nodes,
)


@pytest.fixture
def temp_evidence_dir(tmp_path, monkeypatch):
    """Create a temporary evidence directory."""
    evidence_dir = tmp_path / "logs" / "evidence"
    evidence_dir.mkdir(parents=True)
    
    # Monkey-patch get_evidence_dir to use temp directory
    def mock_get_evidence_dir():
        return evidence_dir
    
    monkeypatch.setattr(
        "station_calyx.evidence.store.get_evidence_dir",
        mock_get_evidence_dir
    )
    
    return evidence_dir


@pytest.fixture
def sample_envelope():
    """Create a sample envelope."""
    return create_envelope(
        node_id="test-node-001",
        seq=0,
        event_type="SYSTEM_SNAPSHOT",
        payload={"cpu": 25.0, "memory": 42.0},
        collector_version="v1.0.0",
        node_name="Test Node",
    )


class TestIngestState:
    """Tests for ingest state management."""
    
    def test_initial_state(self):
        """Initial state has seq=-1 and no hash."""
        state = IngestState(node_id="test")
        
        assert state.last_seq == -1
        assert state.last_hash is None
        assert state.total_envelopes == 0
    
    def test_state_roundtrip(self):
        """State survives dict roundtrip."""
        original = IngestState(
            node_id="test",
            last_seq=42,
            last_hash="abc123",
            last_ingested_at="2026-01-01T00:00:00Z",
            total_envelopes=100,
        )
        
        restored = IngestState.from_dict(original.to_dict())
        
        assert restored.node_id == original.node_id
        assert restored.last_seq == original.last_seq
        assert restored.last_hash == original.last_hash
        assert restored.total_envelopes == original.total_envelopes
    
    def test_save_and_load_state(self, temp_evidence_dir):
        """State persists to disk."""
        state = IngestState(
            node_id="persist-test",
            last_seq=10,
            last_hash="xyz789",
            total_envelopes=11,
        )
        
        save_ingest_state(state)
        loaded = load_ingest_state("persist-test")
        
        assert loaded.last_seq == 10
        assert loaded.last_hash == "xyz789"
        assert loaded.total_envelopes == 11


class TestValidation:
    """Tests for envelope validation."""
    
    def test_valid_envelope_first(self, sample_envelope, temp_evidence_dir):
        """First envelope (seq=0) is valid against empty state."""
        state = IngestState(node_id="test-node-001")
        
        is_valid, reason = validate_for_ingest(sample_envelope, state)
        
        assert is_valid is True
        assert reason is None
    
    def test_reject_duplicate_seq(self, sample_envelope, temp_evidence_dir):
        """Envelope with seq <= last_seq is rejected."""
        state = IngestState(node_id="test-node-001", last_seq=5)
        sample_envelope.seq = 5  # Same as last_seq
        
        is_valid, reason = validate_for_ingest(sample_envelope, state)
        
        assert is_valid is False
        assert "monotonic" in reason.lower() or "seq" in reason.lower()
    
    def test_reject_lower_seq(self, sample_envelope, temp_evidence_dir):
        """Envelope with seq < last_seq is rejected (replay)."""
        state = IngestState(node_id="test-node-001", last_seq=10)
        sample_envelope.seq = 5  # Lower than last_seq
        
        is_valid, reason = validate_for_ingest(sample_envelope, state)
        
        assert is_valid is False
        assert "monotonic" in reason.lower() or "seq" in reason.lower()
    
    def test_reject_wrong_prev_hash(self, temp_evidence_dir):
        """Envelope with wrong prev_hash is rejected."""
        env = create_envelope(
            node_id="test-node",
            seq=1,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash="wrong_hash_value",
        )
        
        state = IngestState(
            node_id="test-node",
            last_seq=0,
            last_hash="correct_hash_value",
        )
        
        is_valid, reason = validate_for_ingest(env, state)
        
        assert is_valid is False
        assert "hash" in reason.lower() or "chain" in reason.lower()
    
    def test_reject_tampered_payload(self, temp_evidence_dir):
        """Envelope with tampered payload is rejected."""
        env = create_envelope(
            node_id="test-node",
            seq=0,
            event_type="TEST",
            payload={"original": True},
            collector_version="v1.0.0",
        )
        
        # Tamper with payload after hash was computed
        env.payload["original"] = False
        
        state = IngestState(node_id="test-node")
        
        is_valid, reason = validate_for_ingest(env, state)
        
        assert is_valid is False
        assert "hash" in reason.lower() or "tamper" in reason.lower()


class TestAppendEnvelope:
    """Tests for envelope append."""
    
    def test_append_first_envelope(self, sample_envelope, temp_evidence_dir):
        """First envelope appends successfully."""
        result = append_envelope(sample_envelope)
        
        assert result.accepted is True
        assert result.envelope_hash is not None
        assert result.rejection_reason is None
    
    def test_append_updates_state(self, sample_envelope, temp_evidence_dir):
        """Appending updates ingest state."""
        result = append_envelope(sample_envelope)
        
        state = load_ingest_state("test-node-001")
        
        assert state.last_seq == 0
        assert state.last_hash == result.envelope_hash
        assert state.total_envelopes == 1
    
    def test_append_chain(self, temp_evidence_dir):
        """Chain of envelopes appends with correct linking."""
        env0 = create_envelope(
            node_id="chain-test",
            seq=0,
            event_type="TEST",
            payload={"seq": 0},
            collector_version="v1.0.0",
        )
        
        result0 = append_envelope(env0)
        assert result0.accepted is True
        
        env1 = create_envelope(
            node_id="chain-test",
            seq=1,
            event_type="TEST",
            payload={"seq": 1},
            collector_version="v1.0.0",
            prev_hash=result0.envelope_hash,
        )
        
        result1 = append_envelope(env1)
        assert result1.accepted is True
        
        state = load_ingest_state("chain-test")
        assert state.last_seq == 1
        assert state.total_envelopes == 2
    
    def test_reject_replay(self, sample_envelope, temp_evidence_dir):
        """Replayed envelope (same seq) is rejected."""
        # First append succeeds
        result1 = append_envelope(sample_envelope)
        assert result1.accepted is True
        
        # Same envelope again (replay) fails
        result2 = append_envelope(sample_envelope)
        assert result2.accepted is False
        assert "seq" in result2.rejection_reason.lower() or "monotonic" in result2.rejection_reason.lower()


class TestBatchIngest:
    """Tests for batch ingest."""
    
    def test_batch_empty(self, temp_evidence_dir):
        """Empty batch returns zero counts."""
        summary = ingest_batch([])
        
        assert summary.accepted_count == 0
        assert summary.rejected_count == 0
    
    def test_batch_single(self, temp_evidence_dir):
        """Single envelope batch works."""
        env = create_envelope(
            node_id="batch-test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        summary = ingest_batch([env.to_dict()])
        
        assert summary.accepted_count == 1
        assert summary.rejected_count == 0
    
    def test_batch_chain(self, temp_evidence_dir):
        """Batch with valid chain works."""
        env0 = create_envelope(
            node_id="batch-chain",
            seq=0,
            event_type="TEST",
            payload={"i": 0},
            collector_version="v1.0.0",
        )
        
        env1 = create_envelope(
            node_id="batch-chain",
            seq=1,
            event_type="TEST",
            payload={"i": 1},
            collector_version="v1.0.0",
            prev_hash=env0.compute_envelope_hash(),
        )
        
        summary = ingest_batch([env0.to_dict(), env1.to_dict()])
        
        assert summary.accepted_count == 2
        assert summary.rejected_count == 0
    
    def test_batch_stops_on_rejection(self, temp_evidence_dir):
        """Batch stops processing node after rejection."""
        env0 = create_envelope(
            node_id="stop-test",
            seq=0,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
        )
        
        # env1 has wrong prev_hash - will be rejected
        env1 = create_envelope(
            node_id="stop-test",
            seq=1,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash="wrong_hash",
        )
        
        # env2 would be valid but should be skipped
        env2 = create_envelope(
            node_id="stop-test",
            seq=2,
            event_type="TEST",
            payload={},
            collector_version="v1.0.0",
            prev_hash="also_wrong",
        )
        
        summary = ingest_batch([
            env0.to_dict(),
            env1.to_dict(),
            env2.to_dict(),
        ])
        
        assert summary.accepted_count == 1  # Only env0
        assert summary.rejected_count == 2  # env1 rejected, env2 skipped


class TestNodeSeparation:
    """Tests for per-node evidence separation."""
    
    def test_separate_nodes(self, temp_evidence_dir):
        """Envelopes from different nodes are stored separately."""
        env_a = create_envelope(
            node_id="node-A",
            seq=0,
            event_type="TEST",
            payload={"node": "A"},
            collector_version="v1.0.0",
        )
        
        env_b = create_envelope(
            node_id="node-B",
            seq=0,
            event_type="TEST",
            payload={"node": "B"},
            collector_version="v1.0.0",
        )
        
        append_envelope(env_a)
        append_envelope(env_b)
        
        # Both nodes should be known
        nodes = get_known_nodes()
        assert "node-A" in nodes or any("node-A" in n for n in nodes)
        assert "node-B" in nodes or any("node-B" in n for n in nodes)
        
        # Each should have separate state
        state_a = load_ingest_state("node-A")
        state_b = load_ingest_state("node-B")
        
        assert state_a.total_envelopes == 1
        assert state_b.total_envelopes == 1
    
    def test_retrieve_node_evidence(self, temp_evidence_dir):
        """Can retrieve evidence for specific node."""
        env = create_envelope(
            node_id="retrieve-test",
            seq=0,
            event_type="TEST",
            payload={"data": "test"},
            collector_version="v1.0.0",
        )
        
        append_envelope(env)
        
        evidence = get_node_evidence("retrieve-test")
        
        assert len(evidence) == 1
        assert evidence[0]["payload"]["data"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
