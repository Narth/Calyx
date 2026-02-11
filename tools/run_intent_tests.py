#!/usr/bin/env python3
"""
Deterministic intent test runner for Calyx Daemon.
Produces intents via atomic writer and validates outbox results.
Usage: python tools/run_intent_tests.py
"""
from pathlib import Path
import subprocess
import json
import uuid
import time
from datetime import datetime, timezone
import shutil
import os

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / 'governance' / 'intents' / 'inbox'
OUTBOX = ROOT / 'governance' / 'intents' / 'outbox'
PROCESSED = ROOT / 'governance' / 'intents' / 'processed'
QUARANTINE = ROOT / 'governance' / 'intents' / 'quarantine'
LOCKS = ROOT / 'logs' / 'executor' / 'locks'

# test harness init: clear artifacts to ensure deterministic run
def clean_test_artifacts():
    # remove and recreate directories to ensure no stale locks or indices remain
    paths = [OUTBOX, PROCESSED, QUARANTINE, LOCKS, ROOT / 'governance' / 'intents' / 'processing']
    for d in paths:
        try:
            if d.exists():
                # remove directory and all contents
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                # best-effort cleanup of individual files
                for f in d.glob('*'):
                    try:
                        if f.is_file():
                            f.unlink()
                        else:
                            shutil.rmtree(f)
                    except Exception:
                        pass
            except Exception:
                pass

    # remove processed index if present
    try:
        proc_idx = ROOT / 'logs' / 'executor' / 'processed_intents.json'
        if proc_idx.exists():
            proc_idx.unlink()
    except Exception:
        pass
    # remove any lingering lock files under logs/executor/locks
    try:
        locks_dir = ROOT / 'logs' / 'executor' / 'locks'
        if locks_dir.exists():
            shutil.rmtree(locks_dir)
        locks_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

clean_test_artifacts()

TESTS = []

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# Helpers
def atomic_write_intent(filename: Path, data: dict):
    cmd = ['py', '-3', 'tools/atomic_intent_writer.py', str(filename)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out,err = p.communicate(json.dumps(data))
    if p.returncode != 0:
        raise RuntimeError(f'atomic write failed: {err}')

def wait_for_outbox(intent_id: str, timeout=20):
    target = OUTBOX / f"{intent_id}.result.json"
    start = time.time()
    while time.time() - start < timeout:
        if target.exists():
            # ensure file is non-empty and valid JSON; attempt to read with retries
            try:
                content = target.read_text(encoding='utf-8')
                if not content.strip():
                    time.sleep(0.1)
                    continue
                data = json.loads(content)
                outcome = data.get('result', {}).get('outcome')
                # wait until processing placeholder is replaced with final outcome
                if outcome == 'processing':
                    time.sleep(0.1)
                    continue
                return data
            except Exception:
                # possible partial write; retry until timeout
                time.sleep(0.1)
                continue
        time.sleep(0.2)
    return None

# Test cases
TR = str(uuid.uuid4())[:8]
# 1) fs_read README.md
TESTS.append({'name':'fs_read_readme','intent':{
    'intent_id': f'intent-{TR}-fsread', 'timestamp': now_iso(), 'actor':'CBO', 'intent':'fs_read', 'payload':{'path':'README.md','max_bytes':16384}, 'justification':'test read', 'requires_approval': True
}, 'expect':'success'})
# 2) fs_list repo root
TESTS.append({'name':'fs_list_root','intent':{
    'intent_id': f'intent-{TR}-fslist', 'timestamp': now_iso(), 'actor':'CBO', 'intent':'fs_list', 'payload':{'path':'.','max_items':200}, 'justification':'test list', 'requires_approval': True
}, 'expect':'success'})
# 3) repo_grep for 'Calyx'
TESTS.append({'name':'repo_grep','intent':{
    'intent_id': f'intent-{TR}-grepp', 'timestamp': now_iso(), 'actor':'CBO', 'intent':'repo_grep', 'payload':{'pattern':'Calyx','file_ext':['.py','.md'], 'max_hits':50}, 'justification':'test grep', 'requires_approval': True
}, 'expect':'success'})
# 4) malformed JSON (write raw .json file partial)
TESTS.append({'name':'malformed','intent_file':'malformed-'+TR+'.json','malformed':True, 'expect':'validation_failed'})
# 5) duplicate intent_id
dup_id = f'intent-{TR}-dup'
TESTS.append({'name':'dup1','intent':{'intent_id':dup_id,'timestamp':now_iso(),'actor':'CBO','intent':'fs_read','payload':{'path':'README.md'},'justification':'dup test','requires_approval':True}, 'expect':'success'})
TESTS.append({'name':'dup2','intent':{'intent_id':dup_id,'timestamp':now_iso(),'actor':'CBO','intent':'fs_read','payload':{'path':'README.md'},'justification':'dup test 2','requires_approval':True}, 'expect':'skipped_duplicate'})
# 6) traversal attempt
TESTS.append({'name':'traversal','intent':{
    'intent_id': f'intent-{TR}-trv', 'timestamp': now_iso(), 'actor':'CBO', 'intent':'fs_read', 'payload':{'path':'..\\Windows\\System32'}, 'justification':'attempt traversal', 'requires_approval': True
}, 'expect':'error'})

# Run tests
results = []
seen_intents = set()

for t in TESTS:
    print('Running', t['name'])
    if t.get('malformed'):
        fname = INBOX / t['intent_file']
        INBOX.mkdir(parents=True, exist_ok=True)
        # write partial file then atomically move to inbox (invalid JSON)
        with open(str(fname)+'.pending','w',encoding='utf-8') as f:
            f.write('{"intent_id": "bad')
        Path(str(fname)+'.pending').replace(fname)
        print('Wrote malformed', fname)
        # wait for quarantine + outbox
        start = time.time()
        out = None
        while time.time() - start < 20:
            q = QUARANTINE / fname.name
            if q.exists():
                # expect outbox result for stem
                out = wait_for_outbox(fname.stem, timeout=5)
                break
            time.sleep(0.2)
        ok = out is not None and out['result']['outcome']=='validation_failed'
        results.append((t['name'], t.get('intent',{}).get('intent','malformed'), t['expect'], out['result']['outcome'] if out else 'none', ok))
        continue

    intent = t['intent']
    intent_id = intent['intent_id']
    # If this intent_id was seen previously (duplicate scenario), wait for the earlier submission to be processed
    if intent_id in seen_intents:
        print(f"Detected duplicate submission for {intent_id}; waiting for initial processing to complete")
        out_prev = wait_for_outbox(intent_id, timeout=20)
        if not out_prev:
            print(f"Warning: initial submission for {intent_id} did not produce outbox before duplicate write")
    # write to a unique filename so duplicate submissions do not overwrite the previous file
    uniq = str(uuid.uuid4())[:6]
    fname = INBOX / f"{intent_id}-{uniq}.json"
    try:
        atomic_write_intent(fname, intent)
    except Exception as e:
        print('atomic write failed', e)
        results.append((t['name'], intent['intent'], t['expect'], 'write_failed', False))
        continue
    out = wait_for_outbox(intent_id, timeout=10)
    actual = out['result']['outcome'] if out else 'none'
    ok = (t['expect']=='success' and actual=='success') or (t['expect']=='skipped_duplicate' and actual=='skipped_duplicate') or (t['expect']=='validation_failed' and actual=='validation_failed') or (t['expect']=='error' and actual!='success')
    results.append((t['name'], intent['intent'], t['expect'], actual, ok))

# Print summary
print('\nTest Summary:')
print('name | action | expected | actual | pass')
for r in results:
    print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}")

# Exit code non-zero if any fail
if not all(r[4] for r in results):
    print('One or more tests failed')
    exit(2)
print('All tests passed')
exit(0)
