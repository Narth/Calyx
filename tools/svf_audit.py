#!/usr/bin/env python3
"""
SVF Communication Audit Trail
Part of SVF v2.0 Phase 3 (implemented 2025-10-26)
Tracks all SVF communication for analysis and debugging
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SVF_AUDIT_DIR = ROOT / "logs" / "svf_audit"
AUDIT_FILE = SVF_AUDIT_DIR / "svf_audit.jsonl"


def _write_audit_entry(entry: Dict[str, Any]) -> None:
    """Write audit entry to log"""
    try:
        SVF_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        audit_file = SVF_AUDIT_DIR / f"svf_audit_{timestamp_str}.jsonl"
        
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Error writing audit entry: {e}")


def log_communication(agent: str, action: str, target: Optional[str] = None,
                     message_preview: str = "", outcome: str = "success",
                     metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a communication event
    
    Args:
        agent: Agent name
        action: Action type (query, respond, message, handshake, intent, etc.)
        target: Target agent or channel
        message_preview: Preview of message content
        outcome: Outcome (success, failed, timeout, etc.)
        metadata: Additional metadata
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "target": target,
        "message_preview": message_preview[:100],
        "outcome": outcome,
        "metadata": metadata or {}
    }
    
    _write_audit_entry(entry)


def log_intent_activity(intent_id: str, agent: str, activity: str,
                       details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log intent-related activity
    
    Args:
        intent_id: Intent ID
        agent: Agent performing the activity
        activity: Activity type (created, reviewed, approved, etc.)
        details: Additional details
    """
    metadata = {"intent_id": intent_id, "activity": activity}
    if details:
        metadata.update(details)
    
    log_communication(
        agent=agent,
        action="intent",
        target=intent_id,
        message_preview=activity,
        outcome="success",
        metadata=metadata
    )


def log_deployment_event(event_type: str, lease_id: str, intent_id: str,
                        agent: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Log Phase 3 deployment events
    
    Args:
        event_type: Event type (COSIGNED, VERIFIED_2KEY, STARTED, etc.)
        lease_id: Lease ID
        intent_id: Intent ID
        agent: Agent generating the event
        metadata: Additional metadata
    """
    event_metadata = {
        "lease_id": lease_id,
        "intent_id": intent_id,
        "event_type": event_type
    }
    if metadata:
        event_metadata.update(metadata)
    
    log_communication(
        agent=agent,
        action="deployment",
        target=lease_id,
        message_preview=f"{event_type}",
        outcome="success",
        metadata=event_metadata
    )


def get_audit_trail(agent: Optional[str] = None, action: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get audit trail entries
    
    Args:
        agent: Filter by agent
        action: Filter by action
        limit: Maximum entries to return
        
    Returns:
        List of audit entries
    """
    entries = []
    
    if not SVF_AUDIT_DIR.exists():
        return entries
    
    # Get today's audit file
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    audit_file = SVF_AUDIT_DIR / f"svf_audit_{timestamp_str}.jsonl"
    
    if not audit_file.exists():
        return entries
    
    with audit_file.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Apply filters
                if agent and entry.get("agent") != agent:
                    continue
                if action and entry.get("action") != action:
                    continue
                
                entries.append(entry)
            except Exception:
                continue
    
    # Return most recent entries
    return entries[-limit:]


def analyze_communication_patterns(days: int = 1) -> Dict[str, Any]:
    """
    Analyze communication patterns
    
    Args:
        days: Number of days to analyze
        
    Returns:
        Analysis results
    """
    from collections import defaultdict
    
    action_counts = defaultdict(int)
    agent_counts = defaultdict(int)
    outcome_counts = defaultdict(int)
    
    timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    audit_file = SVF_AUDIT_DIR / f"svf_audit_{timestamp_str}.jsonl"
    
    if audit_file.exists():
        with audit_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    action_counts[entry.get("action", "unknown")] += 1
                    agent_counts[entry.get("agent", "unknown")] += 1
                    outcome_counts[entry.get("outcome", "unknown")] += 1
                except Exception:
                    continue
    
    return {
        "actions": dict(action_counts),
        "agents": dict(agent_counts),
        "outcomes": dict(outcome_counts),
        "total_communications": sum(action_counts.values())
    }


def main():
    parser = argparse.ArgumentParser(description="SVF Communication Audit Trail")
    parser.add_argument("--log", action="store_true", help="Log communication event")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--action", help="Action type")
    parser.add_argument("--target", help="Target agent/channel")
    parser.add_argument("--message", help="Message preview")
    parser.add_argument("--outcome", default="success", help="Outcome")
    
    parser.add_argument("--get", action="store_true", help="Get audit trail")
    parser.add_argument("--filter-agent", help="Filter by agent")
    parser.add_argument("--filter-action", help="Filter by action")
    parser.add_argument("--limit", type=int, default=100, help="Limit results")
    
    parser.add_argument("--analyze", action="store_true", help="Analyze patterns")
    parser.add_argument("--days", type=int, default=1, help="Days to analyze")
    
    args = parser.parse_args()
    
    if args.log:
        if not args.agent or not args.action:
            parser.error("--agent and --action required for --log")
        
        log_communication(
            agent=args.agent,
            action=args.action,
            target=args.target,
            message_preview=args.message or "",
            outcome=args.outcome
        )
        print("Audit entry logged")
    
    elif args.get:
        entries = get_audit_trail(
            agent=args.filter_agent,
            action=args.filter_action,
            limit=args.limit
        )
        print(f"Found {len(entries)} audit entries")
        for entry in entries[-10:]:  # Show last 10
            print(f"\n[{entry['timestamp']}] {entry['agent']} → {entry['action']}: {entry.get('outcome', 'unknown')}")
    
    elif args.analyze:
        analysis = analyze_communication_patterns(args.days)
        print("Communication Analysis:")
        print(json.dumps(analysis, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

