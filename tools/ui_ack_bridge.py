"""Bridge that forwards MESSAGE_ACK_SENT events into a UI-consumable file/websocket.

Simplest implementation: append ack records to outgoing/shared_logs/ui_acks.jsonl
UI can tail this file or a websocket endpoint.
"""
from __future__ import annotations
import time
from station_calyx.core.evidence import load_recent_events
from pathlib import Path

OUT = Path.cwd() / 'outgoing' / 'shared_logs'
OUT.mkdir(parents=True, exist_ok=True)
ACKS = OUT / 'ui_acks.jsonl'

def run_once():
    events = load_recent_events(200)
    acks = [e for e in events if e.get('event_type') == 'MESSAGE_ACK_SENT']
    if not acks:
        return 0
    with ACKS.open('a', encoding='utf-8') as f:
        for a in acks:
            f.write(__import__('json').dumps(a, ensure_ascii=False) + '\n')
    return len(acks)

if __name__ == '__main__':
    print('ui_ack_bridge: one-shot run')
    n = run_once()
    print('wrote', n, 'acks')
