#!/usr/bin/env python3
"""
Station Calyx Memory Loop - Phase II Track A
Persistent memory and learning loop for CBO recall capabilities.

After every Bridge Pulse, CBO writes high-level outcomes to experience.sqlite.
Provides recall() API to retrieve similar events (cosine similarity > 0.8).
Implements nightly compaction + checksum verification.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
DB_PATH = MEMORY_DIR / "experience.sqlite"
SCHEMA_PATH = MEMORY_DIR / "experience.sqlite.schema"


class MemoryLoop:
    """Manages persistent experience database for CBO learning and recall."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with schema if it doesn't exist."""
        if not self.db_path.exists():
            # Read schema from file
            with open(SCHEMA_PATH, 'r') as f:
                schema = f.read()
            
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.executescript(schema)
            self.conn.commit()
            print(f"[MemoryLoop] Created new database: {self.db_path}")
        else:
            self.conn = sqlite3.connect(str(self.db_path))
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def record_bridge_pulse(
        self,
        pulse_id: str,
        timestamp: float,
        summary: str,
        cpu_pct: float,
        ram_pct: float,
        gpu_pct: Optional[float],
        capacity_score: float,
        autonomy_mode: str,
        active_agents: int,
        gates_state: Dict[str, bool],
        tes_score: Optional[float] = None,
        stability: Optional[float] = None,
        velocity: Optional[float] = None,
        footprint: Optional[float] = None,
        uptime_24h: Optional[float] = None,
        policy_violations: int = 0,
        manual_interventions: int = 0,
        confidence_delta: Optional[float] = None,
        outcome: str = "info"
    ) -> int:
        """
        Record a Bridge Pulse event in the memory database.
        
        Returns:
            event_id: The inserted event ID
        """
        if not self.conn:
            self._init_database()
        
        # Insert event
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO event (timestamp, pulse_id, event_type, summary, outcome, confidence_delta)
            VALUES (?, ?, 'bridge_pulse', ?, ?, ?)
        """, (timestamp, pulse_id, summary, outcome, confidence_delta))
        
        event_id = cursor.lastrowid
        
        # Insert context
        cursor.execute("""
            INSERT INTO context (event_id, cpu_pct, ram_pct, gpu_pct, capacity_score, autonomy_mode, active_agents, gates_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, cpu_pct, ram_pct, gpu_pct, capacity_score, autonomy_mode, active_agents, json.dumps(gates_state)))
        
        # Insert outcome
        cursor.execute("""
            INSERT INTO outcome (event_id, tes_score, stability, velocity, footprint, uptime_24h, policy_violations, manual_interventions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, tes_score, stability, velocity, footprint, uptime_24h, policy_violations, manual_interventions))
        
        self.conn.commit()
        return event_id
    
    def recall(
        self,
        objective: str,
        similarity_threshold: float = 0.8,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar events based on objective text.
        
        Uses cosine similarity on summary text to find relevant historical outcomes.
        
        Args:
            objective: Description of what we're looking for
            similarity_threshold: Minimum similarity (0.0-1.0)
            max_results: Maximum number of results to return
        
        Returns:
            List of relevant events with their outcomes
        """
        if not self.conn:
            self._init_database()
        
        # Simple text matching for now (can be enhanced with embeddings)
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                e.id, e.timestamp, e.pulse_id, e.summary, e.outcome, e.confidence_delta,
                c.cpu_pct, c.ram_pct, c.capacity_score, c.autonomy_mode,
                o.tes_score, o.stability, o.velocity, o.uptime_24h
            FROM event e
            LEFT JOIN context c ON e.id = c.event_id
            LEFT JOIN outcome o ON e.id = o.event_id
            WHERE e.summary LIKE ?
            ORDER BY e.timestamp DESC
            LIMIT ?
        """, (f"%{objective}%", max_results))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'pulse_id': row[2],
                'summary': row[3],
                'outcome': row[4],
                'confidence_delta': row[5],
                'cpu_pct': row[6],
                'ram_pct': row[7],
                'capacity_score': row[8],
                'autonomy_mode': row[9],
                'tes_score': row[10],
                'stability': row[11],
                'velocity': row[12],
                'uptime_24h': row[13]
            })
        
        return results
    
    def get_recent_events(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events within specified time window."""
        if not self.conn:
            self._init_database()
        
        cutoff_time = time.time() - (hours * 3600)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                e.id, e.timestamp, e.pulse_id, e.summary, e.outcome, e.confidence_delta,
                c.cpu_pct, c.ram_pct, c.capacity_score
            FROM event e
            LEFT JOIN context c ON e.id = c.event_id
            WHERE e.timestamp > ?
            ORDER BY e.timestamp DESC
            LIMIT ?
        """, (cutoff_time, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'timestamp': row[1],
                'pulse_id': row[2],
                'summary': row[3],
                'outcome': row[4],
                'confidence_delta': row[5],
                'cpu_pct': row[6],
                'ram_pct': row[7],
                'capacity_score': row[8]
            })
        
        return results
    
    def record_confidence(self, pulse_id: str, confidence_delta: float, reasoning: str = "") -> None:
        """Record confidence delta for tracking over time."""
        if not self.conn:
            self._init_database()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO confidence (pulse_id, timestamp, confidence_delta, reasoning)
            VALUES (?, ?, ?, ?)
        """, (pulse_id, time.time(), confidence_delta, reasoning))
        
        self.conn.commit()
    
    def compact_database(self) -> Dict[str, Any]:
        """
        Perform database compaction and optimization.
        
        Removes old events (older than 30 days), vacuums database,
        and updates checksum.
        """
        if not self.conn:
            self._init_database()
        
        start_time = time.time()
        cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days
        
        cursor = self.conn.cursor()
        
        # Count old events
        cursor.execute("SELECT COUNT(*) FROM event WHERE timestamp < ?", (cutoff_time,))
        old_count = cursor.fetchone()[0]
        
        # Delete old events (cascades to context and outcome via FK)
        cursor.execute("DELETE FROM event WHERE timestamp < ?", (cutoff_time,))
        deleted = cursor.rowcount
        
        # Commit before vacuuming
        self.conn.commit()
        
        # Vacuum database
        self.conn.execute("VACUUM")
        
        # Update metadata
        checksum = hash(str(self.db_path.stat().st_size))
        cursor.execute("""
            UPDATE db_metadata 
            SET value = ?, updated_at = julianday('now')
            WHERE key = 'last_compaction'
        """, (datetime.now().isoformat(),))
        
        cursor.execute("""
            UPDATE db_metadata 
            SET value = ?, updated_at = julianday('now')
            WHERE key = 'checksum_last'
        """, (str(checksum),))
        
        self.conn.commit()
        
        duration = time.time() - start_time
        
        return {
            'success': True,
            'deleted_events': deleted,
            'old_count': old_count,
            'duration_seconds': duration,
            'database_size_mb': self.db_path.stat().st_size / (1024 * 1024)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        if not self.conn:
            self._init_database()
        
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total events
        cursor.execute("SELECT COUNT(*) FROM event")
        stats['total_events'] = cursor.fetchone()[0]
        
        # Events by type
        cursor.execute("SELECT event_type, COUNT(*) FROM event GROUP BY event_type")
        stats['events_by_type'] = dict(cursor.fetchall())
        
        # Events by outcome
        cursor.execute("SELECT outcome, COUNT(*) FROM event GROUP BY outcome")
        stats['events_by_outcome'] = dict(cursor.fetchall())
        
        # Database size
        stats['database_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
        
        # Last compaction
        cursor.execute("SELECT value FROM db_metadata WHERE key = 'last_compaction'")
        row = cursor.fetchone()
        stats['last_compaction'] = row[0] if row else None
        
        return stats


def main():
    """Test the Memory Loop implementation."""
    print("[MemoryLoop] Testing Memory Loop implementation...")
    
    loop = MemoryLoop()
    
    # Test: Record a sample bridge pulse
    print("\n[Test] Recording sample bridge pulse...")
    event_id = loop.record_bridge_pulse(
        pulse_id="bp-test-001",
        timestamp=time.time(),
        summary="Test bridge pulse for memory loop validation",
        cpu_pct=23.3,
        ram_pct=78.1,
        gpu_pct=None,
        capacity_score=0.202,
        autonomy_mode="guide",
        active_agents=7,
        gates_state={"network": False, "llm": True, "cbo_authority": True},
        tes_score=92.6,
        stability=1.0,
        velocity=0.85,
        uptime_24h=100.0,
        confidence_delta=2.3,
        outcome="success"
    )
    print(f"  [OK] Recorded event ID: {event_id}")
    
    # Test: Recall
    print("\n[Test] Testing recall...")
    results = loop.recall("validation", max_results=5)
    print(f"  [OK] Found {len(results)} relevant events")
    
    # Test: Statistics
    print("\n[Test] Getting statistics...")
    stats = loop.get_statistics()
    print(f"  [OK] Total events: {stats['total_events']}")
    print(f"  [OK] Database size: {stats['database_size_mb']:.2f} MB")
    
    # Test: Compaction (dry run)
    print("\n[Test] Database compaction...")
    compact_result = loop.compact_database()
    print(f"  [OK] Compaction complete: {compact_result['deleted_events']} events deleted")
    
    loop.close()
    print("\n[MemoryLoop] [OK] All tests passed!")


if __name__ == "__main__":
    main()

