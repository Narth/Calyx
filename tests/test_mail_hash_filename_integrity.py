"""Tests for hash-to-filename integrity (content-addressed storage)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from calyx.mail import codec, mailbox


def test_hash_filename_match():
    """Test that filename hash matches content hash."""
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
    
    # Compute hash
    content_hash = codec.compute_envelope_hash(envelope)
    
    # Write to outbox
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        outbox_path = mailbox.write_outbox(envelope, runtime_dir)
        
        # Filename should match hash
        assert outbox_path.stem == content_hash
        assert len(outbox_path.stem) == 64  # Full SHA256 hex


def test_hash_mismatch_detection():
    """Test that hash mismatch is detected."""
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
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Write envelope
        outbox_path = mailbox.write_outbox(envelope, runtime_dir)
        
        # Tamper with file content
        tampered_content = b'{"tampered": true}'
        outbox_path.write_bytes(tampered_content)
        
        # Try to list inbox (should skip tampered file)
        # Note: list_inbox verifies hash matches filename
        inbox_list = mailbox.list_inbox(runtime_dir)
        
        # Tampered file should not appear in list (hash mismatch)
        assert len(inbox_list) == 0


def test_duplicate_content_same_filename():
    """Test that duplicate content produces same filename."""
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
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Write twice
        path1 = mailbox.write_outbox(envelope, runtime_dir)
        path2 = mailbox.write_outbox(envelope, runtime_dir)
        
        # Should be same file (content-addressed)
        assert path1 == path2
        assert path1.exists()


def test_content_hash_full_sha256():
    """Test that content hash is full SHA256 (64 hex chars)."""
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
    
    content_hash = codec.compute_envelope_hash(envelope)
    
    assert len(content_hash) == 64  # Full SHA256 hex (no truncation)
    assert all(c in "0123456789abcdef" for c in content_hash)
