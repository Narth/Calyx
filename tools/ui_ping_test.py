"""UI ping test: send a dashboard-originated ping and verify evidence chain.

Run: python tools/ui_ping_test.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.svf_channels import send_message
from tools.dashboard_message_handler import process_dashboard_messages
from station_calyx.core.evidence import load_recent_events
from station_calyx.core.session_router import set_selected_session, get_selected_session
from station_calyx.core.config import get_config


def run():
    # Set session route to UI-selected lane
    set_selected_session('agent:main:main', user_id='user-ui-1')
    sel_session, sel_user = get_selected_session()
    print('Session route set ->', sel_session, sel_user)

    # Send dashboard message without explicit session_user (UI would rely on router)
    mid = send_message(sender='dashboard', message='ping-ui-1', channel='standard', context={})
    print('Outbound dashboard message id:', mid)

    # Process pending dashboard messages (one-shot)
    processed = process_dashboard_messages()
    print('Processed count:', processed)

    # Read recent evidence
    events = load_recent_events(100)
    recent = events[-40:]
    for e in recent:
        # print only related to this message or recent intents
        payload = e.get('payload') or {}
        sid = e.get('session_id')
        if payload.get('message_id') == mid or (sid and sid.startswith('intent-')):
            print(e)

    print('\nEvidence file path:', get_config().evidence_path)
    print('Intent artifacts dir:', get_config().data_dir / 'intents')
    print('SVF outgoing dir:', ROOT / 'outgoing' / 'comms' / 'standard')
    print('Ack sink (dashboard):', ROOT / 'outgoing' / 'shared_logs')

if __name__ == '__main__':
    run()
