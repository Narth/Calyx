"""
Station Calyx User Intent Model
===============================

Captures declared user intent and advisory profile preferences.

INVARIANT: HUMAN_PRIMACY
- Intent informs advisory framing only
- No automated actions based on intent
- User explicitly declares preferences

Role: core/intent
Scope: User intent storage, retrieval, and logging
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .evidence import append_event, create_event
from .config import get_config

COMPONENT_ROLE = "intent_manager"
COMPONENT_SCOPE = "user intent declaration and profile management"


class AdvisoryProfile(Enum):
    """
    Advisory profiles that influence framing of recommendations.
    
    These profiles affect HOW advice is presented, not WHAT data is collected.
    No execution capability is granted by any profile.
    
    Available profiles:
    - STABILITY_FIRST: Prioritize system stability and uptime
    - PERFORMANCE_SENSITIVE: Focus on performance metrics and responsiveness
    - RESOURCE_CONSTRAINED: Limited compute/memory resources
    - STORAGE_PRESSURE: High disk usage, storage-focused monitoring
    - DEVELOPER_WORKSTATION: Development environment with dev tools
    """
    STABILITY_FIRST = "stability_first"
    PERFORMANCE_SENSITIVE = "performance_sensitive"
    RESOURCE_CONSTRAINED = "resource_constrained"
    STORAGE_PRESSURE = "storage_pressure"
    DEVELOPER_WORKSTATION = "developer_workstation"
    
    @classmethod
    def from_string(cls, value: str) -> "AdvisoryProfile":
        """Parse profile from string (case-insensitive)."""
        normalized = value.lower().replace("-", "_").replace(" ", "_")
        for profile in cls:
            if profile.value == normalized or profile.name.lower() == normalized:
                return profile
        raise ValueError(f"Unknown advisory profile: {value}. Valid: {[p.name for p in cls]}")
    
    def get_framing_guidance(self) -> dict[str, Any]:
        """Return framing guidance for this profile."""
        guidance = {
            AdvisoryProfile.STABILITY_FIRST: {
                "priority": "system stability and reliability",
                "tone": "conservative",
                "risk_tolerance": "low",
                "emphasis": ["uptime", "error prevention", "gradual changes"],
                "avoid": ["aggressive optimizations", "experimental changes"],
            },
            AdvisoryProfile.PERFORMANCE_SENSITIVE: {
                "priority": "performance and responsiveness",
                "tone": "optimization-focused",
                "risk_tolerance": "medium",
                "emphasis": ["latency", "throughput", "resource efficiency"],
                "avoid": ["unnecessary overhead", "blocking operations"],
            },
            AdvisoryProfile.RESOURCE_CONSTRAINED: {
                "priority": "resource conservation",
                "tone": "efficiency-focused",
                "risk_tolerance": "low",
                "emphasis": ["memory usage", "disk space", "CPU efficiency"],
                "avoid": ["resource-heavy operations", "unnecessary processes"],
            },
            AdvisoryProfile.STORAGE_PRESSURE: {
                "priority": "storage capacity and usage",
                "tone": "cautious",
                "risk_tolerance": "medium",
                "emphasis": ["disk usage trends", "cleanup recommendations", "archive suggestions"],
                "avoid": ["filling up disk", "ignoring storage alerts"],
            },
            AdvisoryProfile.DEVELOPER_WORKSTATION: {
                "priority": "development workflow support",
                "tone": "balanced",
                "risk_tolerance": "medium",
                "emphasis": ["IDE performance", "build times", "tool availability"],
                "avoid": ["workflow interruptions", "unexpected restarts"],
            },
        }
        return guidance.get(self, {})


@dataclass
class UserIntent:
    """
    Declared user intent for advisory context.
    
    This model captures what the user cares about, enabling
    context-aware advisory output without granting execution capability.
    """
    intent_id: str
    description: str
    advisory_profile: AdvisoryProfile
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize intent to dictionary."""
        return {
            "intent_id": self.intent_id,
            "description": self.description,
            "advisory_profile": self.advisory_profile.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserIntent":
        """Deserialize intent from dictionary."""
        return cls(
            intent_id=data["intent_id"],
            description=data["description"],
            advisory_profile=AdvisoryProfile.from_string(data["advisory_profile"]),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )
    
    def get_framing(self) -> dict[str, Any]:
        """Get framing guidance based on profile."""
        return self.advisory_profile.get_framing_guidance()


def get_intent_path() -> Path:
    """Get path to intent storage file."""
    config = get_config()
    return config.data_dir / "intent.json"


def load_current_intent() -> Optional[UserIntent]:
    """Load current user intent from storage."""
    path = get_intent_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return UserIntent.from_dict(data)
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def save_intent(intent: UserIntent, log_event: bool = True) -> None:
    """
    Save user intent to storage.
    
    INVARIANT: Logs INTENT_SET event to evidence.
    """
    path = get_intent_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(intent.to_dict(), f, indent=2)
    
    if log_event:
        event = create_event(
            event_type="INTENT_SET",
            node_role=COMPONENT_ROLE,
            summary=f"User intent set: {intent.advisory_profile.value} - {intent.description[:50]}",
            payload={
                "intent": intent.to_dict(),
                "profile_framing": intent.get_framing(),
            },
            tags=["intent", "configuration", intent.advisory_profile.value],
            session_id=intent.intent_id,
        )
        append_event(event)


def create_intent(
    description: str,
    profile: AdvisoryProfile,
    intent_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> UserIntent:
    """Create a new user intent."""
    from .evidence import generate_session_id
    
    return UserIntent(
        intent_id=intent_id or generate_session_id(),
        description=description,
        advisory_profile=profile,
        metadata=metadata or {},
    )


def get_or_create_default_intent() -> UserIntent:
    """Get current intent or create a default one."""
    intent = load_current_intent()
    if intent is None:
        intent = create_intent(
            description="Default intent: General system monitoring",
            profile=AdvisoryProfile.STABILITY_FIRST,
        )
        save_intent(intent, log_event=False)
    return intent


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print("\nAvailable Advisory Profiles:")
    for profile in AdvisoryProfile:
        framing = profile.get_framing_guidance()
        print(f"  - {profile.name}: {framing.get('priority', 'N/A')}")
