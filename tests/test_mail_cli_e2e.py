"""End-to-end CLI test: keygen → send → deliver/open → receipt."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def test_cli_e2e():
    """Test complete CLI workflow: keygen → send → open → receipt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime_dir = Path(tmpdir)
        
        # Step 1: Generate sender identity
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "keygen",
                "--identity", "sender"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"keygen failed: {result.stderr}"
        
        # Step 2: Generate recipient identity
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "keygen",
                "--identity", "recipient"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"keygen failed: {result.stderr}"
        
        # Step 3: Load recipient public bundle
        recipient_bundle_path = runtime_dir / "keys" / "recipient_public_bundle.json"
        assert recipient_bundle_path.exists()
        
        with recipient_bundle_path.open('r') as f:
            recipient_bundle = json.load(f)
        recipient_fp = recipient_bundle["encryption_fp"]
        
        # Step 4: Add sender to recipient's allowlist
        sender_bundle_path = runtime_dir / "keys" / "sender_public_bundle.json"
        with sender_bundle_path.open('r') as f:
            sender_bundle = json.load(f)
        sender_fp = sender_bundle["signing_fp"]
        
        allowlist_path = runtime_dir / "mailbox" / "allowlist.json"
        allowlist_path.parent.mkdir(parents=True, exist_ok=True)
        with allowlist_path.open('w') as f:
            json.dump([sender_fp], f)
        
        # Step 5: Send envelope
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "send",
                "--identity", "sender",
                "--to", str(recipient_bundle_path),
                "--subject", "Test Subject",
                "--body", "Hello, this is a test message!"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"send failed: {result.stderr}"
        
        # Step 6: Find envelope in outbox
        outbox_dir = runtime_dir / "mailbox" / "outbox"
        assert outbox_dir.exists()
        envelope_files = list(outbox_dir.glob("*.json"))
        assert len(envelope_files) == 1
        envelope_path = envelope_files[0]
        
        # Step 7: Open envelope (deliver to inbox and decrypt)
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "open",
                "--in", str(envelope_path),
                "--sender-bundle", str(sender_bundle_path),
                "--identity", "recipient"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"open failed: {result.stderr}"
        assert "Hello, this is a test message!" in result.stdout
        
        # Step 8: List inbox
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "inbox"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "Test Subject" in result.stdout
        
        # Step 9: Mark receipt as read
        # Extract msg_id from envelope
        with envelope_path.open('r') as f:
            envelope = json.load(f)
        msg_id = envelope["header"]["msg_id"]
        
        result = subprocess.run(
            [
                "python", "-m", "tools.calyx_mail",
                "--runtime-dir", str(runtime_dir),
                "receipt",
                "--msg-id", msg_id,
                "--read"
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"receipt failed: {result.stderr}"
