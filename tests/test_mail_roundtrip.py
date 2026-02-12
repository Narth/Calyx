"""Test Calyx Mail roundtrip: sender creates envelope -> recipient opens -> plaintext matches."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from calyx.mail import crypto, envelope, mailbox


def test_mail_roundtrip():
    """Test complete mail roundtrip: create -> verify -> decrypt."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Create temporary runtime directory
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Plaintext message
        plaintext = b"Hello, this is a test message!"
        subject = "Test Subject"
        
        # Create envelope
        env = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender_identity["signing_keypair"]["private"],
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
            subject=subject,
        )
        
        # Verify envelope structure
        assert "header" in env
        assert "ciphertext" in env
        assert "signature" in env
        assert env["header"]["subject"] == subject
        
        # Verify and decrypt
        decrypted = envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
        )
        
        # Plaintext should match
        assert decrypted == plaintext


def test_mail_roundtrip_with_mailbox():
    """Test roundtrip with mailbox operations (outbox -> inbox)."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    # Add sender to recipient's allowlist
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        sender_fp = crypto.compute_fingerprint(sender_identity["signing_keypair"]["public"])
        mailbox.save_allowlist(runtime_dir, [sender_fp])
        
        # Create envelope
        plaintext = b"Test message via mailbox"
        env = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender_identity["signing_keypair"]["private"],
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        # Write to outbox
        outbox_path = mailbox.write_outbox(env, runtime_dir)
        assert outbox_path.exists()
        
        # Deliver to inbox
        inbox_path = mailbox.deliver_to_inbox(
            env,
            runtime_dir,
            check_allowlist=True,
            check_replay=True,
        )
        assert inbox_path.exists()
        
        # List inbox
        inbox_list = mailbox.list_inbox(runtime_dir)
        assert len(inbox_list) == 1
        assert inbox_list[0]["header"]["msg_id"] == env["header"]["msg_id"]
        
        # Open envelope
        decrypted = envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
            allowlist_check=lambda fp: fp in mailbox.load_allowlist(runtime_dir),
            msg_id_seen_check=lambda mid: mid in mailbox.load_seen_cache(runtime_dir),
            timestamp_check=envelope.check_timestamp_window,
        )
        
        assert decrypted == plaintext
