"""Test run: Discord ping via SVF -> IntentGateway -> ack
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.svf_channels import send_message
from station_calyx.core.intent_gateway import process_inbound_message, echo_chain_info
from station_calyx.core.evidence import load_recent_events, create_event, append_event

# Send outbound discord message
discord_sender = '1234567890'
mid = send_message(sender=discord_sender, message='ping', channel='standard', context={})
print('discord outbound msg id:', mid)

# Ingest via gateway
res = process_inbound_message(channel='discord', sender=discord_sender, message='ping', metadata={'message_id': mid, 'user_id': discord_sender})
print('ingest result:', res)

# Send ack back via SVF
ack_text = f"Intent {res.get('intent_id')} status={res.get('status')}"
ack_mid = send_message(sender='cbo', message=ack_text, channel='standard', context={'reply_to': mid})
print('ack outbound id:', ack_mid)

# Emit MESSAGE_ACK_SENT evidence
try:
    evt = create_event(
        event_type='MESSAGE_ACK_SENT',
        node_role='discord_test',
        summary=f'Acknowledgment sent for {mid}',
        payload={'message_id': mid, 'intent_id': res.get('intent_id')},
        tags=['ack','discord'],
        session_id=res.get('intent_id')
    )
    append_event(evt)
except Exception as e:
    print('failed to append ack event', e)

# Print related evidence lines
events = load_recent_events(50)
for e in events[-50:]:
    if e.get('payload') and (e['payload'].get('message_id') in (mid, ack_mid) or e.get('session_id') == res.get('intent_id')):
        print(e)
