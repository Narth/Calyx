"""Tests for replay key determinism."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from calyx.mail import codec, replay


def test_replay_key_determinism():
    """Test that same envelope always produces same replay key."""
    envelope = {
        "protocol_version": "0.1",
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    # Compute replay key twice
    replay_key1 = codec.compute_envelope_hash(envelope)
    replay_key2 = codec.compute_envelope_hash(envelope)
    
    assert replay_key1 == replay_key2
    assert len(replay_key1) == 64  # Full SHA256 hex


def test_replay_key_tamper_resistance():
    """Test that tampering envelope changes replay key."""
    envelope1 = {
        "protocol_version": "0.1",
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    envelope2 = {
        "protocol_version": "0.1",
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z",
            "subject": "TAMPERED"  # Added field
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    replay_key1 = codec.compute_envelope_hash(envelope1)
    replay_key2 = codec.compute_envelope_hash(envelope2)
    
    assert replay_key1 != replay_key2  # Tampering changes replay key


def test_replay_state_sqlite():
    """Test SQLite replay state operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        db_path = runtime_dir / "mailbox" / "replay_state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        replay_state = replay.ReplayState(db_path)
        
        # Add replay key
        replay_key = "a" * 64  # 64-char hex
        replay_state.add_replay_key(
            replay_key=replay_key,
            msg_id="550e8400-e29b-41d4-a716-446655440000",
            sender_fp="abc123",
            recipient_fp="def456",
            envelope_timestamp="2026-02-12T10:30:00Z"
        )
        
        # Check exists
        assert replay_state.has_replay_key(replay_key)
        
        # Try to add again (should fail)
        with pytest.raises(replay.ReplayError):
            replay_state.add_replay_key(
                replay_key=replay_key,
                msg_id="550e8400-e29b-41d4-a716-446655440000",
                sender_fp="abc123",
                recipient_fp="def456",
                envelope_timestamp="2026-02-12T10:30:00Z"
            )


def test_replay_key_full_length():
    """Test that replay key is full SHA256 (64 hex chars)."""
    envelope = {
        "protocol_version": "0.1",
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    replay_key = codec.compute_envelope_hash(envelope)
    
    assert len(replay_key) == 64  # Full SHA256 hex (no truncation)
    assert all(c in "0123456789abcdef" for c in replay_key)
