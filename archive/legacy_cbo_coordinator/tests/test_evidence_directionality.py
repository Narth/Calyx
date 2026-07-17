from tools.svf_channels import send_message
from tools.dashboard_message_handler import process_dashboard_messages
from station_calyx.core.evidence import load_recent_events, get_last_event_ts


def test_evidence_directionality():
    # Capture last event timestamp
    last_ts = get_last_event_ts()

    # Send a dashboard message (outbound from dashboard perspective)
    mid = send_message(sender='dashboard', message='ping', channel='standard')

    # Process dashboard messages which will ingest and ack
    processed = process_dashboard_messages()
    assert processed >= 1

    # Collect recent events since last_ts
    events = load_recent_events(50)
    # Filter events newer than last_ts (approximate by presence order)
    # For simplicity, examine the last 20 events
    recent = events[-20:]
    types = [e.get('event_type') for e in recent]

    # Ensure outbound message written exists
    assert 'OUTBOUND_MESSAGE_WRITTEN' in types
    # Ensure gateway received the message
    assert 'MESSAGE_RECEIVED' in types
    # Ensure intent artifact created
    assert 'INTENT_ARTIFACT_CREATED' in types
    # Ensure ack sent
    assert 'MESSAGE_ACK_SENT' in types

    # Ensure ordering: find indices
    idx_out = types.index('OUTBOUND_MESSAGE_WRITTEN')
    idx_recv = types.index('MESSAGE_RECEIVED')
    idx_art = types.index('INTENT_ARTIFACT_CREATED')
    idx_ack = types.index('MESSAGE_ACK_SENT')

    assert idx_out < idx_recv < idx_art < idx_ack
