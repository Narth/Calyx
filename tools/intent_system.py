#!/usr/bin/env python3
"""
Intent Ticketing System
Part of Capability Evolution Phase 0 (implemented 2025-10-26)
Tracks all proposed changes with comprehensive metadata
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
INTENTS_DIR = ROOT / "outgoing" / "intents"
INTENTS_FILE = INTENTS_DIR / "intents.jsonl"

# SVF v2.0 imports for broadcasts
try:
    from tools.svf_audit import log_intent_activity
    from tools.svf_channels import send_message
    SVF_AVAILABLE = True
except ImportError:
    SVF_AVAILABLE = False
    def log_intent_activity(*args, **kwargs):
        pass
    def send_message(*args, **kwargs):
        pass


class IntentStatus(Enum):
    """Intent lifecycle status"""
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"
    STALE = "stale"


class IntentType(Enum):
    """Types of intents"""
    CODE_CHANGE = "code_change"
    CONFIG_CHANGE = "config_change"
    DEPLOYMENT = "deployment"
    TEST_RUN = "test_run"
    CLEANUP = "cleanup"


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _write_intent(intent: Dict[str, Any]) -> None:
    """Write intent to log"""
    try:
        INTENTS_DIR.mkdir(parents=True, exist_ok=True)
        with INTENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(intent) + "\n")
    except Exception as e:
        print(f"Error writing intent: {e}")


def create_intent(
    proposed_by: str,
    intent_type: str,
    goal: str,
    change_set: List[str],
    risk_level: str = "medium",
    rollback_plan: str = "",
    reviewers: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new intent
    
    Args:
        proposed_by: Agent or user proposing the change
        intent_type: Type of intent (code_change, config_change, etc.)
        goal: Description of what this intent aims to achieve
        change_set: List of files or components affected
        risk_level: Low, medium, high, or critical
        rollback_plan: How to rollback if needed
        reviewers: List of agents that should review this
        metadata: Additional metadata
        
    Returns:
        Intent ID
    """
    intent_id = str(uuid.uuid4())
    
    now = datetime.now(timezone.utc)
    meta = metadata or {}
    chain_id = meta.get("chain_of_custody") or str(uuid.uuid4())
    # Default stale cutoff: 24h after creation unless caller sets stale_after_hours
    stale_after_hours = float(meta.get("stale_after_hours", 24))
    expires_at = now.timestamp() + (stale_after_hours * 3600.0)

    intent = {
        "intent_id": intent_id,
        "proposed_by": proposed_by,
        "intent_type": intent_type,
        "status": IntentStatus.DRAFT.value,
        "goal": goal,
        "change_set": change_set,
        "risk_level": risk_level,
        "rollback_plan": rollback_plan,
        "reviewers": reviewers or [],
        "reviews": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "metadata": {
            **meta,
            "chain_of_custody": chain_id,
            "stale_after_hours": stale_after_hours,
            "expires_at_ts": expires_at,
        }
    }
    
    _write_intent(intent)
    
    # Broadcast to CP17 and CP16 per CGPT recommendation
    if SVF_AVAILABLE:
        log_intent_activity(intent_id, proposed_by, "created", {"goal": goal})
        
        # Notify CP17 (documenter) and CP16 (arbitrator)
        send_message("cbo", "cp17", f"Intent created: {goal[:50]}", "standard", "low", {"intent_id": intent_id})
        send_message("cbo", "cp16", f"Intent created: {goal[:50]}", "standard", "low", {"intent_id": intent_id})
    
    return intent_id


def get_intent(intent_id: str) -> Optional[Dict[str, Any]]:
    """Get intent by ID"""
    if not INTENTS_FILE.exists():
        return None
    
    with INTENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                intent = json.loads(line.strip())
                if intent.get("intent_id") == intent_id:
                    return intent
            except Exception:
                continue
    
    return None


def update_intent_status(intent_id: str, status: str, updated_by: str = "system") -> bool:
    """Update intent status"""
    intent = get_intent(intent_id)
    if not intent:
        return False
    
    intent["status"] = status
    intent["updated_at"] = datetime.now(timezone.utc).isoformat()
    intent["updated_by"] = updated_by
    
    _write_intent(intent)
    return True


def flag_stale_intents(max_age_hours: float = 24.0) -> int:
    """
    Mark intents older than their expiration as STALE.
    Returns count of intents flagged.
    """
    if not INTENTS_FILE.exists():
        return 0
    flagged = 0
    cutoff_sec = float(max_age_hours) * 3600.0
    now_ts = datetime.now(timezone.utc).timestamp()

    with INTENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                intent = json.loads(line.strip())
            except Exception:
                continue
            status = intent.get("status", "")
            if status in (
                IntentStatus.REJECTED.value,
                IntentStatus.IMPLEMENTED.value,
                IntentStatus.ROLLED_BACK.value,
                IntentStatus.STALE.value,
            ):
                continue

            meta = intent.get("metadata", {}) or {}
            expires = meta.get("expires_at_ts")
            if expires is None:
                created = intent.get("created_at")
                try:
                    created_ts = datetime.fromisoformat(created).timestamp() if created else 0
                except Exception:
                    created_ts = 0
                expires = created_ts + cutoff_sec

            try:
                if now_ts >= float(expires):
                    intent["status"] = IntentStatus.STALE.value
                    intent["updated_at"] = datetime.now(timezone.utc).isoformat()
                    intent["updated_by"] = "stale_guard"
                    _write_intent(intent)
                    flagged += 1
            except Exception:
                continue

    return flagged


def add_review(intent_id: str, reviewer: str, approval: bool, 
               comments: str = "", findings: Optional[Dict[str, Any]] = None) -> bool:
    """Add a review to an intent"""
    intent = get_intent(intent_id)
    if not intent:
        return False
    
    if "reviews" not in intent:
        intent["reviews"] = {}
    
    intent["reviews"][reviewer] = {
        "approval": approval,
        "comments": comments,
        "findings": findings or {},
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }
    
    intent["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    _write_intent(intent)
    
    # Log review activity
    if SVF_AVAILABLE:
        log_intent_activity(intent_id, reviewer, "review_added", {"approval": approval, "comments": comments[:50]})
    
    return True


def get_pending_intents(proposed_by: Optional[str] = None, 
                       status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get pending intents"""
    intents = []
    
    if not INTENTS_FILE.exists():
        return intents
    
    with INTENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                intent = json.loads(line.strip())
                
                # Apply filters
                if proposed_by and intent.get("proposed_by") != proposed_by:
                    continue
                if status and intent.get("status") != status:
                    continue
                
                intents.append(intent)
            except Exception:
                continue
    
    return intents


def main():
    parser = argparse.ArgumentParser(description="Intent Ticketing System")
    parser.add_argument("--create", action="store_true", help="Create new intent")
    parser.add_argument("--proposed-by", help="Agent proposing the change")
    parser.add_argument("--type", help="Intent type")
    parser.add_argument("--goal", help="Goal description")
    parser.add_argument("--changes", nargs="+", help="Change set")
    parser.add_argument("--risk", help="Risk level")
    parser.add_argument("--rollback", help="Rollback plan")
    parser.add_argument("--reviewers", nargs="+", help="Reviewers")
    
    parser.add_argument("--get", help="Get intent by ID")
    parser.add_argument("--status", help="Get intents by status")
    parser.add_argument("--list", action="store_true", help="List all intents")
    parser.add_argument("--flag-stale", action="store_true", help="Flag stale intents older than cutoff")
    parser.add_argument("--stale-max-hours", type=float, default=24.0, help="Cutoff hours for staleness (default 24)")
    
    parser.add_argument("--update-status", help="Update intent status")
    parser.add_argument("--intent-id", help="Intent ID")
    parser.add_argument("--new-status", help="New status")
    parser.add_argument("--updated-by", help="Updated by")
    
    parser.add_argument("--add-review", action="store_true", help="Add review")
    parser.add_argument("--reviewer", help="Reviewer name")
    parser.add_argument("--approval", type=bool, help="Approval (true/false)")
    parser.add_argument("--comments", help="Review comments")
    
    args = parser.parse_args()
    
    if args.create:
        if not all([args.proposed_by, args.type, args.goal, args.changes]):
            parser.error("--create requires --proposed-by, --type, --goal, and --changes")
        
        intent_id = create_intent(
            proposed_by=args.proposed_by,
            intent_type=args.type,
            goal=args.goal,
            change_set=args.changes,
            risk_level=args.risk or "medium",
            rollback_plan=args.rollback or "",
            reviewers=args.reviewers
        )
        print(f"Intent created: {intent_id}")
        return
    
    if args.get:
        intent = get_intent(args.get)
        if intent:
            print(json.dumps(intent, indent=2))
        else:
            print(f"Intent not found: {args.get}")
        return
    
    if args.list or args.status:
        intents = get_pending_intents(status=args.status)
        print(f"Found {len(intents)} intents")
        for intent in intents:
            print(f"\n{intent['intent_id']}: {intent['goal']} ({intent['status']})")
        return
    
    if args.update_status:
        if not all([args.intent_id, args.new_status]):
            parser.error("--update-status requires --intent-id and --new-status")
        
        success = update_intent_status(
            args.intent_id,
            args.new_status,
            args.updated_by or "system"
        )
        if success:
            print(f"Intent {args.intent_id} status updated to {args.new_status}")
        else:
            print(f"Failed to update intent {args.intent_id}")
        return
    
    if args.add_review:
        if not all([args.intent_id, args.reviewer, args.approval is not None]):
            parser.error("--add-review requires --intent-id, --reviewer, and --approval")
        
        success = add_review(
            args.intent_id,
            args.reviewer,
            args.approval,
            args.comments or ""
        )
        if success:
            print(f"Review added for intent {args.intent_id}")
        else:
            print(f"Failed to add review for intent {args.intent_id}")
        return

    if args.flag_stale:
        flagged = flag_stale_intents(args.stale_max_hours)
        print(f"Flagged {flagged} stale intent(s)")
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()

