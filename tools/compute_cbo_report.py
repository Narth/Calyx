#!/usr/bin/env python3
"""Compute brief CBO report: uptime %, self-recoveries, policy violations.

Reads:
- outgoing/autonomy_runner.log
- outgoing/autonomy_errors.log
- outgoing/bridge/last_pulse_report.json

Writes a JSON summary to outgoing/cbo_uptime_report.json and prints a short human summary.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outgoing'
RUN_LOG = OUT / 'autonomy_runner.log'
ERR_LOG = OUT / 'autonomy_errors.log'
LAST_PULSE = OUT / 'bridge' / 'last_pulse_report.json'
OUT_SUM = OUT / 'cbo_uptime_report.json'

def parse_runner():
    if not RUN_LOG.exists():
        return {}
    lines = RUN_LOG.read_text(encoding='utf-8').splitlines()
    rc_re = re.compile(r'rc=(\d+)')
    timestamps = []
    rc_vals = []
    for ln in lines:
        # try to parse ISO timestamp at start
        parts = ln.split(' ', 1)
        if parts:
            ts = parts[0]
            timestamps.append(ts)
        m = rc_re.search(ln)
        if m:
            rc_vals.append(int(m.group(1)))
    total = len(rc_vals)
    failures = sum(1 for v in rc_vals if v != 0)
    successes = total - failures
    uptime_pct = (successes / total * 100.0) if total > 0 else 0.0
    return {
        'total_pulses': total,
        'failed_pulses': failures,
        'success_pulses': successes,
        'uptime_pct': round(uptime_pct, 3),
        'first_ts': timestamps[0] if timestamps else None,
        'last_ts': timestamps[-1] if timestamps else None,
    }

def count_self_recoveries():
    # A self-recovery is defined as a non-zero rc followed by a zero rc in the next pulse
    if not RUN_LOG.exists():
        return 0
    lines = RUN_LOG.read_text(encoding='utf-8').splitlines()
    rc_re = re.compile(r'rc=(\d+)')
    seq = [int(m.group(1)) for ln in lines for m in [rc_re.search(ln)] if m]
    recoveries = 0
    for a,b in zip(seq, seq[1:]):
        if a != 0 and b == 0:
            recoveries += 1
    return recoveries

def read_policy_violations():
    violations = []
    if LAST_PULSE.exists():
        try:
            j = json.loads(LAST_PULSE.read_text(encoding='utf-8'))
            v = j.get('guardrails', {}).get('violations', [])
            if v:
                violations.extend(v)
        except Exception:
            pass
    # Also scan autonomy_errors.log for policy-like markers
    if ERR_LOG.exists():
        txt = ERR_LOG.read_text(encoding='utf-8')
        # simple heuristics
        if 'guardrail' in txt.lower() or 'violation' in txt.lower():
            violations.append('See outgoing/autonomy_errors.log for guardrail traces')
    return violations

def main():
    rpt = {}
    rpt['runner'] = parse_runner()
    rpt['self_recoveries'] = count_self_recoveries()
    rpt['policy_violations'] = read_policy_violations()
    rpt['generated_at'] = datetime.now(timezone.utc).isoformat()
    OUT_SUM.write_text(json.dumps(rpt, indent=2), encoding='utf-8')
    # print short human summary
    print('CBO Uptime Report:')
    print(f"  Pulses: {rpt['runner'].get('total_pulses',0)}  Success: {rpt['runner'].get('success_pulses',0)}  Failed: {rpt['runner'].get('failed_pulses',0)}")
    print(f"  Uptime: {rpt['runner'].get('uptime_pct',0.0)}%")
    print(f"  Self-recoveries: {rpt['self_recoveries']}")
    if rpt['policy_violations']:
        print('  Policy violations:')
        for v in rpt['policy_violations']:
            print('   -', v)
    else:
        print('  Policy violations: None')

if __name__ == '__main__':
    main()
