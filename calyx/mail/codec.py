"""Canonical encoding/decoding for Calyx Mail Protocol Layer v0.1."""

from __future__ import annotations

import base64
import hashlib
import json
import unicodedata
from typing import Any

from .crypto import DecryptionError


class EncodingError(Exception):
    """Raised when encoding fails."""
    pass


class VersionError(Exception):
    """Raised when protocol version is unknown or invalid."""
    pass


def validate_canonical_types(obj: Any) -> None:
    """
    Validate that object contains only canonical types.
    
    Raises:
        ValueError: If disallowed types are present
    """
    import math
    if isinstance(obj, float):
        # Check for NaN/Infinity
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("NaN/Infinity disallowed")
        raise ValueError("Floats disallowed in canonical encoding (use int with scaling)")
    if isinstance(obj, set):
        raise ValueError("Sets disallowed (use sorted list)")
    if isinstance(obj, tuple):
        raise ValueError("Tuples disallowed (use list)")
    if isinstance(obj, bytes):
        raise ValueError("Bytes disallowed (use base64-encoded string)")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(f"Dict keys must be strings, got {type(k)}")
            validate_canonical_types(v)
    elif isinstance(obj, list):
        for item in obj:
            validate_canonical_types(item)


def canonical_encode(obj: Any) -> bytes:
    """
    Canonical encoding: SINGLE SOURCE OF TRUTH for deterministic serialization.
    
    This is the ONLY function that produces canonical bytes. All canonical encoding
    goes through this function to ensure byte-identical output for semantically
    identical structures.
    
    Encoding rules (deterministic):
    - UTF-8 encoding
    - NFC Unicode normalization
    - Sorted keys (recursive, depth-first, alphabetical) via json.dumps(sort_keys=True)
    - No whitespace (separators=(',', ':'))
    - No floats (rejected)
    
    Args:
        obj: Object to encode (dict, list, or primitive)
        
    Returns:
        Canonical JSON bytes (UTF-8)
        
    Raises:
        ValueError: If disallowed types are present
        UnicodeEncodeError: If invalid UTF-8
        
    Note:
        There is NO alternate code path. This function is the single source of truth.
        All envelope hashing, signature computation, and replay key generation
        use this function to ensure determinism.
    """
    # Type validation
    validate_canonical_types(obj)
    
    # Canonical JSON encoding (single deterministic method)
    # json.dumps with sort_keys=True ensures alphabetical key ordering
    canonical_json_str = json.dumps(
        obj,
        sort_keys=True,        # Alphabetical key sorting (deterministic)
        separators=(',', ':'), # No whitespace (deterministic)
        ensure_ascii=False,    # Allow UTF-8 (will normalize)
        allow_nan=False,       # Reject NaN/Infinity
    )
    
    # Unicode normalization (NFC) - ensures canonical form
    normalized = unicodedata.normalize('NFC', canonical_json_str)
    
    # UTF-8 encoding (final deterministic bytes)
    return normalized.encode('utf-8')


def build_signed_payload(protocol_version: str, header: dict, ciphertext: str) -> dict:
    """
    Build signed payload with explicit construction order.
    
    Construction order:
    1. protocol_version (first)
    2. header (second, with keys sorted alphabetically)
    3. ciphertext (third)
    
    Args:
        protocol_version: Protocol version string (e.g., "0.1")
        header: Header dict (will be sorted internally)
        ciphertext: Base64-encoded ciphertext
        
    Returns:
        Dict with explicit key order: protocol_version, header, ciphertext
    """
    # Sort header keys alphabetically
    sorted_header = dict(sorted(header.items()))
    
    # Build payload in explicit order
    payload = {
        "protocol_version": protocol_version,
        "header": sorted_header,
        "ciphertext": ciphertext,
    }
    
    return payload


def detect_version(envelope: dict[str, Any]) -> str:
    """
    Detect protocol version from envelope.
    
    Args:
        envelope: Envelope dict
        
    Returns:
        Protocol version string ("0.1" or "0.0" for legacy v0)
    """
    if "protocol_version" in envelope:
        version = envelope["protocol_version"]
        if version == "0.1":
            return "0.1"
        else:
            raise VersionError(f"Unknown protocol version: {version}")
    else:
        return "0.0"  # Legacy v0 (no protocol_version field)


def encode_envelope_v0_1(envelope: dict[str, Any]) -> bytes:
    """
    Encode envelope to canonical bytes (v0.1).
    
    Args:
        envelope: Envelope dict with protocol_version="0.1"
        
    Returns:
        Canonical JSON bytes
        
    Raises:
        VersionError: If protocol_version is not "0.1"
        EncodingError: If encoding fails
    """
    # Verify version
    version = detect_version(envelope)
    if version != "0.1":
        raise VersionError(f"Expected protocol_version='0.1', got '{version}'")
    
    # Build signed payload (for signature verification)
    # Note: We encode the entire envelope, not just the signed payload
    # The signed payload structure is used for signature computation
    return canonical_encode(envelope)


def decode_envelope_v0_1(data: bytes) -> dict[str, Any]:
    """
    Decode canonical bytes to envelope dict (v0.1).
    
    Args:
        data: Canonical JSON bytes
        
    Returns:
        Envelope dict
        
    Raises:
        EncodingError: If decoding fails
        VersionError: If protocol_version is not "0.1"
    """
    try:
        # Decode UTF-8
        json_str = data.decode('utf-8')
        
        # Parse JSON
        envelope = json.loads(json_str)
        
        # Verify version
        version = detect_version(envelope)
        if version != "0.1":
            raise VersionError(f"Expected protocol_version='0.1', got '{version}'")
        
        return envelope
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EncodingError(f"Failed to decode envelope: {e}") from e


def encode_envelope_v0(envelope: dict[str, Any]) -> bytes:
    """
    Encode envelope to canonical bytes (legacy v0).
    
    **Float Policy (Option B - Strict Rejection):**
    v0 envelopes containing floats are rejected as non-canonical.
    This ensures deterministic encoding and prevents ambiguity.
    
    Args:
        envelope: Envelope dict without protocol_version
        
    Returns:
        Canonical JSON bytes
        
    Raises:
        EncodingError: If encoding fails (including floats)
        ValueError: If envelope contains floats (strict rejection)
    """
    # Legacy v0: no protocol_version field
    # Use canonical encoding (strict rejection of floats)
    try:
        return canonical_encode(envelope)
    except ValueError as e:
        # Strict rejection: v0 envelopes with floats are non-canonical
        if "Floats disallowed" in str(e):
            raise EncodingError(
                "v0 envelope contains floats (non-canonical). "
                "Floats are strictly rejected in v0.1. "
                "Use integers with explicit scaling if needed."
            ) from e
        raise EncodingError(f"Failed to encode v0 envelope: {e}") from e


def decode_envelope_v0(data: bytes) -> dict[str, Any]:
    """
    Decode canonical bytes to envelope dict (legacy v0).
    
    Args:
        data: Canonical JSON bytes
        
    Returns:
        Envelope dict
        
    Raises:
        EncodingError: If decoding fails
    """
    try:
        json_str = data.decode('utf-8')
        envelope = json.loads(json_str)
        return envelope
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EncodingError(f"Failed to decode v0 envelope: {e}") from e


def compute_envelope_hash(envelope: dict[str, Any]) -> str:
    """
    Compute full SHA256 hash of canonical envelope.
    
    Args:
        envelope: Envelope dict
        
    Returns:
        64-character hexadecimal string (full SHA256, no truncation)
    """
    version = detect_version(envelope)
    if version == "0.1":
        canonical_bytes = encode_envelope_v0_1(envelope)
    else:
        canonical_bytes = encode_envelope_v0(envelope)
    
    hash_obj = hashlib.sha256(canonical_bytes)
    return hash_obj.hexdigest()  # Full 64-character hex


def validate_canonical(data: bytes) -> bool:
    """
    Validate that bytes are canonical JSON.
    
    Args:
        data: Bytes to validate
        
    Returns:
        True if canonical, False otherwise
    """
    try:
        # Try to decode
        json_str = data.decode('utf-8')
        obj = json.loads(json_str)
        
        # Re-encode and compare
        re_encoded = canonical_encode(obj)
        return re_encoded == data
    except Exception:
        return False
