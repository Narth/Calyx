"""Envelope creation and verification for Calyx Mail Protocol Layer v0.1."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from .codec import build_signed_payload, canonical_encode, detect_version
from .crypto import (
    DecryptionError,
    compute_fingerprint,
    open_from_sender,
    sign,
    verify,
)


class VerificationError(Exception):
    """Raised when envelope verification fails."""
    pass


class AllowlistError(Exception):
    """Raised when sender is not in recipient's allowlist."""
    pass


class ReplayError(Exception):
    """Raised when message ID is already seen or timestamp is invalid."""
    pass


# canonical_json moved to codec.py - use canonical_encode() instead


def create_envelope(
    plaintext: bytes,
    sender_signing_priv: bytes,
    sender_signing_pub: bytes,
    recipient_encryption_pub: bytes,
    subject: str | None = None,
    msg_id: str | None = None,
    protocol_version: str = "0.1",
) -> dict[str, Any]:
    """
    Create a signed and encrypted envelope (v0.1).
    
    Args:
        plaintext: Message body bytes
        sender_signing_priv: Sender's ed25519 private key (32 bytes)
        sender_signing_pub: Sender's ed25519 public key (32 bytes)
        recipient_encryption_pub: Recipient's x25519 public key (32 bytes)
        subject: Optional subject line (max 256 chars)
        msg_id: Optional message ID (UUID v4). Generated if not provided.
        protocol_version: Protocol version (default: "0.1")
        
    Returns:
        Envelope dict with protocol_version, header, ciphertext, and signature
    """
    # Generate message ID if not provided
    if msg_id is None:
        msg_id = str(uuid.uuid4())
    
    # Validate subject length
    if subject is not None and len(subject) > 256:
        raise ValueError("Subject must be 256 characters or less")
    
    # Compute fingerprints
    sender_fp = compute_fingerprint(sender_signing_pub)
    recipient_fp = compute_fingerprint(recipient_encryption_pub)
    
    # Encrypt plaintext
    from .crypto import seal_to_recipient
    ciphertext_bytes = seal_to_recipient(plaintext, recipient_encryption_pub)
    ciphertext_b64 = base64.b64encode(ciphertext_bytes).decode('ascii')
    
    # Create header (keys will be sorted in build_signed_payload)
    header = {
        "sender_fp": sender_fp,
        "recipient_fp": recipient_fp,
        "msg_id": msg_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if subject is not None:
        header["subject"] = subject
    
    # Build signed payload (explicit construction order: protocol_version, header, ciphertext)
    payload = build_signed_payload(protocol_version, header, ciphertext_b64)
    
    # Canonical encode signed payload
    payload_bytes = canonical_encode(payload)
    
    # Sign payload
    signature_bytes = sign(payload_bytes, sender_signing_priv)
    signature_b64 = base64.b64encode(signature_bytes).decode('ascii')
    
    # Create envelope (with protocol_version)
    envelope = {
        "protocol_version": protocol_version,
        "header": header,
        "ciphertext": ciphertext_b64,
        "signature": signature_b64,
    }
    
    return envelope


def verify_and_open_envelope(
    envelope: dict[str, Any],
    sender_signing_pub: bytes,
    recipient_encryption_priv: bytes,
    allowlist_check: Callable[[str], bool] | None = None,
    msg_id_seen_check: Callable[[str], bool] | None = None,
    timestamp_check: Callable[[str], bool] | None = None,
) -> bytes:
    """
    Verify envelope signature and decrypt ciphertext.
    
    Args:
        envelope: Envelope dict with header, ciphertext, signature
        sender_signing_pub: Sender's ed25519 public key (32 bytes)
        recipient_encryption_priv: Recipient's x25519 private key (32 bytes)
        allowlist_check: Optional function to check sender fingerprint against allowlist.
                        Should return True if allowed, False otherwise.
        msg_id_seen_check: Optional function to check if msg_id was already seen.
                          Should return True if seen (replay), False otherwise.
        timestamp_check: Optional function to validate timestamp.
                        Should return True if valid, False otherwise.
        
    Returns:
        Decrypted plaintext bytes
        
    Raises:
        VerificationError: If signature verification fails
        AllowlistError: If sender is not in allowlist
        ReplayError: If message ID is seen or timestamp is invalid
        DecryptionError: If decryption fails
    """
    # Validate envelope structure
    if "header" not in envelope or "ciphertext" not in envelope or "signature" not in envelope:
        raise VerificationError("Envelope missing required fields")
    
    header = envelope["header"]
    ciphertext_b64 = envelope["ciphertext"]
    signature_b64 = envelope["signature"]
    
    # Check required header fields
    required_fields = ["sender_fp", "recipient_fp", "msg_id", "timestamp"]
    for field in required_fields:
        if field not in header:
            raise VerificationError(f"Header missing required field: {field}")
    
    # Check sender fingerprint against allowlist (deny-by-default)
    if allowlist_check is not None:
        sender_fp = header["sender_fp"]
        if not allowlist_check(sender_fp):
            raise AllowlistError(f"Sender fingerprint not in allowlist: {sender_fp}")
    
    # Check message ID uniqueness (replay protection)
    if msg_id_seen_check is not None:
        msg_id = header["msg_id"]
        if msg_id_seen_check(msg_id):
            raise ReplayError(f"Message ID already seen: {msg_id}")
    
    # Check timestamp window (replay protection)
    if timestamp_check is not None:
        timestamp = header["timestamp"]
        if not timestamp_check(timestamp):
            raise ReplayError(f"Timestamp validation failed: {timestamp}")
    
    # Build signed payload (with explicit construction order)
    protocol_version = envelope.get("protocol_version", "0.0")  # Legacy v0 support
    if protocol_version == "0.1":
        payload = build_signed_payload(protocol_version, header, ciphertext_b64)
        payload_bytes = canonical_encode(payload)
    else:
        # Legacy v0: no protocol_version in signed payload
        payload_dict = {
            "header": header,
            "ciphertext": ciphertext_b64,
        }
        payload_bytes = canonical_encode(payload_dict)
    
    try:
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        raise VerificationError(f"Invalid signature encoding: {e}") from e
    
    if not verify(payload_bytes, signature_bytes, sender_signing_pub):
        raise VerificationError("Signature verification failed")
    
    # Decrypt ciphertext
    try:
        ciphertext_bytes = base64.b64decode(ciphertext_b64)
    except Exception as e:
        raise DecryptionError(f"Invalid ciphertext encoding: {e}") from e
    
    plaintext = open_from_sender(ciphertext_bytes, recipient_encryption_priv)
    
    return plaintext


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse ISO 8601 timestamp string.
    
    Args:
        timestamp_str: ISO 8601 timestamp (e.g., "2026-02-12T10:30:00Z")
        
    Returns:
        datetime object (UTC)
        
    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e


def check_timestamp_window(timestamp_str: str, window_seconds: int = 300) -> bool:
    """
    Check if timestamp is within acceptable window (±window_seconds from now).
    
    Args:
        timestamp_str: ISO 8601 timestamp string
        window_seconds: Acceptable time window in seconds (default: 300 = 5 minutes)
        
    Returns:
        True if timestamp is within window, False otherwise
    """
    try:
        msg_time = parse_timestamp(timestamp_str)
        now = datetime.now(timezone.utc)
        delta = abs((now - msg_time).total_seconds())
        return delta <= window_seconds
    except ValueError:
        return False
