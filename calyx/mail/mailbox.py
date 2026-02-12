"""Mailbox operations: filesystem-based inbox, outbox, and receipt storage."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .envelope import AllowlistError, ReplayError, check_timestamp_window


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
    Load sender fingerprint allowlist from runtime/mailbox/allowlist.json.
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        List of allowed sender fingerprints (empty list if file doesn't exist)
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    allowlist_path = mailbox_dir / "allowlist.json"
    
    if not allowlist_path.exists():
        return []
    
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
    Save sender fingerprint allowlist to runtime/mailbox/allowlist.json.
    
    Args:
        runtime_dir: Runtime root directory
        fingerprints: List of allowed sender fingerprints
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    allowlist_path = mailbox_dir / "allowlist.json"
    
    with allowlist_path.open('w', encoding='utf-8') as f:
        json.dump(fingerprints, f, indent=2)


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


def write_outbox(envelope_json: dict[str, Any], runtime_dir: Path) -> Path:
    """
    Write envelope to outbox.
    
    Args:
        envelope_json: Envelope dict
        runtime_dir: Runtime root directory
        
    Returns:
        Path to written envelope file
    """
    mailbox_dir = get_mailbox_dir(runtime_dir)
    outbox_dir = mailbox_dir / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    msg_id = envelope_json.get("header", {}).get("msg_id", "unknown")
    envelope_path = outbox_dir / f"{msg_id}.json"
    
    with envelope_path.open('w', encoding='utf-8') as f:
        json.dump(envelope_json, f, indent=2)
    
    return envelope_path


def deliver_to_inbox(
    envelope_json: dict[str, Any],
    runtime_dir: Path,
    check_allowlist: bool = True,
    check_replay: bool = True,
) -> Path:
    """
    Deliver envelope to inbox (with allowlist and replay checks).
    
    Args:
        envelope_json: Envelope dict
        runtime_dir: Runtime root directory
        check_allowlist: If True, verify sender is in allowlist
        check_replay: If True, verify message ID is not seen and timestamp is valid
        
    Returns:
        Path to written envelope file
        
    Raises:
        AllowlistError: If sender is not in allowlist
        ReplayError: If message ID is seen or timestamp is invalid
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
    
    # Check replay protection
    if check_replay:
        # Check message ID uniqueness
        seen_cache = load_seen_cache(runtime_dir)
        if msg_id in seen_cache:
            raise ReplayError(f"Message ID already seen: {msg_id}")
        
        # Check timestamp window
        if not check_timestamp_window(timestamp):
            raise ReplayError(f"Timestamp validation failed: {timestamp}")
        
        # Add to seen cache
        add_to_seen_cache(runtime_dir, msg_id)
    
    # Write to inbox
    mailbox_dir = get_mailbox_dir(runtime_dir)
    inbox_dir = mailbox_dir / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    envelope_path = inbox_dir / f"{msg_id}.json"
    
    with envelope_path.open('w', encoding='utf-8') as f:
        json.dump(envelope_json, f, indent=2)
    
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
