"""Test Calyx Mail tamper detection: modify header -> verify fails."""

from __future__ import annotations

import base64
import json

import pytest

from calyx.mail import crypto, envelope


def test_mail_tamper_header():
    """Test that tampering with header causes verification to fail."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Create envelope
    plaintext = b"Original message"
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_identity["signing_keypair"]["private"],
        sender_signing_pub=sender_identity["signing_keypair"]["public"],
        recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
    )
    
    # Tamper with header (modify subject)
    env["header"]["subject"] = "TAMPERED SUBJECT"
    
    # Verification should fail
    with pytest.raises(envelope.VerificationError):
        envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
        )


def test_mail_tamper_ciphertext():
    """Test that tampering with ciphertext causes decryption to fail."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Create envelope
    plaintext = b"Original message"
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_identity["signing_keypair"]["private"],
        sender_signing_pub=sender_identity["signing_keypair"]["public"],
        recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
    )
    
    # Tamper with ciphertext (flip a bit)
    ciphertext_bytes = base64.b64decode(env["ciphertext"])
    tampered_bytes = bytearray(ciphertext_bytes)
    tampered_bytes[0] ^= 1  # Flip first bit
    env["ciphertext"] = base64.b64encode(bytes(tampered_bytes)).decode('ascii')
    
    # Verification should fail (signature check)
    with pytest.raises(envelope.VerificationError):
        envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
        )


def test_mail_tamper_signature():
    """Test that tampering with signature causes verification to fail."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Create envelope
    plaintext = b"Original message"
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_identity["signing_keypair"]["private"],
        sender_signing_pub=sender_identity["signing_keypair"]["public"],
        recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
    )
    
    # Tamper with signature (flip a bit)
    sig_bytes = base64.b64decode(env["signature"])
    tampered_sig = bytearray(sig_bytes)
    tampered_sig[0] ^= 1  # Flip first bit
    env["signature"] = base64.b64encode(bytes(tampered_sig)).decode('ascii')
    
    # Verification should fail
    with pytest.raises(envelope.VerificationError):
        envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
        )
