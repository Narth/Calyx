#!/usr/bin/env python3
"""
SVF Priority Communication Channels
Part of SVF v2.0 Phase 2 (implemented 2025-10-26)
Enables agents to prioritize communications by urgency
"""
from __future__ import annotations
    
import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
COMMS_DIR = OUT / "comms"
URGENT_DIR = COMMS_DIR / "urgent"
STANDARD_DIR = COMMS_DIR / "standard"
CASUAL_DIR = COMMS_DIR / "casual"
SHARED_LOGS = OUT / "shared_logs"
SVF_AUDIT_DIR = ROOT / "logs" / "svf_audit"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON file"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Emit evidence event for MESSAGE_RECEIVED when messages are created via SVF
        try:
            from station_calyx.core.evidence import create_event, append_event
            evt = create_event(
                event_type="OUTBOUND_MESSAGE_WRITTEN",
                node_role="svf_channels",
                summary=f"Outbound message written by {data.get('sender')} to {path.name}",
                payload={
                    "message_id": data.get('message_id'),
                    "sender": data.get('sender'),
                    "channel": data.get('channel'),
                    "direction": "outbound",
                },
                tags=["svf", "message", "outbound", data.get('channel')],
                session_id=data.get('message_id'),
            )
            append_event(evt)
        except Exception:
            pass
    except Exception as e:
        print(f"Error writing {path}: {e}")


def _emit_svf_audit(sender: str, targets: list[str], message_type: str, payload_bytes: int,
                    correlation_id: str | None = None) -> None:
    """
    Append a minimal SVF audit record to logs/svf_audit/svf_audit_YYYYMMDD.jsonl.
    Best-effort; failures should not block message delivery.
    """
    try:
        ts = datetime.now(timezone.utc)
        date_str = ts.strftime("%Y%m%d")
        fname = SVF_AUDIT_DIR / f"svf_audit_{date_str}.jsonl"
        fname.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "timestamp": ts.isoformat(),
            "route_id": f"{sender}->{','.join(targets)}",
            "source": sender,
            "targets": targets,
            "message_type": message_type,
            "payload_bytes": payload_bytes,
            "correlation_id": correlation_id or None,
        }
        with fname.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        try:
            print(f"SVF audit emit failed: {e}")
        except Exception:
            pass


def send_message(sender: str, message: str, channel: str = "standard",
                 priority: str = "medium", context: Optional[Dict[str, Any]] = None) -> str:
    """
    Send a message via priority channel
    
    Args:
        sender: Agent sending message
        message: Message content
        channel: urgent, standard, or casual
        priority: low, medium, high, urgent
        context: Additional context data
        
    Returns:
        Message ID
    """
    message_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    message_data = {
        "message_id": message_id,
        "sender": sender,
        "timestamp": timestamp,
        "channel": channel,
        "priority": priority,
        "message": message,
        "context": context or {}
    }
    
    # Choose directory based on channel
    if channel == "urgent":
        msg_file = URGENT_DIR / f"{message_id}.msg.json"  # urgent messages
    elif channel == "casual":
        msg_file = CASUAL_DIR / f"{message_id}.msg.json"
    else:
        msg_file = STANDARD_DIR / f"{message_id}.msg.json"
    
    _write_json(msg_file, message_data)
    
    # Log to shared logs
    log_entry = {
        "timestamp": timestamp,
        "type": "message",
        "message_id": message_id,
        "sender": sender,
        "channel": channel,
        "priority": priority,
        "message_preview": message[:100]
    }
    
    log_file = SHARED_LOGS / f"svf_channel_{channel}_{message_id}.md"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as f:
        f.write(f"# SVF Message: {message_id}\n\n")
        f.write(f"**Channel:** {channel.upper()}\n")
        f.write(f"**Priority:** {priority}\n")
        f.write(f"**From:** {sender}\n")
        f.write(f"**Time:** {timestamp}\n\n")
        f.write(f"## Message\n\n{message}\n\n")
        if context:
            f.write(f"## Context\n\n```json\n{json.dumps(context, indent=2)}\n```\n")

    # Emit SVF audit record (metadata only)
    ctx = context or {}
    targets = []
    if "targets" in ctx and isinstance(ctx["targets"], list):
        targets = [str(t) for t in ctx["targets"]]  # target list
    elif "target" in ctx:
        targets = [str(ctx["target"])]
    else:
        targets = [ctx.get("recipient") or "unknown"]
    mtype = ctx.get("message_type", "other")
    correlation_id = ctx.get("correlation_id")
    payload_bytes = len(message.encode("utf-8"))
    _emit_svf_audit(sender, targets, mtype, payload_bytes, correlation_id)
    
    return message_id


def get_recent_messages(channel: str = "standard", limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent messages from a channel"""
    messages = []
    
    if channel == "urgent":
        dir_path = URGENT_DIR
    elif channel == "casual":
        dir_path = CASUAL_DIR
    else:
        dir_path = STANDARD_DIR
    
    if not dir_path.exists():
        return messages
    
    for msg_file in sorted(dir_path.glob("*.msg.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            msg = json.loads(msg_file.read_text(encoding="utf-8"))
            messages.append(msg)
        except Exception:
            continue
    
    return messages


def filter_messages(agent: str, channels: List[str], priorities: List[str]) -> List[Dict[str, Any]]:
    """
    Filter messages for an agent based on preferences
    
    Args:
        agent: Agent name
        channels: List of channels to read
        priorities: List of priorities to include
        
    Returns:
        Filtered messages
    """
    all_messages = []
    
    for channel in channels:
        channel_msgs = get_recent_messages(channel, limit=50)
        all_messages.extend(channel_msgs)
    
    # Filter by priority
    filtered = [msg for msg in all_messages if msg.get("priority") in priorities]
    
    # Sort by timestamp
    filtered.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
    
    return filtered


def main():
    parser = argparse.ArgumentParser(description="SVF Priority Communication Channels")
    parser.add_argument("--send", action="store_true", help="Send a message")
    parser.add_argument("--from", dest="sender", help="Sender agent")
    parser.add_argument("--message", help="Message content")
    parser.add_argument("--channel", choices=["urgent", "standard", "casual"], default="standard")
    parser.add_argument("--priority", choices=["low", "medium", "high", "urgent"], default="medium")
    parser.add_argument("--context", help="JSON context file")
    
    parser.add_argument("--get", help="Get messages from channel")
    parser.add_argument("--limit", type=int, default=10, help="Message limit")
    
    parser.add_argument("--filter", help="Filter messages for agent")
    parser.add_argument("--channels", nargs="+", help="Channels to read")
    parser.add_argument("--priorities", nargs="+", help="Priorities to include")
    
    args = parser.parse_args()
    
    if args.send:
        context = None
        if args.context:
            context = json.loads(Path(args.context).read_text(encoding="utf-8"))
        
        msg_id = send_message(
            sender=args.sender or "unknown",
            message=args.message or "",
            channel=args.channel,
            priority=args.priority,
            context=context
        )
        print(f"Message sent: {msg_id}")
    
    elif args.get:
        messages = get_recent_messages(args.get, args.limit)
        print(f"Found {len(messages)} messages in {args.get} channel")
        for msg in messages:
            print(f"\n[{msg['priority']}] {msg['sender']}: {msg['message'][:60]}...")
    
    elif args.filter:
        if not args.channels or not args.priorities:
            print("Error: --channels and --priorities required for filtering")
            return
        
        messages = filter_messages(args.filter, args.channels, args.priorities)
        print(f"Found {len(messages)} filtered messages")
        for msg in messages:
            print(f"\n[{msg['channel']}/{msg['priority']}] {msg['sender']}: {msg['message'][:60]}...")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

