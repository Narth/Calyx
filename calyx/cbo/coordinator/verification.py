"""Verification & Learning Loop - Validates execution and learns from outcomes"""

from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import Intent


class VerificationLoop:
    """Validates execution results and updates confidence"""
    
    def __init__(self, root: Path):
        self.root = root
        self.history_file = root / "state" / "coordinator_history.jsonl"
        self.confidence_file = root / "state" / "coordinator_confidence.json"
        self.confidence: Dict[str, float] = {}
        self._load_confidence()
    
    def _load_confidence(self):
        """Load confidence scores"""
        try:
            with self.confidence_file.open('r', encoding='utf-8') as f:
                self.confidence = json.load(f)
        except Exception:
            self.confidence = {}
    
    def _save_confidence(self):
        """Save confidence scores"""
        try:
            with self.confidence_file.open('w', encoding='utf-8') as f:
                json.dump(self.confidence, f, indent=2)
        except Exception:
            pass
    
    def verify_execution(self, intent: Intent, result: Dict[str, Any]) -> Dict[str, Any]:
        """Verify execution result against intent"""
        # Simple success check based on desired outcome
        success = False
        
        # Check if desired outcome was achieved
        if "status" in result:
            success = result["status"] == "done"
        
        # Update confidence (cap updates to prevent runaway)
        capability_key = intent.required_capabilities[0] if intent.required_capabilities else "unknown"
        current_conf = self.confidence.get(capability_key, 0.8)
        
        if success:
            # Reward success (but don't over-reward)
            new_conf = min(1.0, current_conf + 0.02)
        else:
            # Penalize failure (but don't over-penalize)
            new_conf = max(0.3, current_conf - 0.05)
        
        self.confidence[capability_key] = new_conf
        self._save_confidence()
        
        # Log to history
        self._log_history(intent, result, success)
        
        return {
            "success": success,
            "confidence": new_conf,
            "capability": capability_key
        }
    
    def _log_history(self, intent: Intent, result: Dict[str, Any], success: bool):
        """Log execution to history"""
        try:
            with self.history_file.open('a', encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "intent_id": intent.id,
                    "intent_description": intent.description,
                    "result": result,
                    "success": success
                }
                f.write(json.dumps(entry) + '\n')
        except Exception:
            pass
    
    def get_confidence(self, capability: str) -> float:
        """Get confidence score for a capability"""
        return self.confidence.get(capability, 0.8)
    
    def get_all_confidence(self) -> Dict[str, float]:
        """Get all confidence scores"""
        return self.confidence.copy()

