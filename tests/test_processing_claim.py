import shutil
import json
from pathlib import Path
from tools.calyx_daemon import run_once

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / 'governance' / 'intents' / 'inbox'
PROCESSED = ROOT / 'governance' / 'intents' / 'processed'
OUTBOX = ROOT / 'governance' / 'intents' / 'outbox'


def setup_dirs():
    for d in [INBOX, PROCESSED, OUTBOX]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)


def test_claim_and_process():
    setup_dirs()
    intent = {'intent_id': 'test-claim-1', 'intent': 'fs_read', 'payload': {'path':'README.md'}, 'requires_approval': True}
    fname = INBOX / (intent['intent_id'] + '-1.json')
    fname.write_text(json.dumps(intent), encoding='utf-8')
    run_once()
    # after run_once, outbox should have result and processed file moved
    out = OUTBOX / (intent['intent_id'] + '.result.json')
    assert out.exists()
    proc_file = PROCESSED / fname.name
    assert proc_file.exists()
