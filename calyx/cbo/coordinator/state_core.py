"""State Core - Shared World Model for Station Calyx"""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import EventEnvelope, Intent


class StateCore:
    """Maintains shared operational picture"""
    
    def __init__(self, root: Path):
        self.root = root
        self.state_file = root / "state" / "coordinator_state.json"
        self.intents_file = root / "state" / "coordinator_intents.jsonl"
        self.history_file = root / "state" / "coordinator_history.jsonl"
        
        self._ensure_dirs()
        self._load_state()
    
    def _ensure_dirs(self):
        """Ensure state directories exist"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.intents_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        """Load persisted state"""
        try:
            with self.state_file.open('r', encoding='utf-8') as f:
                self.state = json.load(f)
        except Exception:
            self.state = {
                "last_updated": datetime.now().isoformat(),
                "resource_headroom": {},
                "gates": {},
                "agent_status": {},
                "tes_summary": {},
                "failure_streaks": {},
                "autonomy_mode": "suggest"
            }
    
    def save_state(self):
        """Persist current state"""
        self.state["last_updated"] = datetime.now().isoformat()
        try:
            with self.state_file.open('w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass
    
    def update_from_events(self, events: List[EventEnvelope]):
        """Update state from telemetry events"""
        for event in events:
            if event.source == "cbo_overseer":
                self._update_from_cbo(event.payload)
            elif event.source == "agent_scheduler":
                self._update_from_agent_metrics(event.payload)
        
        self.save_state()
    
    def _update_from_cbo(self, payload: Dict[str, Any]):
        """Update state from CBO heartbeat"""
        # Update gates
        if "gates" in payload:
            self.state["gates"] = payload["gates"]
        
        # Update resource headroom
        if "capacity" in payload:
            self.state["resource_headroom"] = payload["capacity"]
        
        # Update agent status from locks
        if "locks" in payload:
            self.state["agent_status"] = payload["locks"]
    
    def _update_from_agent_metrics(self, payload: Dict[str, Any]):
        """Update state from agent metrics"""
        tes = payload.get("tes", 0)
        status = payload.get("status", "unknown")
        
        # Update TES summary
        if "tes_summary" not in self.state:
            self.state["tes_summary"] = {}
        
        # Track failure streaks
        if status != "done":
            key = f"failure_{payload.get('autonomy_mode', 'unknown')}"
            self.state["failure_streaks"][key] = self.state["failure_streaks"].get(key, 0) + 1
        else:
            # Reset on success
            for key in list(self.state["failure_streaks"].keys()):
                if "failure_" in key:
                    self.state["failure_streaks"][key] = 0
    
    def get_resource_headroom(self) -> Dict[str, Any]:
        """Get current resource headroom"""
        return self.state.get("resource_headroom", {})
    
    def get_autonomy_mode(self) -> str:
        """Get current autonomy mode"""
        return self.state.get("autonomy_mode", "suggest")
    
    def set_autonomy_mode(self, mode: str):
        """Set autonomy mode"""
        self.state["autonomy_mode"] = mode
        self.save_state()
    
    def get_tes_summary(self) -> Dict[str, Any]:
        """Get TES summary"""
        return self.state.get("tes_summary", {})
    
    def check_guardrails(self) -> Dict[str, Any]:
        """Check guardrail thresholds"""
        headroom = self.get_resource_headroom()
        cpu = headroom.get("cpu_ok", True)
        mem = headroom.get("mem_ok", True)
        gpu = headroom.get("gpu_ok", True)
        
        violations = []
        
        if not cpu:
            violations.append("CPU headroom critical")
        if not mem:
            violations.append("RAM headroom critical")
        if not gpu:
            violations.append("GPU headroom critical")
        
        # Check failure streaks
        failure_streaks = self.state.get("failure_streaks", {})
        if any(count >= 3 for count in failure_streaks.values()):
            violations.append("Too many consecutive failures")
        
        return {
            "violations": violations,
            "ok": len(violations) == 0
        }

