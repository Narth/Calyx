#!/usr/bin/env python3
"""
Dashboard Data Broker
Lightweight metrics broker between SVF and dashboard backend
Phase A - Backend Skeleton
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from threading import Thread

ROOT = Path(__file__).resolve().parents[2]


class MetricsBroker:
    """Lightweight broker for streaming metrics from SVF to dashboard"""
    
    def __init__(self):
        self.update_interval = 5  # seconds
        self.running = False
        self.latest_data = {}
    
    def start(self):
        """Start broker thread"""
        self.running = True
        thread = Thread(target=self._broker_loop, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop broker thread"""
        self.running = False
    
    def _broker_loop(self):
        """Main broker loop"""
        while self.running:
            try:
                # Collect metrics from SVF and agents
                data = self._collect_metrics()
                self.latest_data = data
                
                # Write to shared location for dashboard backend
                self._write_data(data)
                
            except Exception as e:
                print(f"Broker error: {e}")
            
            time.sleep(self.update_interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics from various sources"""
        from api.health import get_current_health
        from api.agents import list_agents
        from api.leases import list_active_leases
        from api.approvals import list_pending_approvals
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_health": get_current_health(),
            "agents": list_agents(),
            "leases": list_active_leases(),
            "approvals": list_pending_approvals()
        }
    
    def _write_data(self, data: Dict[str, Any]):
        """Write data to shared location"""
        output_file = ROOT / "outgoing" / "dashboard" / "metrics.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def get_latest(self) -> Dict[str, Any]:
        """Get latest metrics"""
        return self.latest_data


if __name__ == "__main__":
    broker = MetricsBroker()
    broker.start()
    print("Metrics broker started")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        broker.stop()
        print("Metrics broker stopped")

