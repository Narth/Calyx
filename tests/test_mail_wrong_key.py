"""Test Calyx Mail wrong key handling: recipient mismatch -> decrypt fails."""

from __future__ import annotations

import pytest

from calyx.mail import crypto, envelope


def test_mail_wrong_recipient_key():
    """Test that wrong recipient key causes decryption to fail."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    wrong_recipient_identity = crypto.generate_identity()
    
    # Create envelope for recipient
    plaintext = b"Secret message"
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_identity["signing_keypair"]["private"],
        sender_signing_pub=sender_identity["signing_keypair"]["public"],
        recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
    )
    
    # Try to decrypt with wrong recipient's key
    with pytest.raises(crypto.DecryptionError):
        envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=wrong_recipient_identity["encryption_keypair"]["private"],
        )


def test_mail_wrong_sender_key():
    """Test that wrong sender public key causes verification to fail."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    wrong_sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Create envelope
    plaintext = b"Secret message"
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_identity["signing_keypair"]["private"],
        sender_signing_pub=sender_identity["signing_keypair"]["public"],
        recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
    )
    
    # Try to verify with wrong sender's public key
    with pytest.raises(envelope.VerificationError):
        envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=wrong_sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
        )
