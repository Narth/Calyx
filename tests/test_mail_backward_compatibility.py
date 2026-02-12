"""Tests for backward compatibility (v0 envelopes readable by v0.1 code)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from calyx.mail import codec, envelope


def test_v0_envelope_detection():
    """Test that v0 envelopes are detected correctly."""
    # v0 envelope (no protocol_version)
    envelope_v0 = {
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    # v0.1 envelope
    envelope_v0_1 = {
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
    
    assert codec.detect_version(envelope_v0) == "0.0"
    assert codec.detect_version(envelope_v0_1) == "0.1"


def test_v0_envelope_encoding_strict_rejection():
    """Test that v0 envelopes with floats are rejected (strict policy)."""
    # v0 envelope with float (should be rejected)
    envelope_v0_float = {
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z",
            "numeric_value": 1.0  # Float - should be rejected
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    # Should reject floats (strict policy - Option B)
    with pytest.raises(codec.EncodingError, match="v0 envelope contains floats"):
        codec.encode_envelope_v0(envelope_v0_float)


def test_v0_envelope_hash():
    """Test that v0 envelopes can compute hash."""
    envelope_v0 = {
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    hash_value = codec.compute_envelope_hash(envelope_v0)
    
    assert len(hash_value) == 64  # Full SHA256 hex
    assert isinstance(hash_value, str)


def test_v0_v0_1_hash_difference():
    """Test that v0 and v0.1 envelopes produce different hashes."""
    envelope_v0 = {
        "header": {
            "sender_fp": "abc123",
            "recipient_fp": "def456",
            "msg_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-12T10:30:00Z"
        },
        "ciphertext": "base64-ciphertext",
        "signature": "base64-signature"
    }
    
    envelope_v0_1 = {
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
    
    hash_v0 = codec.compute_envelope_hash(envelope_v0)
    hash_v0_1 = codec.compute_envelope_hash(envelope_v0_1)
    
    # Different protocol versions should produce different hashes
    assert hash_v0 != hash_v0_1


def test_v0_float_edge_cases():
    """Test v0 float edge cases (all should be rejected)."""
    import math
    
    test_cases = [
        {"value": 0.1},  # Non-integer float
        {"value": 1e6},  # Scientific notation
        {"value": -0.0},  # Negative zero
        {"value": math.nan},  # NaN
        {"value": math.inf},  # Infinity
        {"value": -math.inf},  # Negative infinity
    ]
    
    for test_case in test_cases:
        envelope = {
            "header": {
                "sender_fp": "abc123",
                "recipient_fp": "def456",
                "msg_id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2026-02-12T10:30:00Z",
                **test_case
            },
            "ciphertext": "base64-ciphertext",
            "signature": "base64-signature"
        }
        
        # All should be rejected (strict policy - Option B)
        # NaN/Infinity raise different error messages
        if any(math.isnan(v) or math.isinf(v) for v in test_case.values()):
            with pytest.raises(codec.EncodingError):
                codec.encode_envelope_v0(envelope)
        else:
            with pytest.raises(codec.EncodingError, match="v0 envelope contains floats"):
                codec.encode_envelope_v0(envelope)
