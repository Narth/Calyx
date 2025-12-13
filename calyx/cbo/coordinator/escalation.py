"""Human Escalation - Stall detection and cockpit interface"""

from __future__ import annotations
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import Intent


class EscalationManager:
    """Manages human escalation for stalled executions"""
    
    def __init__(self, root: Path):
        self.root = root
        self.stall_threshold = 900  # 15 minutes
        self.escalation_dir = root / "outgoing" / "escalations"
        self.escalation_dir.mkdir(parents=True, exist_ok=True)
        self.execution_trackers: Dict[str, float] = {}  # intent_id -> start_time
    
    def track_execution(self, intent_id: str):
        """Track when an execution starts"""
        self.execution_trackers[intent_id] = time.time()
    
    def check_stalls(self) -> List[Dict[str, Any]]:
        """Check for stalled executions"""
        stalls = []
        now = time.time()
        
        for intent_id, start_time in list(self.execution_trackers.items()):
            elapsed = now - start_time
            
            if elapsed > self.stall_threshold:
                stalls.append({
                    "intent_id": intent_id,
                    "elapsed_minutes": elapsed / 60,
                    "status": "stalled"
                })
        
        return stalls
    
    def escalate(self, intent: Intent, reason: str) -> str:
        """Create human escalation request"""
        escalation_id = f"esc-{int(time.time())}"
        
        escalation = {
            "id": escalation_id,
            "timestamp": datetime.now().isoformat(),
            "intent": intent.to_dict(),
            "reason": reason,
            "severity": "medium",
            "action_required": "human_decision",
            "resolved": False
        }
        
        escalation_file = self.escalation_dir / f"{escalation_id}.json"
        escalation_file.write_text(json.dumps(escalation, indent=2), encoding='utf-8')
        
        return escalation_id
    
    def resolve_escalation(self, escalation_id: str, decision: str):
        """Resolve an escalation with human decision"""
        escalation_file = self.escalation_dir / f"{escalation_id}.json"
        
        if not escalation_file.exists():
            return False
        
        try:
            escalation = json.loads(escalation_file.read_text(encoding='utf-8'))
            escalation["resolved"] = True
            escalation["resolution"] = decision
            escalation["resolved_at"] = datetime.now().isoformat()
            
            escalation_file.write_text(json.dumps(escalation, indent=2), encoding='utf-8')
            return True
        except Exception:
            return False
    
    def get_active_escalations(self) -> List[Dict[str, Any]]:
        """Get active (unresolved) escalations"""
        escalations = []
        
        for escalation_file in self.escalation_dir.glob("esc-*.json"):
            try:
                escalation = json.loads(escalation_file.read_text(encoding='utf-8'))
                if not escalation.get("resolved", False):
                    escalations.append(escalation)
            except Exception:
                pass
        
        return escalations

