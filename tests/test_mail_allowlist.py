"""Test Calyx Mail allowlist: deny-by-default unless sender fingerprint allowlisted."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from calyx.mail import crypto, envelope, mailbox


def test_mail_allowlist_deny_by_default():
    """Test that sender not in allowlist is rejected."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Create envelope
        plaintext = b"Test message"
        env = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender_identity["signing_keypair"]["private"],
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        # Allowlist is empty (deny-by-default)
        allowlist = mailbox.load_allowlist(runtime_dir)
        assert len(allowlist) == 0
        
        sender_fp = crypto.compute_fingerprint(sender_identity["signing_keypair"]["public"])
        
        # Deliver should fail (allowlist check)
        with pytest.raises(mailbox.AllowlistError):
            mailbox.deliver_to_inbox(
                env,
                runtime_dir,
                check_allowlist=True,
                check_replay=False,  # Skip replay check for this test
            )
        
        # Verify should also fail with allowlist check
        with pytest.raises(envelope.AllowlistError):
            envelope.verify_and_open_envelope(
                env,
                sender_signing_pub=sender_identity["signing_keypair"]["public"],
                recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
                allowlist_check=lambda fp: fp in mailbox.load_allowlist(runtime_dir),
            )


def test_mail_allowlist_allow_sender():
    """Test that sender in allowlist is accepted."""
    # Generate identities
    sender_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Add sender to allowlist
        sender_fp = crypto.compute_fingerprint(sender_identity["signing_keypair"]["public"])
        mailbox.save_allowlist(runtime_dir, [sender_fp])
        
        # Verify allowlist
        allowlist = mailbox.load_allowlist(runtime_dir)
        assert sender_fp in allowlist
        
        # Create envelope
        plaintext = b"Test message"
        env = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender_identity["signing_keypair"]["private"],
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        # Deliver should succeed
        inbox_path = mailbox.deliver_to_inbox(
            env,
            runtime_dir,
            check_allowlist=True,
            check_replay=False,  # Skip replay check for this test
        )
        assert inbox_path.exists()
        
        # Verify and decrypt should succeed
        decrypted = envelope.verify_and_open_envelope(
            env,
            sender_signing_pub=sender_identity["signing_keypair"]["public"],
            recipient_encryption_priv=recipient_identity["encryption_keypair"]["private"],
            allowlist_check=lambda fp: fp in mailbox.load_allowlist(runtime_dir),
        )
        
        assert decrypted == plaintext


def test_mail_allowlist_multiple_senders():
    """Test allowlist with multiple senders."""
    # Generate identities
    sender1_identity = crypto.generate_identity()
    sender2_identity = crypto.generate_identity()
    sender3_identity = crypto.generate_identity()
    recipient_identity = crypto.generate_identity()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Add sender1 and sender2 to allowlist (not sender3)
        sender1_fp = crypto.compute_fingerprint(sender1_identity["signing_keypair"]["public"])
        sender2_fp = crypto.compute_fingerprint(sender2_identity["signing_keypair"]["public"])
        sender3_fp = crypto.compute_fingerprint(sender3_identity["signing_keypair"]["public"])
        
        mailbox.save_allowlist(runtime_dir, [sender1_fp, sender2_fp])
        
        # Create envelopes
        plaintext = b"Test message"
        
        env1 = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender1_identity["signing_keypair"]["private"],
            sender_signing_pub=sender1_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        env2 = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender2_identity["signing_keypair"]["private"],
            sender_signing_pub=sender2_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        env3 = envelope.create_envelope(
            plaintext=plaintext,
            sender_signing_priv=sender3_identity["signing_keypair"]["private"],
            sender_signing_pub=sender3_identity["signing_keypair"]["public"],
            recipient_encryption_pub=recipient_identity["encryption_keypair"]["public"],
        )
        
        # Sender1 should be allowed
        inbox_path1 = mailbox.deliver_to_inbox(
            env1,
            runtime_dir,
            check_allowlist=True,
            check_replay=False,
        )
        assert inbox_path1.exists()
        
        # Sender2 should be allowed
        inbox_path2 = mailbox.deliver_to_inbox(
            env2,
            runtime_dir,
            check_allowlist=True,
            check_replay=False,
        )
        assert inbox_path2.exists()
        
        # Sender3 should be rejected
        with pytest.raises(mailbox.AllowlistError):
            mailbox.deliver_to_inbox(
                env3,
                runtime_dir,
                check_allowlist=True,
                check_replay=False,
            )
