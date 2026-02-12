#!/usr/bin/env python3
"""Calyx Mail v0 CLI: Local-first encrypted messaging."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

# Add calyx to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calyx.mail import crypto, envelope, mailbox


def cmd_keygen(args: argparse.Namespace) -> int:
    """Generate a new identity (signing + encryption keypairs)."""
    identity = crypto.generate_identity()
    
    keys_dir = mailbox.get_keys_dir(Path(args.runtime_dir))
    identity_name = args.identity or "default"
    
    # Save private keys
    signing_key_path = keys_dir / f"{identity_name}_signing.key"
    encryption_key_path = keys_dir / f"{identity_name}_encryption.key"
    
    signing_key_path.write_bytes(identity["signing_keypair"]["private"])
    encryption_key_path.write_bytes(identity["encryption_keypair"]["private"])
    
    # Set file permissions (0600 on Unix, no-op on Windows)
    try:
        os.chmod(signing_key_path, 0o600)
        os.chmod(encryption_key_path, 0o600)
    except AttributeError:
        pass  # Windows doesn't support chmod
    
    # Save public keys
    signing_pub_path = keys_dir / f"{identity_name}_signing.key.pub"
    encryption_pub_path = keys_dir / f"{identity_name}_encryption.key.pub"
    
    signing_pub_path.write_bytes(identity["signing_keypair"]["public"])
    encryption_pub_path.write_bytes(identity["encryption_keypair"]["public"])
    
    # Create public key bundle for sharing
    bundle = {
        "identity": identity_name,
        "signing_fp": identity["fingerprints"]["signing"],
        "signing_pub": base64.b64encode(identity["signing_keypair"]["public"]).decode('ascii'),
        "encryption_fp": identity["fingerprints"]["encryption"],
        "encryption_pub": base64.b64encode(identity["encryption_keypair"]["public"]).decode('ascii'),
    }
    bundle_path = keys_dir / f"{identity_name}_public_bundle.json"
    with bundle_path.open('w', encoding='utf-8') as f:
        json.dump(bundle, f, indent=2)
    
    print(f"Identity '{identity_name}' generated successfully")
    print(f"Signing fingerprint: {identity['fingerprints']['signing']}")
    print(f"Encryption fingerprint: {identity['fingerprints']['encryption']}")
    print(f"Public bundle: {bundle_path}")
    
    return 0


def cmd_send(args: argparse.Namespace) -> int:
    """Send an envelope (create and write to outbox)."""
    runtime_dir = Path(args.runtime_dir)
    keys_dir = mailbox.get_keys_dir(runtime_dir)
    
    # Load sender keys
    identity_name = args.identity or "default"
    signing_key_path = keys_dir / f"{identity_name}_signing.key"
    signing_pub_path = keys_dir / f"{identity_name}_signing.key.pub"
    
    if not signing_key_path.exists() or not signing_pub_path.exists():
        print(f"Error: Identity '{identity_name}' not found. Run 'keygen' first.", file=sys.stderr)
        return 1
    
    sender_signing_priv = signing_key_path.read_bytes()
    sender_signing_pub = signing_pub_path.read_bytes()
    
    # Load recipient public key bundle
    recipient_bundle_path = Path(args.to)
    if not recipient_bundle_path.exists():
        print(f"Error: Recipient bundle not found: {recipient_bundle_path}", file=sys.stderr)
        return 1
    
    with recipient_bundle_path.open('r', encoding='utf-8') as f:
        recipient_bundle = json.load(f)
    
    recipient_encryption_pub_b64 = recipient_bundle.get("encryption_pub")
    if not recipient_encryption_pub_b64:
        print("Error: Recipient bundle missing encryption_pub", file=sys.stderr)
        return 1
    
    recipient_encryption_pub = base64.b64decode(recipient_encryption_pub_b64)
    
    # Create envelope (v0.1)
    plaintext = args.body.encode('utf-8')
    env = envelope.create_envelope(
        plaintext=plaintext,
        sender_signing_priv=sender_signing_priv,
        sender_signing_pub=sender_signing_pub,
        recipient_encryption_pub=recipient_encryption_pub,
        subject=args.subject,
        protocol_version="0.1",  # v0.1 protocol
    )
    
    # Write to outbox
    outbox_path = mailbox.write_outbox(env, runtime_dir)
    print(f"Envelope written to: {outbox_path}")
    print(f"Message ID: {env['header']['msg_id']}")
    
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    """Open an envelope (verify and decrypt)."""
    runtime_dir = Path(args.runtime_dir)
    keys_dir = mailbox.get_keys_dir(runtime_dir)
    
    # Load envelope
    envelope_path = Path(args.in_file)
    if not envelope_path.exists():
        print(f"Error: Envelope file not found: {envelope_path}", file=sys.stderr)
        return 1
    
    with envelope_path.open('r', encoding='utf-8') as f:
        env = json.load(f)
    
    header = env.get("header", {})
    sender_fp = header.get("sender_fp")
    
    if not sender_fp:
        print("Error: Envelope missing sender_fp", file=sys.stderr)
        return 1
    
    # Load sender public key (need to find it by fingerprint)
    # For simplicity, assume we have the sender's public bundle
    # In a real implementation, we'd have a key directory lookup
    sender_bundle_path = args.sender_bundle
    if not sender_bundle_path:
        print("Error: --sender-bundle required to verify signature", file=sys.stderr)
        return 1
    
    sender_bundle_path = Path(sender_bundle_path)
    if not sender_bundle_path.exists():
        print(f"Error: Sender bundle not found: {sender_bundle_path}", file=sys.stderr)
        return 1
    
    with sender_bundle_path.open('r', encoding='utf-8') as f:
        sender_bundle = json.load(f)
    
    sender_signing_pub_b64 = sender_bundle.get("signing_pub")
    if not sender_signing_pub_b64:
        print("Error: Sender bundle missing signing_pub", file=sys.stderr)
        return 1
    
    sender_signing_pub = base64.b64decode(sender_signing_pub_b64)
    
    # Load recipient keys
    identity_name = args.identity or "default"
    encryption_key_path = keys_dir / f"{identity_name}_encryption.key"
    
    if not encryption_key_path.exists():
        print(f"Error: Identity '{identity_name}' not found. Run 'keygen' first.", file=sys.stderr)
        return 1
    
    recipient_encryption_priv = encryption_key_path.read_bytes()
    
    # Check allowlist
    allowlist = mailbox.load_allowlist(runtime_dir)
    allowlist_check = lambda fp: fp in allowlist
    
    # Initialize replay state (v0.1)
    from calyx.mail import replay
    replay_db_path = runtime_dir / "mailbox" / "replay_state.db"
    replay_state = replay.ReplayState(replay_db_path)
    
    timestamp_check = envelope.check_timestamp_window
    
    # Verify and decrypt
    try:
        plaintext = envelope.verify_and_open_envelope(
            env,
            sender_signing_pub,
            recipient_encryption_priv,
            allowlist_check=allowlist_check if allowlist else None,
            timestamp_check=timestamp_check,
        )
        
        # Deliver to inbox (v0.1 with replay state)
        mailbox.deliver_to_inbox(
            env,
            runtime_dir,
            replay_state=replay_state,
            check_allowlist=bool(allowlist),
            check_replay=True,
        )
        
        # Mark as delivered
        msg_id = header.get("msg_id")
        mailbox.mark_delivered_receipt(msg_id, "delivered", runtime_dir)
        
        # Output plaintext
        print(plaintext.decode('utf-8'))
        
        return 0
        
    except envelope.AllowlistError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except envelope.ReplayError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except envelope.VerificationError as e:
        print(f"Error: {e}", file=sys.stderr)
        mailbox.mark_delivered_receipt(header.get("msg_id", "unknown"), "failed", runtime_dir, str(e))
        return 1
    except crypto.DecryptionError as e:
        print(f"Error: {e}", file=sys.stderr)
        mailbox.mark_delivered_receipt(header.get("msg_id", "unknown"), "failed", runtime_dir, str(e))
        return 1


def cmd_inbox(args: argparse.Namespace) -> int:
    """List envelopes in inbox."""
    runtime_dir = Path(args.runtime_dir)
    envelopes = mailbox.list_inbox(runtime_dir)
    
    if not envelopes:
        print("Inbox is empty")
        return 0
    
    for env in envelopes:
        header = env.get("header", {})
        msg_id = header.get("msg_id", "unknown")
        sender_fp = header.get("sender_fp", "unknown")
        subject = header.get("subject", "(no subject)")
        timestamp = header.get("timestamp", "unknown")
        
        print(f"{msg_id[:8]}... | {sender_fp[:16]}... | {timestamp} | {subject}")
    
    return 0


def cmd_receipt(args: argparse.Namespace) -> int:
    """Mark receipt status for a message."""
    runtime_dir = Path(args.runtime_dir)
    msg_id = args.msg_id
    
    status = "delivered"
    if args.delivered:
        status = "delivered"
    elif args.read:
        status = "read"
    elif args.failed:
        status = "failed"
    
    error = args.error if args.failed else None
    
    receipt_path = mailbox.mark_delivered_receipt(msg_id, status, runtime_dir, error)
    print(f"Receipt written: {receipt_path}")
    
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Calyx Mail v0 CLI")
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory (default: runtime)",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # keygen
    keygen_parser = subparsers.add_parser("keygen", help="Generate a new identity")
    keygen_parser.add_argument("--identity", help="Identity name (default: default)")
    keygen_parser.set_defaults(func=cmd_keygen)
    
    # send
    send_parser = subparsers.add_parser("send", help="Send an envelope")
    send_parser.add_argument("--to", required=True, help="Path to recipient public bundle JSON")
    send_parser.add_argument("--subject", help="Subject line")
    send_parser.add_argument("--body", required=True, help="Message body")
    send_parser.add_argument("--identity", help="Sender identity name (default: default)")
    send_parser.set_defaults(func=cmd_send)
    
    # open
    open_parser = subparsers.add_parser("open", help="Open and decrypt an envelope")
    open_parser.add_argument("--in", dest="in_file", required=True, help="Path to envelope JSON file")
    open_parser.add_argument("--sender-bundle", required=True, help="Path to sender public bundle JSON")
    open_parser.add_argument("--identity", help="Recipient identity name (default: default)")
    open_parser.set_defaults(func=cmd_open)
    
    # inbox
    inbox_parser = subparsers.add_parser("inbox", help="List envelopes in inbox")
    inbox_parser.set_defaults(func=cmd_inbox)
    
    # receipt
    receipt_parser = subparsers.add_parser("receipt", help="Mark receipt status")
    receipt_parser.add_argument("--msg-id", required=True, help="Message ID")
    receipt_group = receipt_parser.add_mutually_exclusive_group(required=True)
    receipt_group.add_argument("--delivered", action="store_true", help="Mark as delivered")
    receipt_group.add_argument("--read", action="store_true", help="Mark as read")
    receipt_group.add_argument("--failed", action="store_true", help="Mark as failed")
    receipt_parser.add_argument("--error", help="Error message (required if --failed)")
    receipt_parser.set_defaults(func=cmd_receipt)
    
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    import os
    sys.exit(main())
