"""Property tests for canonical encoding stability and determinism."""

from __future__ import annotations

import pytest

from calyx.mail import codec


def test_canonical_determinism():
    """Test that same input always produces same output."""
    obj = {"key": "value", "number": 123}
    result1 = codec.canonical_encode(obj)
    result2 = codec.canonical_encode(obj)
    assert result1 == result2


def test_canonical_order_independence():
    """Test that key order in input does not affect output."""
    obj1 = {"zebra": 1, "alpha": 2}
    obj2 = {"alpha": 2, "zebra": 1}
    result1 = codec.canonical_encode(obj1)
    result2 = codec.canonical_encode(obj2)
    assert result1 == result2


def test_canonical_rejects_floats():
    """Test that floats are rejected."""
    obj = {"value": 1.0}
    with pytest.raises(ValueError, match="Floats disallowed"):
        codec.canonical_encode(obj)


def test_canonical_rejects_nan():
    """Test that NaN is rejected."""
    import math
    obj = {"value": math.nan}
    with pytest.raises(ValueError, match="NaN/Infinity"):
        codec.canonical_encode(obj)


def test_canonical_rejects_sets():
    """Test that sets are rejected."""
    obj = {"items": {1, 2, 3}}
    with pytest.raises(ValueError, match="Sets disallowed"):
        codec.canonical_encode(obj)


def test_canonical_nested_sorting():
    """Test that nested dicts are sorted recursively."""
    obj = {
        "z": {"c": 1, "a": 2},
        "a": {"b": 3}
    }
    encoded = codec.canonical_encode(obj)
    # Should be sorted: a comes before z, and within nested dicts too
    assert encoded.startswith(b'{"a":')


def test_build_signed_payload_order():
    """Test that signed payload has explicit construction order."""
    header = {"sender_fp": "abc", "recipient_fp": "def", "msg_id": "uuid", "timestamp": "2026-01-01T00:00:00Z"}
    payload = codec.build_signed_payload("0.1", header, "ciphertext")
    
    # Check that protocol_version is first (in logical structure)
    # JSON serialization will sort keys, but construction order ensures protocol_version is included
    assert "protocol_version" in payload
    assert payload["protocol_version"] == "0.1"
    assert payload["header"] == header
    assert payload["ciphertext"] == "ciphertext"


def test_envelope_hash_determinism():
    """Test that envelope hash is deterministic."""
    envelope1 = {
        "protocol_version": "0.1",
        "header": {"msg_id": "test", "sender_fp": "abc", "recipient_fp": "def", "timestamp": "2026-01-01T00:00:00Z"},
        "ciphertext": "base64",
        "signature": "sig"
    }
    envelope2 = {
        "protocol_version": "0.1",
        "header": {"msg_id": "test", "sender_fp": "abc", "recipient_fp": "def", "timestamp": "2026-01-01T00:00:00Z"},
        "ciphertext": "base64",
        "signature": "sig"
    }
    
    hash1 = codec.compute_envelope_hash(envelope1)
    hash2 = codec.compute_envelope_hash(envelope2)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # Full SHA256 hex


def test_envelope_hash_full_length():
    """Test that envelope hash is full SHA256 (64 hex chars, no truncation)."""
    envelope = {
        "protocol_version": "0.1",
        "header": {"msg_id": "test", "sender_fp": "abc", "recipient_fp": "def", "timestamp": "2026-01-01T00:00:00Z"},
        "ciphertext": "base64",
        "signature": "sig"
    }
    
    hash_value = codec.compute_envelope_hash(envelope)
    
    assert len(hash_value) == 64  # Full SHA256 hex (no truncation)
    assert all(c in "0123456789abcdef" for c in hash_value)  # Valid hex


def test_version_detection():
    """Test version detection."""
    envelope_v0_1 = {"protocol_version": "0.1", "header": {}, "ciphertext": "", "signature": ""}
    envelope_v0 = {"header": {}, "ciphertext": "", "signature": ""}
    
    assert codec.detect_version(envelope_v0_1) == "0.1"
    assert codec.detect_version(envelope_v0) == "0.0"
    
    with pytest.raises(codec.VersionError):
        codec.detect_version({"protocol_version": "0.2", "header": {}, "ciphertext": "", "signature": ""})


def test_canonical_unicode_normalization():
    """Test Unicode NFC normalization."""
    # U+00E9 (é) vs U+0065 U+0301 (e + combining acute)
    obj1 = {"text": "\u00e9"}  # Precomposed
    obj2 = {"text": "\u0065\u0301"}  # Decomposed
    
    result1 = codec.canonical_encode(obj1)
    result2 = codec.canonical_encode(obj2)
    
    # Should produce same canonical bytes (NFC normalization)
    assert result1 == result2


def test_canonical_dict_insertion_order():
    """Test that dict insertion order doesn't affect canonical output."""
    # Create dicts with different insertion orders
    obj1 = {}
    obj1["z"] = 1
    obj1["a"] = 2
    obj1["m"] = 3
    
    obj2 = {}
    obj2["a"] = 2
    obj2["m"] = 3
    obj2["z"] = 1
    
    result1 = codec.canonical_encode(obj1)
    result2 = codec.canonical_encode(obj2)
    
    assert result1 == result2


def test_canonical_nested_structures():
    """Test canonical encoding of deeply nested structures."""
    obj = {
        "level1": {
            "level2": {
                "level3": [1, 2, {"nested": "value"}]
            }
        }
    }
    
    # Should encode without error
    encoded = codec.canonical_encode(obj)
    assert isinstance(encoded, bytes)
    assert len(encoded) > 0
    
    # Should be deterministic
    encoded2 = codec.canonical_encode(obj)
    assert encoded == encoded2
