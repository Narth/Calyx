#!/usr/bin/env python3
"""
Dashboard API: Chat Module
Phase A - Backend Skeleton
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[3]


def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get chat history from SVF Comms
    
    Args:
        limit: Number of messages
        
    Returns:
        Message history
    """
    messages = []
    
    try:
        # Use SVF channels core (file-backed message store)
        from tools.svf_channels import get_recent_messages

        comms_messages = get_recent_messages(channel='standard', limit=limit)
        
        for msg in comms_messages:
                msg_id = msg.get("message_id") or msg.get("msg_id", "")
            
            # Get receipt status for enrichment
            receipt_data = None
            if msg_id:
                try:
                    receipt_data = get_receipt_status(msg_id)
                except:
                    pass
            
                # Map svf_channels message fields to dashboard schema
                messages.append({
                    "message_id": msg_id,
                    "timestamp": msg.get("timestamp") or msg.get("ts", ""),
                    "sender": msg.get("sender", "unknown"),
                    "recipient": msg.get("context", {}).get("recipient", "all"),
                    "channel": msg.get("channel", "standard"),
                    "content": msg.get("message") or msg.get("text", ""),
                    "status": "delivered",
                    "metadata": {
                        "thread_id": msg.get("context", {}).get("thread_id"),
                        "priority": msg.get("priority", "normal"),
                        "receipt_status": receipt_data.get("status", "queued") if receipt_data else "queued",
                        "receipt_delivered": receipt_data.get("delivered", 0) if receipt_data else 0,
                        "receipt_read": receipt_data.get("read", 0) if receipt_data else 0,
                        "receipt_total": receipt_data.get("total_recipients", 0) if receipt_data else 0
                    }
                })
    except Exception as e:
        print(f"Error getting chat history: {e}")
    
    return messages


def send_broadcast(content: str, priority: str = "medium") -> bool:
    """
    Send broadcast message via SVF Comms
    
    Args:
        content: Message content
        priority: Message priority
        
    Returns:
        True if successful
    """
    try:
        # Fix import path
        import sys
        from pathlib import Path
        
        # Add root directory to path
        root_dir = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root_dir))
        
        # Use new SVF Comms core
        from tools.svf_comms_core import send_message
        
        # Send via SVF Comms (will parse @Station prefix)
        result = send_message(f"@Station {content}", from_role="human", from_id="user1")
        
        return True
    except Exception as e:
        print(f"Error sending broadcast: {e}")
        return False


def get_receipt_status(msg_id: str) -> Dict[str, Any]:
    """
    Get receipt status for a message
    
    Args:
        msg_id: Message ID
        
    Returns:
        Receipt status summary
    """
    try:
        import sys
        from pathlib import Path
        
        root_dir = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root_dir))
        
        from tools.svf_comms_core import get_receipts
        
        receipts = get_receipts(msg_id)
        
        total = len(receipts)
        delivered = sum(1 for r in receipts if r.get("delivered_ts"))
        read = sum(1 for r in receipts if r.get("read_ts"))
        
        return {
            "msg_id": msg_id,
            "total_recipients": total,
            "delivered": delivered,
            "read": read,
            "status": "read" if read == total else "delivered" if delivered == total else "queued"
        }
    except Exception as e:
        print(f"Error getting receipt status: {e}")
        return {
            "msg_id": msg_id,
            "total_recipients": 0,
            "delivered": 0,
            "read": 0,
            "status": "error"
        }


def get_agent_responses(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get agent responses to dashboard messages
    
    Args:
        limit: Number of responses
        
    Returns:
        Agent response list
    """
    responses = []
    
    # Check for acknowledgment files
    shared_logs_dir = ROOT / "outgoing" / "shared_logs"
    if shared_logs_dir.exists():
        ack_files = sorted(shared_logs_dir.glob("dashboard_ack_*.md"), reverse=True)
        
        for ack_file in ack_files[:limit]:
            try:
                content = ack_file.read_text(encoding="utf-8")
                
                # Parse markdown to extract response
                import re
                msg_id_match = re.search(r'\*\*Original Message ID:\*\* (.+)', content)
                reply_id_match = re.search(r'\*\*Reply Message ID:\*\* (.+)', content)
                timestamp_match = re.search(r'\*\*Timestamp:\*\* (.+)', content)
                response_match = re.search(r'## Response\n\n(.+?)\n\n---', content, re.DOTALL)
                
                if response_match:
                    responses.append({
                        "message_id": reply_id_match.group(1) if reply_id_match else "",
                        "timestamp": timestamp_match.group(1) if timestamp_match else "",
                        "sender": "CBO",
                        "recipient": "dashboard",
                        "channel": "agent_response",
                        "content": response_match.group(1).strip(),
                        "status": "delivered",
                        "metadata": {
                            "reply_to": msg_id_match.group(1) if msg_id_match else "",
                            "type": "agent_response"
                        }
                    })
            except Exception:
                continue
    
    return responses


def send_direct_message(recipient: str, content: str) -> bool:
    """
    Send direct message via SVF Comms
    
    Args:
        recipient: Recipient agent ID
        content: Message content
        
    Returns:
        True if successful
    """
    try:
        # Fix import path
        import sys
        from pathlib import Path
        
        # Add root directory to path
        root_dir = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(root_dir))
        
        # Use new SVF Comms core
        from tools.svf_comms_core import send_message
        
        # Send direct message (will parse @agent prefix)
        result = send_message(f"@{recipient} {content}", from_role="human", from_id="user1")
        
        return True
    except Exception as e:
        print(f"Error sending direct message: {e}")
        return False

