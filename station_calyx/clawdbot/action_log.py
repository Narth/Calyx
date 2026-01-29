# -*- coding: utf-8 -*-
"""
Clawdbot Action Logging
=======================

Logs all Clawdbot actions to Station Calyx evidence store.

LOGGING REQUIREMENTS:
- Every action proposal is logged
- Every decision is logged
- Every execution outcome is logged
- Logs are append-only and immutable
- Logs use Evidence Envelope format for integrity
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum


class ActionOutcome(Enum):
    """Outcome of an executed action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    UNINTENDED = "unintended"  # Triggers review


@dataclass
class ActionRecord:
    """Complete record of a Clawdbot action from proposal to outcome."""
    
    # Identity (required)
    record_id: str
    proposal_id: str
    proposed_at: str
    action_category: str
    action_description: str
    
    # Optional fields with defaults
    decided_at: Optional[str] = None
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    action_parameters: dict[str, Any] = field(default_factory=dict)
    
    # Decision
    decision: Optional[str] = None  # approved, denied
    decision_by: Optional[str] = None
    decision_reason: Optional[str] = None
    
    # Execution
    executed: bool = False
    outcome: Optional[str] = None  # ActionOutcome value
    outcome_details: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    
    # Flags
    unintended_behavior: bool = False
    requires_review: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionRecord":
        return cls(**data)


def get_action_log_dir() -> Path:
    """Get the action log directory."""
    from ..core.config import get_config
    config = get_config()
    log_dir = config.data_dir / "clawdbot" / "action_log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def log_action(
    proposal_id: str,
    action_category: str,
    action_description: str,
    action_parameters: dict[str, Any],
    decision: str,
    decision_by: str,
    decision_reason: str,
) -> str:
    """
    Log an action that has been decided (approved or denied).
    
    Returns:
        Record ID
    """
    import uuid
    
    timestamp = datetime.now(timezone.utc).isoformat()
    record_id = str(uuid.uuid4())[:12]
    
    record = ActionRecord(
        record_id=record_id,
        proposal_id=proposal_id,
        proposed_at=timestamp,
        decided_at=timestamp,
        action_category=action_category,
        action_description=action_description,
        action_parameters=action_parameters,
        decision=decision,
        decision_by=decision_by,
        decision_reason=decision_reason,
    )
    
    # Save to log file
    log_dir = get_action_log_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    log_file = log_dir / f"actions_{date_str}.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict()) + "\n")
    
    # Also log to evidence store
    _log_to_evidence("ACTION_LOGGED", record)
    
    return record_id


def log_action_outcome(
    record_id: str,
    proposal_id: str,
    outcome: ActionOutcome,
    outcome_details: Optional[str] = None,
    output: Optional[str] = None,
    error: Optional[str] = None,
    unintended_behavior: bool = False,
) -> None:
    """
    Log the outcome of an executed action.
    
    If unintended_behavior is True, this triggers a review flag.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    outcome_record = {
        "record_id": record_id,
        "proposal_id": proposal_id,
        "completed_at": timestamp,
        "outcome": outcome.value,
        "outcome_details": outcome_details,
        "output": output[:1000] if output else None,  # Truncate large outputs
        "error": error,
        "unintended_behavior": unintended_behavior,
        "requires_review": unintended_behavior or outcome == ActionOutcome.UNINTENDED,
    }
    
    # Append to log
    log_dir = get_action_log_dir()
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    log_file = log_dir / f"outcomes_{date_str}.jsonl"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(outcome_record) + "\n")
    
    # Log to evidence
    event_type = "ACTION_OUTCOME"
    if unintended_behavior:
        event_type = "UNINTENDED_EXECUTION_DETECTED"
    
    _log_to_evidence(event_type, outcome_record)
    
    # If unintended behavior, trigger halt check
    if unintended_behavior:
        _handle_unintended_execution(record_id, proposal_id, outcome_details)


def get_action_history(
    limit: int = 100,
    include_outcomes: bool = True,
) -> list[dict[str, Any]]:
    """Get recent action history."""
    log_dir = get_action_log_dir()
    
    records = []
    
    # Get action files sorted by date descending
    action_files = sorted(log_dir.glob("actions_*.jsonl"), reverse=True)
    
    for action_file in action_files:
        if len(records) >= limit:
            break
        
        try:
            with open(action_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
                        if len(records) >= limit:
                            break
        except (IOError, json.JSONDecodeError):
            continue
    
    # Optionally merge outcomes
    if include_outcomes:
        outcomes = _load_recent_outcomes(limit)
        outcome_map = {o["record_id"]: o for o in outcomes}
        
        for record in records:
            if record["record_id"] in outcome_map:
                record.update(outcome_map[record["record_id"]])
    
    return records


def _load_recent_outcomes(limit: int) -> list[dict[str, Any]]:
    """Load recent action outcomes."""
    log_dir = get_action_log_dir()
    outcomes = []
    
    outcome_files = sorted(log_dir.glob("outcomes_*.jsonl"), reverse=True)
    
    for outcome_file in outcome_files:
        if len(outcomes) >= limit:
            break
        
        try:
            with open(outcome_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        outcomes.append(json.loads(line))
                        if len(outcomes) >= limit:
                            break
        except (IOError, json.JSONDecodeError):
            continue
    
    return outcomes


def _log_to_evidence(event_type: str, data: dict[str, Any]) -> None:
    """Log to Station Calyx evidence store."""
    try:
        from ..core.evidence import add_event
        
        summary = f"Clawdbot {event_type.lower().replace('_', ' ')}"
        if "action_description" in data:
            summary += f": {data['action_description'][:50]}"
        
        add_event(
            event_type=event_type,
            component="clawdbot_action_log",
            summary=summary,
            data=data,
        )
    except Exception:
        pass


def _handle_unintended_execution(
    record_id: str,
    proposal_id: str,
    details: Optional[str],
) -> None:
    """Handle detection of unintended execution."""
    from .kill_switch import emergency_halt, is_clawdbot_enabled
    
    # Log critical event
    _log_to_evidence("UNINTENDED_EXECUTION_ALERT", {
        "record_id": record_id,
        "proposal_id": proposal_id,
        "details": details,
        "action_taken": "emergency_halt_triggered",
    })
    
    # Trigger emergency halt if enabled
    if is_clawdbot_enabled():
        emergency_halt(f"Unintended execution detected: {details}")
