#!/usr/bin/env python3
"""Migration script: Convert Calyx Mail v0 mailbox to v0.1 format."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calyx.mail import codec, mailbox, replay


def migrate_inbox(runtime_dir: Path, backup: bool = True) -> int:
    """
    Migrate inbox from v0 (msg_id.json) to v0.1 (content_hash.json).
    
    Args:
        runtime_dir: Runtime root directory
        backup: If True, backup original files
        
    Returns:
        Number of files migrated
    """
    mailbox_dir = mailbox.get_mailbox_dir(runtime_dir)
    inbox_dir = mailbox_dir / "inbox"
    
    if not inbox_dir.exists():
        print("No inbox directory found")
        return 0
    
    # Backup if requested
    if backup:
        backup_dir = mailbox_dir / "inbox_backup_v0"
        if backup_dir.exists():
            print(f"Backup directory already exists: {backup_dir}")
        else:
            shutil.copytree(inbox_dir, backup_dir)
            print(f"Backed up inbox to: {backup_dir}")
    
    migrated_count = 0
    
    # Find all v0 files (msg_id.json format)
    for old_path in inbox_dir.glob("*.json"):
        # Skip if already v0.1 format (64-char hex filename)
        if len(old_path.stem) == 64 and all(c in "0123456789abcdef" for c in old_path.stem):
            continue  # Already migrated
        
        try:
            # Read envelope
            with old_path.open('r', encoding='utf-8') as f:
                envelope = json.load(f)
            
            # Compute content hash (v0.1)
            content_hash = codec.compute_envelope_hash(envelope)
            
            # New filename
            new_path = inbox_dir / f"{content_hash}.json"
            
            # Skip if already exists (duplicate content)
            if new_path.exists():
                print(f"Skipping duplicate: {old_path.name} -> {new_path.name}")
                old_path.unlink()  # Remove old file
                continue
            
            # Rename (atomic)
            old_path.rename(new_path)
            migrated_count += 1
            print(f"Migrated: {old_path.name} -> {new_path.name}")
            
        except Exception as e:
            print(f"Error migrating {old_path}: {e}")
            continue
    
    return migrated_count


def migrate_outbox(runtime_dir: Path, backup: bool = True) -> int:
    """
    Migrate outbox from v0 (msg_id.json) to v0.1 (content_hash.json).
    
    Args:
        runtime_dir: Runtime root directory
        backup: If True, backup original files
        
    Returns:
        Number of files migrated
    """
    mailbox_dir = mailbox.get_mailbox_dir(runtime_dir)
    outbox_dir = mailbox_dir / "outbox"
    
    if not outbox_dir.exists():
        print("No outbox directory found")
        return 0
    
    # Backup if requested
    if backup:
        backup_dir = mailbox_dir / "outbox_backup_v0"
        if backup_dir.exists():
            print(f"Backup directory already exists: {backup_dir}")
        else:
            shutil.copytree(outbox_dir, backup_dir)
            print(f"Backed up outbox to: {backup_dir}")
    
    migrated_count = 0
    
    # Find all v0 files (msg_id.json format)
    for old_path in outbox_dir.glob("*.json"):
        # Skip if already v0.1 format (64-char hex filename)
        if len(old_path.stem) == 64 and all(c in "0123456789abcdef" for c in old_path.stem):
            continue  # Already migrated
        
        try:
            # Read envelope
            with old_path.open('r', encoding='utf-8') as f:
                envelope = json.load(f)
            
            # Compute content hash (v0.1)
            content_hash = codec.compute_envelope_hash(envelope)
            
            # New filename
            new_path = outbox_dir / f"{content_hash}.json"
            
            # Skip if already exists (duplicate content)
            if new_path.exists():
                print(f"Skipping duplicate: {old_path.name} -> {new_path.name}")
                old_path.unlink()  # Remove old file
                continue
            
            # Rename (atomic)
            old_path.rename(new_path)
            migrated_count += 1
            print(f"Migrated: {old_path.name} -> {new_path.name}")
            
        except Exception as e:
            print(f"Error migrating {old_path}: {e}")
            continue
    
    return migrated_count


def migrate_replay_cache(runtime_dir: Path) -> int:
    """
    Migrate replay cache from v0 (JSON) to v0.1 (SQLite).
    
    Args:
        runtime_dir: Runtime root directory
        
    Returns:
        Number of entries migrated
    """
    mailbox_dir = mailbox.get_mailbox_dir(runtime_dir)
    cache_path = mailbox_dir / "seen_cache.json"
    
    if not cache_path.exists():
        print("No replay cache found (seen_cache.json)")
        return 0
    
    # Load v0 cache
    try:
        with cache_path.open('r', encoding='utf-8') as f:
            msg_ids = json.load(f)
    except Exception as e:
        print(f"Error loading replay cache: {e}")
        return 0
    
    if not isinstance(msg_ids, list):
        print("Replay cache is not a list")
        return 0
    
    # Initialize SQLite replay state
    db_path = mailbox_dir / "replay_state.db"
    replay_state = replay.ReplayState(db_path)
    
    migrated_count = 0
    
    # Migrate entries (requires access to original envelopes)
    # Note: v0 cache only has msg_ids, not replay_keys
    # We can't compute replay_keys without envelopes
    # So we'll create a migration marker and let the system rebuild
    
    print(f"Found {len(msg_ids)} entries in v0 replay cache")
    print("Note: Replay keys require original envelopes. Cache will be rebuilt on first use.")
    
    # Backup old cache
    backup_path = cache_path.with_suffix('.json.backup')
    shutil.copy(cache_path, backup_path)
    print(f"Backed up replay cache to: {backup_path}")
    
    return len(msg_ids)


def main() -> int:
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate Calyx Mail v0 mailbox to v0.1")
    parser.add_argument(
        "--runtime-dir",
        default="runtime",
        help="Runtime directory (default: runtime)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup of original files",
    )
    
    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir)
    
    if not runtime_dir.exists():
        print(f"Error: Runtime directory does not exist: {runtime_dir}")
        return 1
    
    print("=" * 60)
    print("Calyx Mail v0 -> v0.1 Migration")
    print("=" * 60)
    print()
    
    backup = not args.no_backup
    
    # Migrate inbox
    print("Migrating inbox...")
    inbox_count = migrate_inbox(runtime_dir, backup=backup)
    print(f"Inbox: {inbox_count} files migrated")
    print()
    
    # Migrate outbox
    print("Migrating outbox...")
    outbox_count = migrate_outbox(runtime_dir, backup=backup)
    print(f"Outbox: {outbox_count} files migrated")
    print()
    
    # Migrate replay cache
    print("Migrating replay cache...")
    replay_count = migrate_replay_cache(runtime_dir)
    print(f"Replay cache: {replay_count} entries found (will be rebuilt)")
    print()
    
    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
