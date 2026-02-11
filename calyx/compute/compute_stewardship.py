#!/usr/bin/env python3
"""
Compute stewardship: enforces compute budgets, dedupe, yield/backoff and sleep-mode rules.
"""
from __future__ import annotations
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'governance' / 'policies' / 'compute_stewardship_policy.json'
COMPUTE_LOG_DIR = ROOT / 'logs' / 'compute'
COMPUTE_LOG_DIR.mkdir(parents=True, exist_ok=True)
COMPUTE_LOG = COMPUTE_LOG_DIR / 'compute_log.jsonl'
YIELD_LOG = COMPUTE_LOG_DIR / 'yield_log.jsonl'
STATION_MODE = ROOT / 'governance' / 'state' / 'station_mode.json'


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def compute_signature(intent: Dict[str, Any]) -> str:
    # canonical JSON then sha256
    s = json.dumps(intent, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def load_policy() -> Dict[str, Any]:
    try:
        return json.loads(POLICY.read_text(encoding='utf-8'))
    except Exception:
        return {}


def attach_default_contract(intent: Dict[str, Any]) -> Dict[str, Any]:
    pol = load_policy()
    defaults = pol.get('defaults', {})
    contract = {
        'intent_id': intent.get('intent_id') or intent.get('id') or str(time.time()),
        'mode': defaults.get('mode', 'ACTIVE'),
        'budgets': defaults.get('budgets', {}),
        'cadence': defaults.get('cadence', {}),
        'yield': defaults.get('yield', {}),
        'dedupe': {
            'signature': compute_signature({'intent': intent.get('intent'), 'payload': intent.get('payload')}),
            'idempotency_key': intent.get('intent_id') or intent.get('id') or None
        },
        'allowed_actions': pol.get('sleep_allowlist', []),
        'value_definition': 'state_delta'
    }
    intent['compute_contract'] = contract
    return intent


def estimate_cost(intent: Dict[str, Any]) -> Dict[str, Any]:
    # Simple heuristic: tokens ~ len of prompt / 4; tool calls ~ count of known tools
    payload = intent.get('payload', {}) or {}
    prompt = json.dumps(payload) if isinstance(payload, dict) else str(payload)
    tokens_est = max(1, int(len(prompt) / 4))
    tools = 0
    if isinstance(payload, dict):
        for k in ('url', 'paths', 'files', 'pattern'):
            if k in payload:
                tools += 1
    return {'tokens_in': tokens_est, 'tokens_out': 0, 'tool_calls': tools, 'est_seconds': 1 + tools}


def read_station_mode() -> str:
    try:
        if STATION_MODE.exists():
            st = json.loads(STATION_MODE.read_text(encoding='utf-8'))
            return st.get('mode', 'ACTIVE')
    except Exception:
        pass
    return 'ACTIVE'


def should_execute(intent: Dict[str, Any], state: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[float]]:
    """Decide whether to execute. Return (allow, reason, next_eligible_at).
    state is a small dict with recent metrics for the signature.
    """
    contract = intent.get('compute_contract')
    if not contract:
        intent = attach_default_contract(intent)
        contract = intent.get('compute_contract')

    sig = contract.get('dedupe', {}).get('signature')
    mode = contract.get('mode', 'ACTIVE')
    pol = load_policy()

    # Sleep mode restrictions
    if read_station_mode() == 'SLEEP' or mode == 'SLEEP':
        # Only allow actions in allowlist
        allowed = pol.get('sleep_allowlist', [])
        if intent.get('intent') not in allowed:
            return False, 'sleep_restriction', None
    # Budget gate (estimate)
    est = estimate_cost(intent)
    b = contract.get('budgets', {})
    if est['tokens_in'] > b.get('max_input_tokens', 0):
        return False, 'budget_exceeded_input', None
    if est['tool_calls'] > b.get('max_tool_calls', 0):
        return False, 'budget_exceeded_tools', None

    # Dedupe/cadence
    now = time.time()
    entry = state.get(sig, {})
    last_run = entry.get('last_run')
    if last_run:
        min_int = contract.get('cadence', {}).get('min_interval_seconds', 0)
        if now - last_run < min_int:
            return False, 'skipped_duplicate', None

    # Yield gate: simplified rolling check
    win = entry.get('window', {})
    # compute yield = state_changes / confirmations
    confirmations = win.get('confirmations', 0)
    state_changes = win.get('state_changes', 0)
    obs = contract.get('yield', {})
    if confirmations >= obs.get('confirmations_limit', 9999):
        yield_ratio = (state_changes / confirmations) if confirmations > 0 else 0.0
        if yield_ratio < obs.get('yield_threshold', 0.1):
            # schedule backoff
            backoff = contract.get('cadence', {}).get('backoff_seconds', 30)
            return False, 'diminishing_returns', now + backoff

    return True, None, None


def record_outcome(intent: Dict[str, Any], signature: str, usage: Dict[str, Any], outcome: str, state_changed: bool, next_eligible_at: Optional[float] = None):
    # append compute log
    try:
        entry = {
            'timestamp': _now_iso(),
            'intent_id': intent.get('intent_id'),
            'signature': signature,
            'mode': intent.get('compute_contract', {}).get('mode'),
            'tokens_in': usage.get('tokens_in', 0),
            'tokens_out': usage.get('tokens_out', 0),
            'tool_calls': usage.get('tool_calls', 0),
            'wall_seconds': usage.get('wall_seconds', 0),
            'outcome': outcome
        }
        with COMPUTE_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass

    # update yield log entry for signature window
    try:
        window = {
            'window_start': int(time.time()) - 3600,
            'window_end': int(time.time()),
            'state_changes': 1 if state_changed else 0,
            'confirmations': 1,
            'yield': 1.0 if state_changed else 0.0,
            'backoff_level': 0,
            'next_eligible_at': next_eligible_at
        }
        with YIELD_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(window, ensure_ascii=False) + '\n')
    except Exception:
        pass


def compute_status() -> Dict[str, Any]:
    # Summarize recent compute logs (very small summarization)
    out = {'total_executions': 0, 'recent_errors': [], 'last_timestamp': None}
    try:
        if COMPUTE_LOG.exists():
            lines = COMPUTE_LOG.read_text(encoding='utf-8').splitlines()
            out['total_executions'] = len(lines)
            if lines:
                last = json.loads(lines[-1])
                out['last_timestamp'] = last.get('timestamp')
    except Exception:
        pass
    return out
