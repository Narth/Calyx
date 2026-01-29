#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Station Calyx - Clawdbot Integration Bridge
============================================

This script provides the integration layer between Clawdbot and Station Calyx
governance infrastructure.

RESPONSIBILITIES:
- Intercept Clawdbot action proposals
- Route through CBO oversight queue
- Enforce sandbox constraints
- Log all actions to evidence store
- Trigger kill switch on violations

USAGE:
    python -m station_calyx.clawdbot.bridge --watch
    python -m station_calyx.clawdbot.bridge --process-pending

INTEGRATION:
    Clawdbot skills can call this bridge via:
    - HTTP API (when gateway is running)
    - Direct Python import
    - CLI invocation
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from station_calyx.clawdbot.sandbox import (
    ActionCategory,
    get_sandbox,
    is_path_allowed,
    is_action_allowed,
)
from station_calyx.clawdbot.oversight import (
    submit_action_proposal,
    get_pending_proposals,
    approve_action,
    deny_action,
)
from station_calyx.clawdbot.action_log import (
    log_action,
    log_action_outcome,
    ActionOutcome,
)
from station_calyx.clawdbot.kill_switch import (
    is_clawdbot_enabled,
    get_clawdbot_status,
    emergency_halt,
)
from station_calyx.clawdbot.compliance import (
    validate_action_proposal,
    get_compliance_report,
)


def propose_action(
    category: str,
    description: str,
    parameters: dict[str, Any],
    reasoning: str,
    user_intent: Optional[str] = None,
) -> dict[str, Any]:
    """
    Propose a Clawdbot action for CBO oversight.
    
    This is the main entry point for Clawdbot integration.
    
    Args:
        category: Action category (file_read, shell_command, etc.)
        description: Human-readable description of the action
        parameters: Action-specific parameters
        reasoning: Clawdbot's reasoning for why this action is appropriate
        user_intent: Reference to user request that prompted this action
        
    Returns:
        Dict with proposal_id, status, and any immediate denial reason
    """
    # Check if Clawdbot is enabled
    if not is_clawdbot_enabled():
        return {
            "status": "denied",
            "reason": "Clawdbot is not enabled",
            "proposal_id": None,
        }
    
    # Parse category
    try:
        action_category = ActionCategory(category)
    except ValueError:
        return {
            "status": "denied", 
            "reason": f"Unknown action category: {category}",
            "proposal_id": None,
        }
    
    # Submit to oversight queue
    proposal_id, denial_reason = submit_action_proposal(
        action_category=action_category,
        action_description=description,
        action_parameters=parameters,
        clawdbot_reasoning=reasoning,
        user_intent_reference=user_intent,
    )
    
    if denial_reason:
        return {
            "status": "denied",
            "reason": denial_reason,
            "proposal_id": proposal_id,
        }
    
    return {
        "status": "pending",
        "reason": "Awaiting CBO approval",
        "proposal_id": proposal_id,
    }


def check_proposal_status(proposal_id: str) -> dict[str, Any]:
    """Check the status of a pending proposal."""
    from station_calyx.clawdbot.oversight import get_oversight_queue
    
    queue = get_oversight_queue()
    proposal = queue.get_proposal(proposal_id)
    
    if proposal is None:
        return {
            "status": "not_found",
            "proposal_id": proposal_id,
        }
    
    return {
        "status": proposal.status,
        "proposal_id": proposal_id,
        "decision_by": proposal.decision_by,
        "decision_reason": proposal.decision_reason,
    }


def report_outcome(
    proposal_id: str,
    success: bool,
    output: Optional[str] = None,
    error: Optional[str] = None,
    unintended: bool = False,
) -> dict[str, Any]:
    """
    Report the outcome of an executed action.
    
    Args:
        proposal_id: The proposal ID that was executed
        success: Whether execution succeeded
        output: Output from the action (if any)
        error: Error message (if failed)
        unintended: Whether unintended behavior was observed
        
    Returns:
        Dict with logged status
    """
    if unintended:
        outcome = ActionOutcome.UNINTENDED
    elif success:
        outcome = ActionOutcome.SUCCESS
    else:
        outcome = ActionOutcome.FAILURE
    
    import uuid
    record_id = str(uuid.uuid4())[:12]
    
    log_action_outcome(
        record_id=record_id,
        proposal_id=proposal_id,
        outcome=outcome,
        output=output,
        error=error,
        unintended_behavior=unintended,
    )
    
    return {
        "logged": True,
        "record_id": record_id,
        "outcome": outcome.value,
        "halt_triggered": unintended,
    }


def auto_approve_low_risk() -> int:
    """
    Auto-approve low-risk pending proposals.
    
    In trial mode, this is disabled - all actions require explicit approval.
    
    Returns:
        Number of proposals approved
    """
    sandbox = get_sandbox()
    
    if sandbox.config.require_cbo_approval_all:
        print("[Bridge] Trial mode active - auto-approval disabled")
        return 0
    
    pending = get_pending_proposals()
    approved = 0
    
    for proposal in pending:
        # Only auto-approve LOW risk, reversible actions
        if proposal.risk_level == "low" and proposal.reversible:
            approve_action(
                proposal.proposal_id,
                approved_by="auto",
                reason="Auto-approved: low risk, reversible",
            )
            approved += 1
    
    return approved


def watch_mode(interval: int = 5) -> None:
    """
    Watch mode - continuously monitor pending proposals.
    
    Args:
        interval: Check interval in seconds
    """
    print("[Bridge] Entering watch mode...")
    print("[Bridge] Press Ctrl+C to exit")
    print()
    
    try:
        while True:
            status = get_clawdbot_status()
            
            if status["halted"]:
                print(f"[Bridge] HALTED: {status['halt_reason']}")
                time.sleep(interval)
                continue
            
            if not status["enabled"]:
                print("[Bridge] Clawdbot disabled - waiting...")
                time.sleep(interval)
                continue
            
            pending = get_pending_proposals()
            
            if pending:
                print(f"[Bridge] {len(pending)} pending proposals:")
                for p in pending[:5]:
                    print(f"  - {p.proposal_id}: {p.action_category} ({p.risk_level})")
            else:
                print("[Bridge] No pending proposals")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n[Bridge] Watch mode exited")


def main() -> int:
    """Main entry point for the bridge."""
    parser = argparse.ArgumentParser(
        description="Station Calyx - Clawdbot Integration Bridge"
    )
    
    subparsers = parser.add_subparsers(dest="command")
    
    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch pending proposals")
    watch_parser.add_argument("--interval", type=int, default=5, help="Check interval")
    
    # propose
    propose_parser = subparsers.add_parser("propose", help="Propose an action")
    propose_parser.add_argument("--category", required=True, help="Action category")
    propose_parser.add_argument("--description", required=True, help="Action description")
    propose_parser.add_argument("--reasoning", required=True, help="Reasoning")
    propose_parser.add_argument("--params", type=str, default="{}", help="JSON parameters")
    
    # status
    status_parser = subparsers.add_parser("status", help="Check bridge status")
    
    args = parser.parse_args()
    
    if args.command == "watch":
        watch_mode(args.interval)
        return 0
    
    elif args.command == "propose":
        params = json.loads(args.params)
        result = propose_action(
            category=args.category,
            description=args.description,
            parameters=params,
            reasoning=args.reasoning,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] != "denied" else 1
    
    elif args.command == "status":
        status = get_clawdbot_status()
        pending = get_pending_proposals()
        
        print("# Clawdbot Bridge Status")
        print()
        print(f"Enabled: {status['enabled']}")
        print(f"Halted: {status['halted']}")
        print(f"Pending proposals: {len(pending)}")
        return 0
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
