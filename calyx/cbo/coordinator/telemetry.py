"""Telemetry Intake Layer - Event envelope ingestion and normalization"""

from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .schemas import EventEnvelope


class TelemetryIntake:
    """Collects and normalizes telemetry from various sources"""
    
    def __init__(self, root: Path):
        self.root = root
        self.outgoing_dir = root / "outgoing"
        self.logs_dir = root / "logs"
        self.cbo_lock = self.outgoing_dir / "cbo.lock"
        self.metrics_csv = self.logs_dir / "agent_metrics.csv"
        self.last_event_time: float = time.time()
        
    def ingest_recent_events(self, max_age_seconds: int = 300) -> List[EventEnvelope]:
        """Ingest recent events from various sources"""
        events = []
        now = time.time()
        
        # Read CBO heartbeat
        if self.cbo_lock.exists():
            try:
                with self.cbo_lock.open('r', encoding='utf-8') as f:
                    hb = json.load(f)
                    ts = hb.get('ts', 0)
                    if ts > (now - max_age_seconds):
                        events.append(EventEnvelope(
                            timestamp=datetime.fromtimestamp(ts).isoformat(),
                            source="cbo_overseer",
                            category="status",
                            payload={
                                "metrics": hb.get("metrics", {}),
                                "gates": hb.get("gates", {}),
                                "locks": hb.get("locks", {}),
                                "capacity": hb.get("capacity", {})
                            },
                            confidence=1.0
                        ))
            except Exception:
                pass
        
        # Read latest agent metrics
        events.extend(self._read_latest_metrics())
        
        return events
    
    def _read_latest_metrics(self) -> List[EventEnvelope]:
        """Read latest entries from agent_metrics.csv"""
        events = []
        
        if not self.metrics_csv.exists():
            return events
        
        try:
            import csv
            with self.metrics_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Get last 5 rows
                for row in rows[-5:]:
                    try:
                        tes = float(row.get('tes', 0))
                        events.append(EventEnvelope(
                            timestamp=row.get('iso_ts', datetime.now().isoformat()),
                            source="agent_scheduler",
                            category="metric",
                            payload={
                                "tes": tes,
                                "duration_s": float(row.get('duration_s', 0)),
                                "status": row.get('status', 'unknown'),
                                "changed_files": int(row.get('changed_files', 0)),
                                "autonomy_mode": row.get('autonomy_mode', 'safe')
                            },
                            confidence=0.9
                        ))
                    except (ValueError, KeyError):
                        continue
        except Exception:
            pass
        
        return events
    
    def ingest_from_file(self, file_path: Path, source: str) -> Optional[EventEnvelope]:
        """Ingest single event from a file"""
        if not file_path.exists():
            return None
        
        try:
            # Check modification time
            mtime = file_path.stat().st_mtime
            now = time.time()
            
            if mtime < (now - 300):  # Older than 5 minutes
                return None
            
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                
            return EventEnvelope(
                timestamp=datetime.fromtimestamp(mtime).isoformat(),
                source=source,
                category="status",
                payload=data,
                confidence=0.8
            )
        except Exception:
            return None

