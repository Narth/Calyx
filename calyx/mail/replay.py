"""Replay protection for Calyx Mail Protocol Layer v0.1."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .codec import compute_envelope_hash


class ReplayError(Exception):
    """Raised when replay is detected."""
    pass


class ReplayState:
    """
    Replay state database (SQLite) for tracking seen envelopes.
    
    Uses content-addressed replay keys (SHA256 of canonical envelope).
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize replay state database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database schema and hardening."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Enable WAL mode
            cursor.execute("PRAGMA journal_mode = WAL")
            
            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS replay_state (
                    replay_key TEXT PRIMARY KEY,
                    msg_id TEXT NOT NULL,
                    sender_fp TEXT NOT NULL,
                    recipient_fp TEXT NOT NULL,
                    seen_at TIMESTAMP NOT NULL,
                    envelope_timestamp TEXT NOT NULL,
                    UNIQUE(replay_key)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_seen_at 
                ON replay_state(seen_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_msg_id 
                ON replay_state(msg_id)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def has_replay_key(self, replay_key: str) -> bool:
        """
        Check if replay key exists in database.
        
        Args:
            replay_key: Full SHA256 hash (64 hex chars)
            
        Returns:
            True if replay key exists, False otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM replay_state WHERE replay_key = ?",
                (replay_key,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def add_replay_key(
        self,
        replay_key: str,
        msg_id: str,
        sender_fp: str,
        recipient_fp: str,
        envelope_timestamp: str,
    ) -> None:
        """
        Add replay key to database (atomic transaction).
        
        Args:
            replay_key: Full SHA256 hash (64 hex chars)
            msg_id: Message ID (UUID v4)
            sender_fp: Sender fingerprint
            recipient_fp: Recipient fingerprint
            envelope_timestamp: Original envelope timestamp (ISO 8601)
            
        Raises:
            ReplayError: If replay key already exists
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            
            # Check if already exists
            if self.has_replay_key(replay_key):
                raise ReplayError(f"Replay key already exists: {replay_key}")
            
            # Insert (atomic transaction)
            seen_at = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO replay_state 
                (replay_key, msg_id, sender_fp, recipient_fp, seen_at, envelope_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (replay_key, msg_id, sender_fp, recipient_fp, seen_at, envelope_timestamp))
            
            conn.commit()
        except sqlite3.IntegrityError as e:
            raise ReplayError(f"Replay key already exists: {replay_key}") from e
        finally:
            conn.close()
    
    def prune_old_entries(self, retention_hours: int = 24) -> int:
        """
        Prune replay state entries older than retention_hours.
        
        Args:
            retention_hours: Retention window in hours (default: 24)
            
        Returns:
            Number of entries pruned
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
            
            cursor.execute(
                "DELETE FROM replay_state WHERE seen_at < ?",
                (cutoff_time,)
            )
            
            pruned_count = cursor.rowcount
            conn.commit()
            
            return pruned_count
        finally:
            conn.close()
    
    def get_replay_key_by_msg_id(self, msg_id: str) -> Optional[str]:
        """
        Get replay key by message ID (for receipt correlation).
        
        Args:
            msg_id: Message ID (UUID v4)
            
        Returns:
            Replay key if found, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT replay_key FROM replay_state WHERE msg_id = ?",
                (msg_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()


def check_replay(envelope: dict, replay_state: ReplayState) -> None:
    """
    Check if envelope is a replay.
    
    Args:
        envelope: Envelope dict
        replay_state: Replay state database
        
    Raises:
        ReplayError: If replay is detected
    """
    # Compute replay key (full SHA256)
    replay_key = compute_envelope_hash(envelope)
    
    # Check replay state
    if replay_state.has_replay_key(replay_key):
        raise ReplayError(f"Envelope already seen: {replay_key[:16]}...")
    
    # Add to replay state
    header = envelope.get("header", {})
    replay_state.add_replay_key(
        replay_key=replay_key,
        msg_id=header.get("msg_id", ""),
        sender_fp=header.get("sender_fp", ""),
        recipient_fp=header.get("recipient_fp", ""),
        envelope_timestamp=header.get("timestamp", ""),
    )
