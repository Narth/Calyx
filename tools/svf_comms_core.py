#!/usr/bin/env python3
"""
SVF Communication Core - Message Routing & Delivery
Implements CGPT Communication Terminal Spec
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT = Path(__file__).resolve().parents[1]
COMMS_DIR = ROOT / "outgoing" / "comms"
MESSAGES_FILE = COMMS_DIR / "messages.jsonl"
RECEIPTS_FILE = COMMS_DIR / "receipts.jsonl"


def init_comms():
    """Initialize communication directories"""
    COMMS_DIR.mkdir(parents=True, exist_ok=True)
    if not MESSAGES_FILE.exists():
        MESSAGES_FILE.touch()
    if not RECEIPTS_FILE.exists():
        RECEIPTS_FILE.touch()


def parse_route(text: str) -> Dict[str, Any]:
    """
    Parse message text to determine routing
    
    Rules:
    - @Station -> broadcast
    - @<AgentId> -> direct to agent
    - #<INT|LEASE-id> -> thread-based
    - Else -> broadcast
    """
    text = text.strip()
    
    if text.startswith("@Station"):
        return {"route": "broadcast", "to": None, "thread_id": None}
    
    elif text.startswith("@"):
        # Extract agent ID
        parts = text.split(maxsplit=1)
        agent_id = parts[0][1:]  # Remove @
        return {"route": "direct", "to": agent_id, "thread_id": None}
    
    elif text.startswith("#"):
        # Extract thread ID
        parts = text.split(maxsplit=1)
        thread_id = parts[0][1:]  # Remove #
        # Validate it's INT- or LEASE-
        if thread_id.startswith(("INT-", "LEASE-")):
            return {"route": "thread", "to": None, "thread_id": thread_id}
    
    # Default to broadcast
    return {"route": "broadcast", "to": None, "thread_id": None}


def resolve_targets(route: str, to: Optional[str] = None, thread_id: Optional[str] = None) -> List[str]:
    """
    Resolve message targets based on route
    
    Returns:
        List of recipient agent IDs
    """
    targets = []
    
    if route == "broadcast":
        # All agents
        lock_dir = ROOT / "outgoing"
        for lock_file in lock_dir.glob("*.lock"):
            agent_id = lock_file.stem
            if agent_id not in ["dashboard", "svf"]:  # Exclude special
                targets.append(agent_id)
    
    elif route == "direct":
        # Single agent
        if to:
            targets.append(to)
    
    elif route == "thread":
        # Thread participants (from intent/lease)
        if thread_id:
            if thread_id.startswith("INT-"):
                # Get intent participants
                intent_file = ROOT / "outgoing" / "intents" / f"{thread_id}.json"
                if intent_file.exists():
                    try:
                        intent = json.loads(intent_file.read_text(encoding="utf-8"))
                        reviewers = intent.get("reviewers", [])
                        targets.extend(reviewers)
                        targets.append(intent.get("proposed_by", "cbo"))
                    except:
                        pass
            
            elif thread_id.startswith("LEASE-"):
                # Get lease participants
                lease_file = ROOT / "outgoing" / "leases" / f"{thread_id}.json"
                if lease_file.exists():
                    try:
                        lease = json.loads(lease_file.read_text(encoding="utf-8"))
                        cosigners = lease.get("cosigners", [])
                        for c in cosigners:
                            if c.get("role") == "agent":
                                targets.append(c.get("id"))
                        targets.append(lease.get("actor", "cbo"))
                    except:
                        pass
    
    return list(set(targets))  # Remove duplicates


def create_message(route: str, text: str, from_role: str = "human", from_id: str = "user1",
                   to: Optional[str] = None, thread_id: Optional[str] = None,
                   priority: str = "normal", reply_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new message
    
    Returns:
        Message dict with msg_id
    """
    msg_id = f"MSG-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    
    message = {
        "msg_id": msg_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": {"role": from_role, "id": from_id},
        "route": route,
        "to": to,
        "thread_id": thread_id,
        "text": text,
        "meta": {
            "priority": priority,
            "reply_to": reply_to
        }
    }
    
    return message


def persist_message(message: Dict[str, Any]) -> bool:
    """Append message to messages.jsonl"""
    try:
        init_comms()
        with open(MESSAGES_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(message) + '\n')
        return True
    except Exception as e:
        print(f"Error persisting message: {e}")
        return False


def create_receipts(msg_id: str, targets: List[str]) -> List[Dict[str, Any]]:
    """
    Create receipts for all targets
    
    Returns:
        List of receipt dicts
    """
    receipts = []
    now = datetime.now(timezone.utc).isoformat()
    
    for recipient in targets:
        receipt = {
            "msg_id": msg_id,
            "recipient": recipient,
            "delivered_ts": None,
            "read_ts": None,
            "status": "queued"
        }
        receipts.append(receipt)
    
    return receipts


def persist_receipts(receipts: List[Dict[str, Any]]) -> bool:
    """Append receipts to receipts.jsonl"""
    try:
        init_comms()
        with open(RECEIPTS_FILE, 'a', encoding='utf-8') as f:
            for receipt in receipts:
                f.write(json.dumps(receipt) + '\n')
        return True
    except Exception as e:
        print(f"Error persisting receipts: {e}")
        return False


def update_receipt(msg_id: str, recipient: str, status: str) -> bool:
    """
    Update receipt status
    
    Args:
        msg_id: Message ID
        recipient: Recipient agent ID
        status: New status (delivered, read)
    """
    try:
        # Initialize comms
        init_comms()
        
        # Read all receipts
        receipts = []
        if RECEIPTS_FILE.exists() and RECEIPTS_FILE.stat().st_size > 0:
            with open(RECEIPTS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            receipts.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip invalid lines
                            continue
        
        # Update matching receipt
        updated = False
        now = datetime.now(timezone.utc).isoformat()
        
        for receipt in receipts:
            if receipt.get("msg_id") == msg_id and receipt.get("recipient") == recipient:
                if status == "delivered" and not receipt.get("delivered_ts"):
                    receipt["delivered_ts"] = now
                if status == "read" and not receipt.get("read_ts"):
                    receipt["read_ts"] = now
                receipt["status"] = status
                updated = True
                break
        
        if updated:
            # Rewrite file
            with open(RECEIPTS_FILE, 'w', encoding='utf-8') as f:
                for receipt in receipts:
                    f.write(json.dumps(receipt) + '\n')
        
        return updated
    except Exception as e:
        print(f"Error updating receipt: {e}")
        return False


def send_message(text: str, from_role: str = "human", from_id: str = "user1") -> Dict[str, Any]:
    """
    Send a message (main entry point)
    
    Returns:
        Message dict with msg_id and delivery status
    """
    # Parse route
    route_info = parse_route(text)
    
    # Extract clean text (remove prefix)
    clean_text = text
    if text.startswith("@Station"):
        clean_text = text.replace("@Station", "", 1).strip()
    elif text.startswith("@"):
        parts = text.split(maxsplit=1)
        clean_text = parts[1] if len(parts) > 1 else ""
    elif text.startswith("#"):
        parts = text.split(maxsplit=1)
        clean_text = parts[1] if len(parts) > 1 else ""
    
    # Create message
    message = create_message(
        route=route_info["route"],
        text=clean_text,
        from_role=from_role,
        from_id=from_id,
        to=route_info["to"],
        thread_id=route_info["thread_id"]
    )
    
    # Resolve targets
    targets = resolve_targets(route_info["route"], route_info["to"], route_info["thread_id"])
    
    # Persist message
    persist_message(message)
    
    # Create and persist receipts
    receipts = create_receipts(message["msg_id"], targets)
    persist_receipts(receipts)
    
    # Emit SVF event
    try:
        from tools.svf_audit import log_communication
        log_communication(
            agent=from_id,
            action="message",
            target=",".join(targets) if targets else "all",
            message_preview=clean_text[:100],
            outcome="success",
            metadata={"msg_id": message["msg_id"], "route": route_info["route"]}
        )
    except:
        pass
    
    return {
        "message": message,
        "targets": targets,
        "receipts_created": len(receipts)
    }


def get_messages(route: Optional[str] = None, to: Optional[str] = None,
                 thread_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get message history
    
    Args:
        route: Filter by route
        to: Filter by recipient
        thread_id: Filter by thread
        limit: Max messages to return
    """
    messages = []
    
    if not MESSAGES_FILE.exists():
        return messages
    
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line)
                    
                    # Apply filters
                    if route and msg.get("route") != route:
                        continue
                    if to and msg.get("to") != to:
                        continue
                    if thread_id and msg.get("thread_id") != thread_id:
                        continue
                    
                    messages.append(msg)
    except Exception as e:
        print(f"Error reading messages: {e}")
    
    # Return most recent first
    return messages[-limit:]


def get_receipts(msg_id: str) -> List[Dict[str, Any]]:
    """Get all receipts for a message"""
    receipts = []
    
    if not RECEIPTS_FILE.exists() or RECEIPTS_FILE.stat().st_size == 0:
        return receipts
    
    try:
        with open(RECEIPTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        receipt = json.loads(line)
                        if receipt.get("msg_id") == msg_id:
                            receipts.append(receipt)
                    except json.JSONDecodeError:
                        # Skip invalid lines
                        continue
    except Exception as e:
        print(f"Error reading receipts: {e}")
    
    return receipts


if __name__ == "__main__":
    # Test
    result = send_message("@Station Hello Station Calyx")
    print(f"Sent message: {result['message']['msg_id']}")
    print(f"Targets: {result['targets']}")

