"""Shared schemas for Coordinator (e1 event envelope, i1 intent object)"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class EventEnvelope:
    """Event envelope schema (e1) - Telemetry Intake → State Core"""
    
    timestamp: str  # ISO format
    source: str  # agent_scheduler, human, probe, etc.
    category: str  # status, metric, alert, completion
    payload: Dict[str, Any]
    confidence: float = 1.0  # 0.0 to 1.0
    version: str = "e1"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "category": self.category,
            "payload": self.payload,
            "confidence": self.confidence,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventEnvelope:
        return cls(
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            source=data["source"],
            category=data["category"],
            payload=data["payload"],
            confidence=data.get("confidence", 1.0),
            version=data.get("version", "e1")
        )


@dataclass
class Intent:
    """Intent object schema (i1) - Intent Pipeline queue"""
    
    id: str
    origin: str  # CBO, human, probe, playbook
    description: str
    required_capabilities: List[str]
    desired_outcome: str
    priority_hint: int = 50  # 0-100
    expiry: Optional[str] = None  # ISO format
    autonomy_required: str = "suggest"  # suggest, guide, execute
    risk: Dict[str, int] = field(default_factory=lambda: {"impact": 1, "likelihood": 1, "score": 2})
    similar_to: List[str] = field(default_factory=list)
    version: str = "i1"
    
    def calculate_priority(self, freshness_boost: float = 0.0) -> float:
        """Calculate priority score for intent
        
        Scoring: priority = priority_hint + 10*impact + 5*likelihood + freshness_boost
        """
        return (
            self.priority_hint +
            10 * self.risk.get("impact", 1) +
            5 * self.risk.get("likelihood", 1) +
            freshness_boost
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "origin": self.origin,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "desired_outcome": self.desired_outcome,
            "priority_hint": self.priority_hint,
            "expiry": self.expiry,
            "autonomy_required": self.autonomy_required,
            "risk": self.risk,
            "similar_to": self.similar_to,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Intent:
        return cls(
            id=data["id"],
            origin=data["origin"],
            description=data["description"],
            required_capabilities=data.get("required_capabilities", []),
            desired_outcome=data.get("desired_outcome", ""),
            priority_hint=data.get("priority_hint", 50),
            expiry=data.get("expiry"),
            autonomy_required=data.get("autonomy_required", "suggest"),
            risk=data.get("risk", {"impact": 1, "likelihood": 1, "score": 2}),
            similar_to=data.get("similar_to", []),
            version=data.get("version", "i1")
        )

