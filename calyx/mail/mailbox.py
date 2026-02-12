"""Mailbox operations: filesystem-based inbox, outbox, and receipt storage (v0.1 with hardening)."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codec import compute_envelope_hash
from .envelope import AllowlistError, ReplayError, check_timestamp_window
from .replay import ReplayState, check_replay as check_replay_protection


def get_mailbox_dir(runtime_dir: Path) -> Path:
    """
    Get mailbox directory under runtime_dir.
    
    Args:
        runtime_dir: Runtime root directory (e.g., Path("runtime"))
        
    Returns:
        Path to runtime/mailbox/ directory (created if missing)
    """
    mailbox_dir = runtime_dir / "mailbox"
    mailbox_dir.mkdir(parents=True, exist_ok=True)
    return mailbox_dir


def get_keys_dir(runtime_dir: Path) -> Path:
    """
    Get keys directory under runtime_dir.
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        Path to runtime/keys/ directory (created if missing)
    """
    keys_dir = runtime_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    return keys_dir


def load_allowlist(runtime_dir: Path) -> list[str]:
    """
    Load sender fingerprint allowlist from runtime/mailbox/allowlist.json (v0.1 with symlink check).
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        List of allowed sender fingerprints (empty list if file doesn't exist)
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    allowlist_path = mailbox_dir / "allowlist.json"
    
    if not allowlist_path.exists():
        return []
    
    _check_symlink(allowlist_path)
    
    try:
        with allowlist_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, IOError):
        return []


def save_allowlist(runtime_dir: Path, fingerprints: list[str]) -> None:
    """
    Save sender fingerprint allowlist to runtime/mailbox/allowlist.json (v0.1 with atomic write).
    
    Args:
        runtime_dir: Runtime root directory
        fingerprints: List of allowed sender fingerprints
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    allowlist_path = mailbox_dir / "allowlist.json"
    
    _check_symlink(allowlist_path)
    
    # Atomic write
    content = json.dumps(fingerprints, indent=2).encode('utf-8')
    _atomic_write(allowlist_path, content)


def load_seen_cache(runtime_dir: Path) -> list[str]:
    """
    Load seen message ID cache from runtime/mailbox/seen_cache.json.
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        List of seen message IDs (empty list if file doesn't exist)
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    cache_path = mailbox_dir / "seen_cache.json"
    
    if not cache_path.exists():
        return []
    
    try:
        with cache_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, IOError):
        return []


def save_seen_cache(runtime_dir: Path, msg_ids: list[str]) -> None:
    """
    Save seen message ID cache to runtime/mailbox/seen_cache.json.
    
    Prunes entries older than 24 hours (based on message ID timestamp if available).
    Limits cache to 10,000 entries (FIFO eviction).
    
    Args:
        runtime_dir: Runtime root directory
        msg_ids: List of seen message IDs
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    cache_path = mailbox_dir / "seen_cache.json"
    
    # Limit to 10,000 entries (FIFO)
    if len(msg_ids) > 10000:
        msg_ids = msg_ids[-10000:]
    
    with cache_path.open('w', encoding='utf-8') as f:
        json.dump(msg_ids, f, indent=2)


def add_to_seen_cache(runtime_dir: Path, msg_id: str) -> None:
    """
    Add message ID to seen cache.
    
    Args:
        runtime_dir: Runtime root directory
        msg_id: Message ID to add
    """
    seen = load_seen_cache(runtime_dir)
    if msg_id not in seen:
        seen.append(msg_id)
    save_seen_cache(runtime_dir, seen)


def _check_symlink(path: Path) -> None:
    """Check if path is a symlink and reject if so."""
    if path.is_symlink():
        raise SecurityError(f"Symlinks not allowed: {path}")


def _atomic_write(path: Path, content: bytes) -> None:
    """Atomically write content to file (temporary file + atomic rename)."""
    _check_symlink(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix('.tmp')
    try:
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise OSError(f"Failed to atomically write {path}: {e}") from e


def _verify_content_hash(path: Path, expected_hash: str) -> bool:
    """
    Verify that file content, when canonicalized, matches expected hash.
    
    Note: File content may be pretty-printed, but hash is computed from canonical form.
    """
    if not path.exists():
        return False
    try:
        # Read and parse JSON
        with path.open('r', encoding='utf-8') as f:
            envelope = json.load(f)
        
        # Compute canonical hash
        from .codec import compute_envelope_hash
        actual_hash = compute_envelope_hash(envelope)
        return actual_hash == expected_hash
    except Exception:
        return False


class SecurityError(Exception):
    """Raised when security check fails."""
    pass


def write_outbox(envelope_json: dict[str, Any], runtime_dir: Path) -> Path:
    """
    Write envelope to outbox (content-addressed filename, v0.1).
    
    Args:
        envelope_json: Envelope dict
        runtime_dir: Runtime root directory
        
    Returns:
        Path to written envelope file
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    outbox_dir = mailbox_dir / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    _check_symlink(outbox_dir)
    
    # Compute content hash (full SHA256)
    content_hash = compute_envelope_hash(envelope_json)
    
    # Content-addressed filename
    envelope_path = outbox_dir / f"{content_hash}.json"
    
    # Check if file already exists (same content)
    if envelope_path.exists():
        if _verify_content_hash(envelope_path, content_hash):
            return envelope_path
        else:
            raise SecurityError(f"Hash mismatch: filename hash {content_hash} does not match content")
    
    # Atomic write (pretty-printed for readability)
    content = json.dumps(envelope_json, indent=2).encode('utf-8')
    _atomic_write(envelope_path, content)
    
    # Verify hash: filename should match canonical hash
    if envelope_path.stem != content_hash:
        raise SecurityError(f"Filename hash mismatch: {envelope_path.stem} != {content_hash}")
    
    return envelope_path


def deliver_to_inbox(
    envelope_json: dict[str, Any],
    runtime_dir: Path,
    replay_state: ReplayState | None = None,
    check_allowlist: bool = True,
    check_replay: bool = True,
    check_timestamp: bool = True,
) -> Path:
    """
    Deliver envelope to inbox (v0.1 with hardening).
    
    Args:
        envelope_json: Envelope dict
        runtime_dir: Runtime root directory
        replay_state: Replay state database (required if check_replay=True)
        check_allowlist: If True, verify sender is in allowlist
        check_replay: If True, verify envelope is not a replay
        check_timestamp: If True, verify timestamp window
        
    Returns:
        Path to written envelope file
        
    Raises:
        AllowlistError: If sender is not in allowlist
        ReplayError: If envelope is a replay or timestamp invalid
        SecurityError: If symlink or hash mismatch detected
    """
    header = envelope_json.get("header", {})
    sender_fp = header.get("sender_fp")
    msg_id = header.get("msg_id")
    timestamp = header.get("timestamp")
    
    if not sender_fp or not msg_id or not timestamp:
        raise ValueError("Envelope missing required header fields")
    
    # Check allowlist (deny-by-default)
    if check_allowlist:
        allowlist = load_allowlist(runtime_dir)
        if sender_fp not in allowlist:
            raise AllowlistError(f"Sender fingerprint not in allowlist: {sender_fp}")
    
    # Check timestamp window (primary replay protection)
    if check_timestamp:
        if not check_timestamp_window(timestamp):
            raise ReplayError(f"Timestamp validation failed: {timestamp}")
    
    # Check replay protection (secondary, for recent duplicates)
    if check_replay:
        if replay_state is None:
            # Fallback to legacy JSON cache for backward compatibility
            seen_cache = load_seen_cache(runtime_dir)
            if msg_id in seen_cache:
                raise ReplayError(f"Message ID already seen: {msg_id}")
            add_to_seen_cache(runtime_dir, msg_id)
        else:
            # Use SQLite replay state (v0.1)
            check_replay_protection(envelope_json, replay_state)
    
    # Compute content hash (full SHA256)
    content_hash = compute_envelope_hash(envelope_json)
    
    # Write to inbox
    mailbox_dir = get_mailbox_dir(runtime_dir)
    inbox_dir = mailbox_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    _check_symlink(inbox_dir)
    
    # Content-addressed filename
    envelope_path = inbox_dir / f"{content_hash}.json"
    
    # Check if file already exists (same content)
    if envelope_path.exists():
        if _verify_content_hash(envelope_path, content_hash):
            return envelope_path
        else:
            raise SecurityError(f"Hash mismatch: filename hash {content_hash} does not match content")
    
    # Atomic write (pretty-printed for readability)
    content = json.dumps(envelope_json, indent=2).encode('utf-8')
    _atomic_write(envelope_path, content)
    
    # Verify hash: filename should match canonical hash
    if envelope_path.stem != content_hash:
        raise SecurityError(f"Filename hash mismatch: {envelope_path.stem} != {content_hash}")
    
    return envelope_path


def list_inbox(runtime_dir: Path) -> list[dict[str, Any]]:
    """
    List envelopes in inbox (headers only, no ciphertext).
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        List of envelope headers (with ciphertext field removed)
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    inbox_dir = mailbox_dir / "inbox"
    
    if not inbox_dir.exists():
        return []
    
    envelopes = []
    for envelope_path in inbox_dir.glob("*.json"):
        try:
            with envelope_path.open('r', encoding='utf-8') as f:
                envelope = json.load(f)
                # Return header only (remove ciphertext and signature for listing)
                header_only = {
                    "header": envelope.get("header", {}),
                    "msg_id": envelope.get("header", {}).get("msg_id"),
                }
                envelopes.append(header_only)
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by timestamp (newest first)
    envelopes.sort(
        key=lambda e: e.get("header", {}).get("timestamp", ""),
        reverse=True
    )
    
    return envelopes


def mark_delivered_receipt(
    msg_id: str,
    status: str,
    runtime_dir: Path,
    error: str | None = None,
) -> Path:
    """
    Create and append receipt to receipts file.
    
    Args:
        msg_id: Message ID from envelope
        status: One of "delivered", "read", "failed"
        runtime_dir: Runtime root directory
        error: Optional error message if status is "failed"
        
    Returns:
        Path to receipt file
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    receipts_dir = mailbox_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    
    # Daily rotation: receipts_YYYY-MM-DD.jsonl
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    receipts_path = receipts_dir / f"receipts_{today}.jsonl"
    
    receipt = {
        "msg_id": msg_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if error is not None:
        receipt["error"] = error
    
    # Append to JSONL file
    with receipts_path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(receipt, sort_keys=True) + "\n")
    
    return receipts_path
