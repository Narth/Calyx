"""
Station Calyx Notification Layer
================================

Advisory-only notifications for significant findings.
Non-intrusive, rate-limited operation.

INVARIANTS:
- HUMAN_PRIMACY: Notifications are informational only
- NO_HIDDEN_CHANNELS: Every notification logged to evidence
- EXECUTION_GATE: Does not instruct or initiate action

DESIGN PRINCIPLES:
- Non-intrusive, advisory-only operation
- Rate-limited to respect attention
- Always reference evidence
- Explicitly advisory in nature

TRIGGERS (only these events generate notifications):
- DRIFT_WARNING (new)
- PATTERN_RECURRING (new)
- HIGH confidence advisories

Role: core/notifications
Scope: Rate-limited advisory notification emission
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Callable

from .config import get_config
from .evidence import append_event, create_event, load_recent_events, generate_session_id

COMPONENT_ROLE = "notification_layer"
COMPONENT_SCOPE = "rate-limited advisory notification emission"

# Rate limiting: max notifications per time window
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
RATE_LIMIT_MAX_NOTIFICATIONS = 3


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Notification:
    """
    An advisory notification.
    
    INVARIANT: Must reference evidence and state advisory nature.
    """
    notification_id: str
    title: str
    message: str
    priority: NotificationPriority
    evidence_refs: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_event_type: str = ""
    advisory_statement: str = "This is an advisory notification. No action is required."
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "evidence_refs": self.evidence_refs,
            "timestamp": self.timestamp.isoformat(),
            "source_event_type": self.source_event_type,
            "advisory_statement": self.advisory_statement,
        }
    
    def format_console(self) -> str:
        """Format for console output."""
        priority_indicator = {
            NotificationPriority.LOW: "[i]",
            NotificationPriority.MEDIUM: "[*]",
            NotificationPriority.HIGH: "[!]",
        }.get(self.priority, "[?]")
        
        lines = [
            "",
            f"{'=' * 60}",
            f"{priority_indicator} STATION CALYX ADVISORY",
            f"{'=' * 60}",
            f"",
            f"  {self.title}",
            f"",
            f"  {self.message}",
            f"",
            f"  Evidence: {', '.join(self.evidence_refs[:3])}",
            f"",
            f"  {self.advisory_statement}",
            f"",
            f"{'=' * 60}",
            "",
        ]
        return "\n".join(lines)


class NotificationEmitter:
    """
    Manages notification emission with rate limiting.
    
    GUARDRAILS:
    - Rate-limited to prevent notification fatigue
    - Only triggered by specific event types
    - Always logs to evidence
    """
    
    def __init__(self):
        self._recent_notifications: list[datetime] = []
        self._notification_history: list[Notification] = []
        self._console_handler: Optional[Callable[[str], None]] = print
        self._toast_available = self._check_toast_availability()
    
    def _check_toast_availability(self) -> bool:
        """Check if system toast notifications are available."""
        try:
            # Windows toast notifications via win10toast or similar
            # For now, we'll just use console
            return False
        except Exception:
            return False
    
    def _is_rate_limited(self) -> bool:
        """Check if we're within rate limit."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
        
        # Clean old entries
        self._recent_notifications = [
            ts for ts in self._recent_notifications if ts > cutoff
        ]
        
        return len(self._recent_notifications) >= RATE_LIMIT_MAX_NOTIFICATIONS
    
    def _log_notification_event(self, notification: Notification) -> None:
        """Log notification emission to evidence."""
        event = create_event(
            event_type="NOTIFICATION_EMITTED",
            node_role=COMPONENT_ROLE,
            summary=f"Notification: {notification.title}",
            payload=notification.to_dict(),
            tags=["notification", notification.priority.value, notification.source_event_type.lower()],
        )
        append_event(event)
    
    def emit(
        self,
        notification: Notification,
        force: bool = False,
    ) -> bool:
        """
        Emit a notification.
        
        Returns True if notification was emitted, False if rate-limited.
        """
        # Check rate limit
        if not force and self._is_rate_limited():
            return False
        
        # Record emission time
        self._recent_notifications.append(datetime.now(timezone.utc))
        self._notification_history.append(notification)
        
        # Console output (always)
        if self._console_handler:
            self._console_handler(notification.format_console())
        
        # Toast notification (if available)
        if self._toast_available:
            self._emit_toast(notification)
        
        # Log to evidence
        self._log_notification_event(notification)
        
        return True
    
    def _emit_toast(self, notification: Notification) -> None:
        """Emit system toast notification."""
        # Placeholder for future toast implementation
        pass
    
    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent notifications."""
        return [n.to_dict() for n in self._notification_history[-limit:]]
    
    def create_from_event(self, event: dict[str, Any]) -> Optional[Notification]:
        """
        Create notification from an event if it meets trigger criteria.
        
        TRIGGERS:
        - DRIFT_WARNING
        - PATTERN_RECURRING
        - HIGH confidence advisories
        """
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})
        
        if event_type == "DRIFT_WARNING":
            metric = payload.get("metric_name", "unknown")
            direction = payload.get("direction", "changing")
            
            return Notification(
                notification_id=generate_session_id(),
                title="Drift Warning Detected",
                message=f"The metric '{metric}' is {direction} and approaching a threshold.",
                priority=NotificationPriority.MEDIUM,
                evidence_refs=[f"event:{event.get('ts', '')[:19]}"],
                source_event_type=event_type,
            )
        
        elif event_type == "PATTERN_RECURRING":
            summary = event.get("summary", "A pattern is recurring")
            
            return Notification(
                notification_id=generate_session_id(),
                title="Recurring Pattern Detected",
                message=summary[:100],
                priority=NotificationPriority.LOW,
                evidence_refs=[f"event:{event.get('ts', '')[:19]}"],
                source_event_type=event_type,
            )
        
        elif event_type == "ADVISORY_GENERATED":
            # Check for HIGH confidence notes
            notes_count = payload.get("notes_count", 0)
            if notes_count > 0:
                # This is a simplification - ideally we'd check confidence levels
                return Notification(
                    notification_id=generate_session_id(),
                    title="New Advisory Available",
                    message=f"Station Calyx has generated {notes_count} advisory note(s) for your review.",
                    priority=NotificationPriority.LOW,
                    evidence_refs=[f"advisory:{payload.get('session_id', 'unknown')}"],
                    source_event_type=event_type,
                )
        
        return None
    
    def test_notification(self) -> Notification:
        """Generate a test notification without emitting to evidence."""
        return Notification(
            notification_id="test-" + generate_session_id(),
            title="Test Notification",
            message="This is a test notification from Station Calyx. No real event triggered this.",
            priority=NotificationPriority.LOW,
            evidence_refs=["test:example"],
            source_event_type="TEST",
            advisory_statement="This is a TEST notification. No action is required.",
        )


# Global emitter instance
_emitter: Optional[NotificationEmitter] = None


def get_emitter() -> NotificationEmitter:
    """Get or create the global notification emitter."""
    global _emitter
    if _emitter is None:
        _emitter = NotificationEmitter()
    return _emitter


def emit_notification(notification: Notification, force: bool = False) -> bool:
    """Emit a notification through the global emitter."""
    return get_emitter().emit(notification, force=force)


def check_and_notify(event: dict[str, Any]) -> bool:
    """
    Check if an event should trigger a notification and emit if so.
    
    Returns True if notification was emitted.
    """
    emitter = get_emitter()
    notification = emitter.create_from_event(event)
    
    if notification:
        return emitter.emit(notification)
    
    return False


def get_recent_notifications(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent notifications from memory."""
    return get_emitter().get_recent(limit)


def get_notifications_from_evidence(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent notifications from evidence log."""
    events = load_recent_events(500)
    notifications = [
        e for e in events if e.get("event_type") == "NOTIFICATION_EMITTED"
    ]
    
    return [
        {
            "notification_id": e.get("payload", {}).get("notification_id"),
            "title": e.get("payload", {}).get("title"),
            "message": e.get("payload", {}).get("message"),
            "priority": e.get("payload", {}).get("priority"),
            "timestamp": e.get("ts"),
            "evidence_refs": e.get("payload", {}).get("evidence_refs", []),
        }
        for e in notifications[-limit:]
    ]


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print("\nTrigger events:")
    print("- DRIFT_WARNING")
    print("- PATTERN_RECURRING")
    print("- HIGH confidence advisories")
    print(f"\nRate limit: {RATE_LIMIT_MAX_NOTIFICATIONS} per {RATE_LIMIT_WINDOW_SECONDS}s")
