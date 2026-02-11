"""Intent Echo+Clarify Mode Test Runner

Performs an end-to-end echo and clarification test for Dashboard and Discord
using the SVF channels and IntentGateway. SAFE_MODE is enabled to prevent any
execution; results are written to evidence and audit logs.

Run:
    python tools/intent_test_run.py

Outputs:
 - prints evidence paths and a short evidence chain for each message
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
import sys

# Ensure repository root is on sys.path so local packages can be imported when running
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from station_calyx.core.system_mode import set_system_mode, get_system_mode
from station_calyx.core.evidence import load_recent_events
from tools.svf_channels import send_message, get_recent_messages
from tools.dashboard_message_handler import process_dashboard_messages
from station_calyx.integrations.discord_handler import echo_chain_info
from station_calyx.core.intent_gateway import process_inbound_message
from station_calyx.core.user_model import record_confirmation, load_user_model
from station_calyx.core.evidence import create_event, append_event

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "station_calyx" / "data" / "evidence.jsonl"
INTENTS_DIR = ROOT / "station_calyx" / "data" / "intents"
USERS_DIR = ROOT / "station_calyx" / "data" / "users"


def emit_service_online(name: str):
    evt = create_event(
        event_type="SERVICE_ONLINE",
        node_role=name,
        summary=f"Service {name} online",
        payload={"service": name, "ts": datetime.now(timezone.utc).isoformat()},
        tags=["service", "online"],
        session_id=None,
    )
    append_event(evt)


def run():
    print("Starting Intent Echo+Clarify test in SAFE MODE")
    set_system_mode(safe_mode=True, deny_execution=True, reason="Phase 3/Intent Test")
    print("System mode:", get_system_mode())

    # Emit SERVICE_ONLINE for components
    services = ["intent_gateway", "dashboard_handler", "discord_handler"]
    for s in services:
        emit_service_online(s)

    print("Services marked online. Sending test messages...")

    # 1) Send dashboard message (include session_user to bind identity)
    dash_mid = send_message(sender="dashboard", message="ping", channel="standard", context={"session_user": "user-test-01", "user_id": "user-test-01"})
    print(f"Dashboard outbound message id: {dash_mid}")

    # 2) Send discord message (sender is numeric id)
    discord_sender = "1234567890"
    disc_mid = send_message(sender=discord_sender, message="ping", channel="standard", context={})
    print(f"Discord outbound message id: {disc_mid}")

    # Short delay to ensure files written
    time.sleep(0.5)

    # Process dashboard messages (one-shot)
    processed = process_dashboard_messages()
    print(f"Dashboard processed count: {processed}")

    # One-shot process for discord messages
    msgs = get_recent_messages(channel="standard", limit=20)
    handled = 0
    for m in msgs:
        if m.get("sender") == discord_sender:
            res = process_inbound_message(channel='discord', sender=m.get('sender'), message=m.get('message'), metadata={'message_id': m.get('message_id'), 'user_id': m.get('sender')})
            print("Discord ingest result:", res)
            # Send ack back
            ack_text = f"Intent {res.get('intent_id')} status={res.get('status')}"
            send_message(sender='cbo', message=ack_text, channel='standard', context={'reply_to': m.get('message_id')})
            handled += 1
    print(f"Discord handled: {handled}")

    # Wait a moment for evidence writes
    time.sleep(0.5)

    # Collect recent events and print chains for intents
    events = load_recent_events(100)
    print(f"Loaded {len(events)} recent evidence events (tail 40):")
    for e in events[-40:]:
        print(f"{e.get('event_type')} - {e.get('node_role')} - {e.get('session_id')} - {e.get('summary')}")

    # For each intent artifact in intents dir, print user model entries
    if INTENTS_DIR.exists():
        for f in sorted(INTENTS_DIR.glob('*.json')):
            print(f"Intent file: {f}")

    if USERS_DIR.exists():
        for f in sorted(USERS_DIR.glob('*.json')):
            print(f"User model file: {f}")
            print(f.read_text(encoding='utf-8'))

    print("Test run complete. Evidence path:", EVIDENCE_PATH)


if __name__ == '__main__':
    run()
