# -*- coding: utf-8 -*-
"""
Clawdbot Kill Switch
====================

Provides emergency halt and enable/disable controls for Clawdbot.

KILL SWITCH TRIGGERS:
- Manual disable by human or CBO
- Unintended execution detected
- HVD-1 violation detected
- Governance artifact modification attempt
- Rate limit exceeded with suspicious pattern

HALT EFFECTS:
- All pending proposals cancelled
- No new proposals accepted
- Clawdbot processes terminated (if running locally)
- Evidence preserved
- Human notification triggered
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Gate file location
CLAWDBOT_GATE_FILE = "outgoing/gates/clawdbot.ok"
CLAWDBOT_HALT_FILE = "outgoing/gates/clawdbot.halt"


def get_gates_dir() -> Path:
    """Get the gates directory."""
    gates_dir = Path("outgoing/gates")
    gates_dir.mkdir(parents=True, exist_ok=True)
    return gates_dir


def is_clawdbot_enabled() -> bool:
    """Check if Clawdbot is enabled."""
    gate_path = get_gates_dir() / "clawdbot.ok"
    halt_path = get_gates_dir() / "clawdbot.halt"
    
    # Halt takes precedence
    if halt_path.exists():
        return False
    
    return gate_path.exists()


def get_clawdbot_status() -> dict[str, Any]:
    """Get detailed Clawdbot status."""
    gate_path = get_gates_dir() / "clawdbot.ok"
    halt_path = get_gates_dir() / "clawdbot.halt"
    
    status = {
        "enabled": False,
        "halted": False,
        "halt_reason": None,
        "halt_timestamp": None,
        "enabled_timestamp": None,
        "enabled_by": None,
    }
    
    if halt_path.exists():
        status["halted"] = True
        try:
            halt_data = json.loads(halt_path.read_text(encoding="utf-8"))
            status["halt_reason"] = halt_data.get("reason")
            status["halt_timestamp"] = halt_data.get("timestamp")
        except (json.JSONDecodeError, IOError):
            pass
        return status
    
    if gate_path.exists():
        status["enabled"] = True
        try:
            gate_data = json.loads(gate_path.read_text(encoding="utf-8"))
            status["enabled_timestamp"] = gate_data.get("timestamp")
            status["enabled_by"] = gate_data.get("enabled_by")
        except (json.JSONDecodeError, IOError):
            pass
    
    return status


def enable_clawdbot(enabled_by: str = "human", reason: str = "Manual enable") -> bool:
    """
    Enable Clawdbot execution.
    
    Args:
        enabled_by: Who enabled ("human", "cbo")
        reason: Reason for enabling
        
    Returns:
        True if enabled successfully
    """
    gate_path = get_gates_dir() / "clawdbot.ok"
    halt_path = get_gates_dir() / "clawdbot.halt"
    
    # Remove halt file if present
    if halt_path.exists():
        halt_path.unlink()
    
    # Create enable gate
    gate_data = {
        "enabled": True,
        "enabled_by": enabled_by,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    gate_path.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")
    
    # Log to evidence
    _log_state_change("CLAWDBOT_ENABLED", enabled_by, reason)
    
    return True


def disable_clawdbot(disabled_by: str = "human", reason: str = "Manual disable") -> bool:
    """
    Disable Clawdbot execution (graceful).
    
    Args:
        disabled_by: Who disabled
        reason: Reason for disabling
        
    Returns:
        True if disabled successfully
    """
    gate_path = get_gates_dir() / "clawdbot.ok"
    
    # Remove enable gate
    if gate_path.exists():
        gate_path.unlink()
    
    # Log to evidence
    _log_state_change("CLAWDBOT_DISABLED", disabled_by, reason)
    
    return True


def emergency_halt(reason: str, halted_by: str = "auto") -> bool:
    """
    Emergency halt of Clawdbot (immediate).
    
    This is triggered automatically on:
    - Unintended execution detection
    - HVD-1 violation
    - Governance artifact modification attempt
    
    Args:
        reason: Reason for halt
        halted_by: Who/what triggered halt
        
    Returns:
        True if halt successful
    """
    gate_path = get_gates_dir() / "clawdbot.ok"
    halt_path = get_gates_dir() / "clawdbot.halt"
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Remove enable gate immediately
    if gate_path.exists():
        gate_path.unlink()
    
    # Create halt file
    halt_data = {
        "halted": True,
        "halted_by": halted_by,
        "reason": reason,
        "timestamp": timestamp,
        "requires_human_review": True,
    }
    
    halt_path.write_text(json.dumps(halt_data, indent=2), encoding="utf-8")
    
    # Cancel all pending proposals
    _cancel_pending_proposals(reason)
    
    # Log critical event
    _log_state_change("CLAWDBOT_EMERGENCY_HALT", halted_by, reason, critical=True)
    
    # TODO: Terminate Clawdbot processes if running locally
    
    return True


def clear_halt(cleared_by: str = "human", reason: str = "Halt cleared after review") -> bool:
    """
    Clear a halt state after human review.
    
    Args:
        cleared_by: Must be "human"
        reason: Reason for clearing
        
    Returns:
        True if cleared successfully
    """
    if cleared_by != "human":
        return False  # Only humans can clear halts
    
    halt_path = get_gates_dir() / "clawdbot.halt"
    
    if halt_path.exists():
        halt_path.unlink()
    
    _log_state_change("CLAWDBOT_HALT_CLEARED", cleared_by, reason)
    
    return True


def _cancel_pending_proposals(reason: str) -> None:
    """Cancel all pending proposals in the oversight queue."""
    try:
        from .oversight import get_oversight_queue, OversightDecision, DenialReason
        
        queue = get_oversight_queue()
        pending = queue.get_pending()
        
        for proposal in pending:
            decision = OversightDecision(
                proposal_id=proposal.proposal_id,
                decision="denied",
                decision_by="auto",
                decision_timestamp=datetime.now(timezone.utc).isoformat(),
                reason=f"Emergency halt: {reason}",
                denial_reason=DenialReason.UNINTENDED_EXECUTION.value,
            )
            queue.decide(proposal.proposal_id, decision)
            
    except Exception:
        pass  # Don't fail halt on queue errors


def _log_state_change(
    event_type: str,
    actor: str,
    reason: str,
    critical: bool = False,
) -> None:
    """Log Clawdbot state change to evidence."""
    try:
        from ..core.evidence import add_event
        
        add_event(
            event_type=event_type,
            component="clawdbot_kill_switch",
            summary=f"Clawdbot state change: {event_type} by {actor}",
            data={
                "actor": actor,
                "reason": reason,
                "critical": critical,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        pass
