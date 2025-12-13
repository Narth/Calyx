#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequence Manager - Monotonic counter persistence for evidence envelopes.

Maintains a strictly monotonic sequence number per node, persisted across restarts.
Thread-safe for concurrent access within a single process.

[CBO Governance]: Sequence numbers are the backbone of chronological continuity.
They MUST be strictly monotonic (never decrement, never skip) to ensure evidence
chain integrity across all Station Calyx instances.

Usage:
    from station_calyx.node import SequenceManager
    
    seq_mgr = SequenceManager()
    seq = seq_mgr.next()  # Returns 1, 2, 3, ...
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
SEQUENCE_DIR = ROOT / "outgoing" / "node"
SEQUENCE_FILE = SEQUENCE_DIR / "sequence.json"


class SequenceManager:
    """
    Thread-safe monotonic sequence counter with disk persistence.

    [CBO Governance]: This class guarantees:
    - Strictly monotonic increments (1, 2, 3, ...)
    - Persistence across process restarts
    - Thread-safe access within a single process
    - Atomic disk writes to prevent corruption
    """
    
    def __init__(self, sequence_file: Optional[Path] = None):
        """
        Initialize sequence manager.
        
        Args:
            sequence_file: Path to sequence persistence file 
                          (default: outgoing/node/sequence.json)
        """
        self.sequence_file = sequence_file or SEQUENCE_FILE
        self._lock = threading.Lock()
        self._current = self._load()
    
    def _load(self) -> int:
        """Load last sequence from disk."""
        if not self.sequence_file.exists():
            return 0
        
        try:
            data = json.loads(self.sequence_file.read_text(encoding="utf-8"))
            seq = int(data.get("seq", 0))
            return seq
        except Exception as e:
            print(f"[WARN] Failed to load sequence, starting from 0: {e}")
            return 0
    
    def _save(self) -> None:
        """Persist current sequence to disk (atomic write)."""
        self.sequence_file.parent.mkdir(parents=True, exist_ok=True)
        
        data: Dict[str, Any] = {
            "seq": self._current,
            "updated_at": datetime.now().isoformat(),
        }
        
        # Atomic write via temp file
        temp_path = self.sequence_file.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        temp_path.replace(self.sequence_file)
    
    def next(self) -> int:
        """
        Get next sequence number (atomic increment + persist).

        [CBO Governance]: This is the ONLY method that should increment
        the sequence. It guarantees strict monotonicity.

        Returns:
            Next sequence number (1, 2, 3, ...)
        """
        with self._lock:
            self._current += 1
            self._save()
            return self._current
    
    def current(self) -> int:
        """
        Get current sequence number without incrementing.
        
        Returns:
            Current sequence number (last assigned)
        """
        with self._lock:
            return self._current
    
    def reset(self, value: int = 0) -> None:
        """
        Reset sequence to specific value.

        [CBO WARNING]: Use with extreme caution. Resetting sequence
        breaks chronological continuity and invalidates hash chains.
        Only use for testing or disaster recovery.

        Args:
            value: New sequence value (default: 0)
        """
        with self._lock:
            self._current = value
            self._save()
            print(f"[WARN] Sequence reset to {value} - chain continuity broken")


if __name__ == "__main__":
    # CLI test - demonstrates monotonicity
    seq_mgr = SequenceManager()
    print(f"Current sequence: {seq_mgr.current()}")
    
    print("Generating 5 sequence numbers:")
    for i in range(5):
        seq = seq_mgr.next()
        print(f"  seq={seq}")
    
    print(f"Final sequence: {seq_mgr.current()}")
    
    # Simulate restart
    print("\nSimulating restart (new SequenceManager instance):")
    seq_mgr2 = SequenceManager()
    print(f"Loaded sequence: {seq_mgr2.current()}")
    print(f"Next after restart: {seq_mgr2.next()}")
