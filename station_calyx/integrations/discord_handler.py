"""Minimal Discord integration routing inbound messages to IntentGateway.

This is a lightweight handler intended for local test usage. It uses a polling
mechanism that reads messages written by an external Discord bridge into the
SVF standard channel directory. When a new message is detected, it calls
IntentGateway and writes an acknowledgment back via svf_channels.send_message.

This file intentionally avoids connecting directly to Discord APIs to keep
the environment offline-friendly and deterministic for tests.
"""
from __future__ import annotations

import time
import json
from pathlib import Path
from station_calyx.core.intent_gateway import process_inbound_message, echo_chain_info
from tools.svf_channels import get_recent_messages, send_message
from station_calyx.core.evidence import create_event, append_event
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]


def poll_and_route(channel: str = 'standard', poll_interval: float = 2.0):
    seen = set()
    while True:
        msgs = get_recent_messages(channel, limit=20)
        for m in msgs:
            mid = m.get('message_id')
            if mid in seen:
                continue
            seen.add(mid)
            # Route to intent gateway
            result = process_inbound_message(channel='discord', sender=m.get('sender','discord'), message=m.get('message',''), metadata={'message_id': mid, 'user_id': m.get('sender')}, trusted=False)
            # Send ack back to channel
            if result.get('status') == 'NEEDS_CLARIFICATION':
                text = f"Intent {result.get('intent_id')} needs clarification: {result.get('clarification_questions', ['Please clarify.'])[0]}"
            elif result.get('status') == 'ACCEPTED':
                text = f"Intent {result.get('intent_id')} accepted."
            else:
                text = f"Failed to persist intent {result.get('intent_id')}"
            # Append echo info
            try:
                echo = echo_chain_info(result.get('intent_id'))
                text += f"\nArtifact: {echo.get('artifact_path')}\nLast event: {echo.get('last_event_ts')}"
            except Exception:
                pass

            send_message(sender='cbo', message=text, channel=channel, priority='medium', context={'reply_to': mid})

            # Emit MESSAGE_ACK_SENT event
            try:
                evt_ack = create_event(
                    event_type="MESSAGE_ACK_SENT",
                    node_role="discord_handler",
                    summary=f"Acknowledgment sent for {mid}",
                    payload={"message_id": mid, "intent_id": result.get('intent_id')},
                    tags=["ack", "discord"],
                    session_id=result.get('intent_id') or mid,
                )
                append_event(evt_ack)
            except Exception:
                pass
        time.sleep(poll_interval)


if __name__ == '__main__':
    poll_and_route()
