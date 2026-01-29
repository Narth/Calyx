# -*- coding: utf-8 -*-
"""
CBO Oversight for Clawdbot Actions
==================================

Provides the oversight queue and approval mechanism for Clawdbot actions.

OVERSIGHT FLOW:
1. Clawdbot proposes an action via submit_action_proposal()
2. Proposal is validated against sandbox and HVD-1
3. If validation passes, proposal enters oversight queue
4. CBO reviews and approves/denies
5. For CRITICAL actions, human approval also required
6. Decision is logged to evidence store
7. Clawdbot receives decision and may execute if approved

DECISION CRITERIA:
- Does the action align with current user intent?
- Does the action have irreversible consequences?
- Is there evidence supporting this action?
- Does the action violate HVD-1 boundaries?
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum

from .sandbox import ActionCategory, ActionRiskLevel, get_sandbox


class ProposalStatus(Enum):
    """Status of an action proposal."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    EXECUTED = "executed"
    FAILED = "failed"


class DenialReason(Enum):
    """Reasons for denying an action proposal."""
    SANDBOX_VIOLATION = "sandbox_violation"
    HVD1_VIOLATION = "hvd1_violation"
    GOVERNANCE_PROTECTION = "governance_protection"
    RATE_LIMIT = "rate_limit"
    BLOCKED_ACTION = "blocked_action"
    CBO_DENIED = "cbo_denied"
    HUMAN_DENIED = "human_denied"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    UNINTENDED_EXECUTION = "unintended_execution"


@dataclass
class ActionProposal:
    """A proposed action from Clawdbot awaiting oversight decision."""
    
    proposal_id: str
    timestamp: str
    
    # Action details
    action_category: str  # ActionCategory value
    action_description: str
    action_parameters: dict[str, Any]
    
    # Context
    clawdbot_reasoning: str  # Why Clawdbot thinks this action is appropriate
    user_intent_reference: Optional[str] = None  # Reference to user request
    evidence_references: list[str] = field(default_factory=list)
    
    # Risk assessment
    risk_level: str = "unknown"  # ActionRiskLevel value
    reversible: bool = True
    external_effects: bool = False
    
    # Status
    status: str = "pending"  # ProposalStatus value
    
    # Decision (filled after review)
    decision_timestamp: Optional[str] = None
    decision_by: Optional[str] = None  # "cbo", "human", "auto"
    decision_reason: Optional[str] = None
    denial_reason: Optional[str] = None  # DenialReason value if denied
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionProposal":
        return cls(**data)


@dataclass
class OversightDecision:
    """A decision on an action proposal."""
    
    proposal_id: str
    decision: str  # "approved" or "denied"
    decision_by: str  # "cbo", "human", "auto"
    decision_timestamp: str
    reason: str
    denial_reason: Optional[str] = None
    conditions: list[str] = field(default_factory=list)  # Conditions for approval
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OversightQueue:
    """Queue for action proposals awaiting oversight."""
    
    def __init__(self, queue_dir: Optional[Path] = None):
        if queue_dir is None:
            from ..core.config import get_config
            config = get_config()
            queue_dir = config.data_dir / "clawdbot" / "oversight_queue"
        
        self.queue_dir = queue_dir
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.pending_dir = self.queue_dir / "pending"
        self.decided_dir = self.queue_dir / "decided"
        self.pending_dir.mkdir(exist_ok=True)
        self.decided_dir.mkdir(exist_ok=True)
    
    def submit(self, proposal: ActionProposal) -> str:
        """Submit a proposal to the queue."""
        path = self.pending_dir / f"{proposal.proposal_id}.json"
        path.write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")
        return proposal.proposal_id
    
    def get_pending(self) -> list[ActionProposal]:
        """Get all pending proposals."""
        proposals = []
        for path in self.pending_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                proposals.append(ActionProposal.from_dict(data))
            except (json.JSONDecodeError, IOError):
                continue
        
        # Sort by timestamp
        proposals.sort(key=lambda p: p.timestamp)
        return proposals
    
    def get_proposal(self, proposal_id: str) -> Optional[ActionProposal]:
        """Get a specific proposal."""
        # Check pending
        path = self.pending_dir / f"{proposal_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return ActionProposal.from_dict(data)
        
        # Check decided
        path = self.decided_dir / f"{proposal_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return ActionProposal.from_dict(data)
        
        return None
    
    def decide(self, proposal_id: str, decision: OversightDecision) -> bool:
        """Record a decision on a proposal."""
        path = self.pending_dir / f"{proposal_id}.json"
        if not path.exists():
            return False
        
        proposal = ActionProposal.from_dict(json.loads(path.read_text(encoding="utf-8")))
        
        # Update proposal with decision
        proposal.status = decision.decision
        proposal.decision_timestamp = decision.decision_timestamp
        proposal.decision_by = decision.decision_by
        proposal.decision_reason = decision.reason
        proposal.denial_reason = decision.denial_reason
        
        # Move to decided
        decided_path = self.decided_dir / f"{proposal_id}.json"
        decided_path.write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")
        path.unlink()
        
        # Log to evidence
        _log_oversight_decision(proposal, decision)
        
        return True


# Global queue instance
_queue: Optional[OversightQueue] = None


def get_oversight_queue() -> OversightQueue:
    """Get the oversight queue instance."""
    global _queue
    if _queue is None:
        _queue = OversightQueue()
    return _queue


def submit_action_proposal(
    action_category: ActionCategory,
    action_description: str,
    action_parameters: dict[str, Any],
    clawdbot_reasoning: str,
    user_intent_reference: Optional[str] = None,
    evidence_references: Optional[list[str]] = None,
) -> tuple[str, Optional[str]]:
    """
    Submit an action proposal for oversight.
    
    Returns:
        Tuple of (proposal_id, immediate_denial_reason or None)
    """
    from .compliance import validate_action_proposal
    
    sandbox = get_sandbox()
    
    # Generate proposal ID
    proposal_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Assess risk
    risk_level = sandbox.get_risk_level(action_category)
    
    # Determine reversibility and external effects
    reversible = action_category not in (
        ActionCategory.EMAIL_SEND,
        ActionCategory.FILE_DELETE,
        ActionCategory.SYSTEM_MODIFY,
    )
    external_effects = action_category in (
        ActionCategory.EMAIL_SEND,
        ActionCategory.NETWORK_REQUEST,
        ActionCategory.API_CALL,
        ActionCategory.BROWSER_ACTION,
    )
    
    # Create proposal
    proposal = ActionProposal(
        proposal_id=proposal_id,
        timestamp=timestamp,
        action_category=action_category.value,
        action_description=action_description,
        action_parameters=action_parameters,
        clawdbot_reasoning=clawdbot_reasoning,
        user_intent_reference=user_intent_reference,
        evidence_references=evidence_references or [],
        risk_level=risk_level.value,
        reversible=reversible,
        external_effects=external_effects,
    )
    
    # Validate against sandbox and HVD-1
    valid, denial_reason = validate_action_proposal(proposal)
    
    if not valid:
        proposal.status = ProposalStatus.DENIED.value
        proposal.decision_timestamp = timestamp
        proposal.decision_by = "auto"
        proposal.decision_reason = f"Automatic denial: {denial_reason}"
        proposal.denial_reason = denial_reason
        
        # Log the denial
        _log_oversight_decision(proposal, OversightDecision(
            proposal_id=proposal_id,
            decision="denied",
            decision_by="auto",
            decision_timestamp=timestamp,
            reason=f"Automatic denial: {denial_reason}",
            denial_reason=denial_reason,
        ))
        
        return proposal_id, denial_reason
    
    # Submit to queue for CBO review
    get_oversight_queue().submit(proposal)
    
    return proposal_id, None


def get_pending_proposals() -> list[ActionProposal]:
    """Get all pending proposals awaiting decision."""
    return get_oversight_queue().get_pending()


def approve_action(
    proposal_id: str,
    approved_by: str = "cbo",
    reason: str = "Action approved after oversight review",
    conditions: Optional[list[str]] = None,
) -> bool:
    """Approve an action proposal."""
    decision = OversightDecision(
        proposal_id=proposal_id,
        decision="approved",
        decision_by=approved_by,
        decision_timestamp=datetime.now(timezone.utc).isoformat(),
        reason=reason,
        conditions=conditions or [],
    )
    
    return get_oversight_queue().decide(proposal_id, decision)


def deny_action(
    proposal_id: str,
    denied_by: str = "cbo",
    reason: str = "Action denied after oversight review",
    denial_reason: DenialReason = DenialReason.CBO_DENIED,
) -> bool:
    """Deny an action proposal."""
    decision = OversightDecision(
        proposal_id=proposal_id,
        decision="denied",
        decision_by=denied_by,
        decision_timestamp=datetime.now(timezone.utc).isoformat(),
        reason=reason,
        denial_reason=denial_reason.value,
    )
    
    return get_oversight_queue().decide(proposal_id, decision)


def _log_oversight_decision(proposal: ActionProposal, decision: OversightDecision) -> None:
    """Log oversight decision to evidence store."""
    try:
        from ..core.evidence import add_event
        
        add_event(
            event_type="CLAWDBOT_OVERSIGHT_DECISION",
            component="clawdbot_oversight",
            summary=f"Action {decision.decision}: {proposal.action_description[:50]}",
            data={
                "proposal_id": proposal.proposal_id,
                "action_category": proposal.action_category,
                "action_description": proposal.action_description,
                "risk_level": proposal.risk_level,
                "decision": decision.decision,
                "decision_by": decision.decision_by,
                "reason": decision.reason,
                "denial_reason": decision.denial_reason,
            },
        )
    except Exception:
        pass  # Don't fail oversight on logging failure
