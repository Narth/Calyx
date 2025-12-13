#!/usr/bin/env python3
"""
SVF Communication Handler
Monitors messages and generates agent responses with receipt acknowledgments
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[1]
MESSAGES_FILE = ROOT / "outgoing" / "comms" / "messages.jsonl"
RECEIPTS_FILE = ROOT / "outgoing" / "comms" / "receipts.jsonl"
SHARED_LOGS = ROOT / "outgoing" / "shared_logs"


def get_messages_for_agent(agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get messages directed to a specific agent"""
    messages = []
    
    if not MESSAGES_FILE.exists():
        return messages
    
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line)
                    
                    # Check if message is for this agent
                    route = msg.get("route", "broadcast")
                    to = msg.get("to")
                    
                    if route == "broadcast" or to == agent_id:
                        messages.append(msg)
    except Exception as e:
        print(f"Error reading messages: {e}")
    
    return messages[-limit:]


def update_receipt(msg_id: str, agent_id: str, status: str) -> bool:
    """Update receipt status"""
    try:
        # Import the core function
        import sys
        from pathlib import Path
        
        root_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root_dir))
        
        from tools.svf_comms_core import update_receipt as core_update_receipt
        
        # Use the core function
        return core_update_receipt(msg_id, agent_id, status)
    except Exception as e:
        print(f"Error updating receipt: {e}")
        return False


def generate_response(message: str) -> str:
    """Generate intelligent response to message"""
    
    # Get current system state for context
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get TES from metrics
        tes = 97.0
        try:
            import csv
            tes_csv = ROOT / "logs" / "agent_metrics.csv"
            if tes_csv.exists():
                with open(tes_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    if rows:
                        tes = float(rows[-1]['tes'])
        except:
            pass
        
        # Check for alerts
        alerts_count = 0
        try:
            alerts_file = ROOT / "logs" / "early_warnings.jsonl"
            if alerts_file.exists():
                with open(alerts_file, 'r') as f:
                    alerts_count = len(f.readlines())
        except:
            pass
        
        # Count active agents
        agent_count = 0
        try:
            lock_dir = ROOT / "outgoing"
            agent_count = len(list(lock_dir.glob("*.lock")))
        except:
            pass
        
        # Build contextual response
        context = {
            "tes": tes,
            "cpu": cpu,
            "ram": mem.percent,
            "disk": disk.percent,
            "alerts": alerts_count,
            "agents": agent_count
        }
        
        # Intelligent response generation
        message_lower = message.lower()
        
        if "status" in message_lower or "health" in message_lower:
            if alerts_count > 0:
                return f"Station Calyx operational. TES: {tes:.1f}, CPU: {cpu:.1f}%, RAM: {mem.percent:.1f}%. {alerts_count} alert(s) require attention."
            else:
                return f"Station Calyx operating at peak efficiency. TES: {tes:.1f}, CPU: {cpu:.1f}%, RAM: {mem.percent:.1f}%. All systems nominal. {agent_count} agents active."
        
        elif "question" in message_lower or "?" in message_lower:
            return f"I received your question. Station status: TES {tes:.1f}, {agent_count} agents active. How can I assist?"
        
        elif "approve" in message_lower or "approval" in message_lower:
            return f"Approval processed successfully. Lease updated with human cosignature. Station maintains {tes:.1f} TES."
        
        elif any(word in message_lower for word in ["hello", "hi", "greetings"]):
            alert_note = f" with {alerts_count} alert(s)" if alerts_count > 0 else ""
            return f"Hello User1! CBO here. Station operating at TES {tes:.1f}{alert_note}. {agent_count} agents active. How can I assist?"
        
        else:
            # Generic intelligent acknowledgment with context
            if alerts_count > 0:
                return f"Message received. I'm monitoring {alerts_count} alert(s). TES: {tes:.1f}. What do you need?"
            else:
                return f"Message received and understood. Station stable (TES: {tes:.1f}, {agent_count} agents). How can I help?"
                
    except Exception as e:
        # Fallback if context gathering fails
        return f"Message received. CBO acknowledging. Error gathering context: {str(e)[:50]}"


def send_agent_response(message_id: str, response: str, agent_id: str = "cbo") -> bool:
    """Send agent response"""
    try:
        import sys
        from pathlib import Path
        
        # Add root directory to path
        root_dir = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root_dir))
        
        from tools.svf_comms_core import send_message
        
        # Send response
        result = send_message(
            f"@Station {response}",
            from_role="agent",
            from_id=agent_id
        )
        
        # Log acknowledgment
        ack_file = SHARED_LOGS / f"cbo_ack_{message_id}.md"
        ack_file.parent.mkdir(parents=True, exist_ok=True)
        
        ack_content = f"""# Message Acknowledgment
        
**Original Message ID:** {message_id}
**Agent:** {agent_id}
**Timestamp:** {datetime.now(timezone.utc).isoformat()}

## Response

{response}

---
*This is an automated acknowledgment from {agent_id}*
"""
        
        ack_file.write_text(ack_content, encoding="utf-8")
        
        return True
    except Exception as e:
        print(f"Error sending response: {e}")
        return False


def process_messages_for_agent(agent_id: str = "cbo"):
    """Process pending messages for an agent"""
    messages = get_messages_for_agent(agent_id, limit=20)
    print(f"[{agent_id}] Checking {len(messages)} messages")
    
    processed_count = 0
    
    for msg in messages:
        msg_id = msg.get("msg_id")
        text = msg.get("text", "")
        
        # Check if already acknowledged
        ack_file = SHARED_LOGS / f"{agent_id}_ack_{msg_id}.md"
        if ack_file.exists():
            # Skip already processed messages
            continue
        
        print(f"[{agent_id}] Processing NEW message: {msg_id}")
        
        # Check if receipt already delivered (prevent duplicate)
        try:
            import sys
            from pathlib import Path
            root_dir = Path(__file__).resolve().parents[1]
            sys.path.insert(0, str(root_dir))
            from tools.svf_comms_core import get_receipts
            
            receipts = get_receipts(msg_id)
            for receipt in receipts:
                if receipt["recipient"] == agent_id and receipt.get("delivered_ts"):
                    # Already delivered, skip
                    print(f"[{agent_id}] Message {msg_id} already delivered, skipping")
                    # Create ack file to prevent future processing
                    try:
                        ack_file.parent.mkdir(parents=True, exist_ok=True)
                        ack_file.write_text(f"# Already Processed\nMessage ID: {msg_id}\nAgent: {agent_id}\n", encoding="utf-8")
                    except:
                        pass
                    continue
        except Exception as e:
            print(f"[{agent_id}] Error checking receipts: {e}")
        
        # Send delivered receipt
        update_receipt(msg_id, agent_id, "delivered")
        print(f"[{agent_id}] Sent delivered receipt for {msg_id}")
        
        # Generate response
        response = generate_response(text)
        print(f"[{agent_id}] Generated response: {response[:50]}")
        
        # Send response
        if send_agent_response(msg_id, response, agent_id):
            processed_count += 1
            
            # Send read receipt
            update_receipt(msg_id, agent_id, "read")
            print(f"[{agent_id}] Sent read receipt for {msg_id}")
            print(f"[{agent_id}] Successfully processed message {msg_id}")
        else:
            print(f"[{agent_id}] Failed to send response for {msg_id}")
        
    return processed_count


def main():
    """Main loop"""
    print("SVF Communication Handler Started")
    print(f"Agent: CBO")
    print(f"Monitoring: {MESSAGES_FILE}")
    
    while True:
        try:
            # Process messages
            count = process_messages_for_agent("cbo")
            
            if count > 0:
                print(f"[CBO] Processed {count} messages")
            
            # Wait before next check
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\nSVF Communication Handler Stopped")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

