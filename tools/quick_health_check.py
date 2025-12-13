#!/usr/bin/env python3
"""Quick Station Calyx Health Check"""
import json
from pathlib import Path
from datetime import datetime

OUT = Path('outgoing')
agents = []

for lock in OUT.glob('*.lock'):
    try:
        data = json.loads(lock.read_text())
        if 'ts' in data:
            age = datetime.now().timestamp() - data['ts']
            agents.append({
                'name': lock.stem,
                'status': data.get('status', 'unknown'),
                'age_min': round(age/60, 1),
                'flow': 'MOVING' if age < 60 else 'PARKED' if age < 300 else 'STALLED'
            })
    except Exception:
        pass

agents.sort(key=lambda x: x['age_min'])

active = [a for a in agents if a['flow'] == 'MOVING']
parked = [a for a in agents if a['flow'] == 'PARKED']
stalled = [a for a in agents if a['flow'] == 'STALLED']

print('\n=== Station Calyx Health Report ===')
print(f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'\nActive (MOVING): {len(active)}/{len(agents)}')
for a in active:
    print(f'  ?? {a["name"]}: {a["status"]} ({a["age_min"]}m old)')

print(f'\nParked (1-5min): {len(parked)}')
for a in parked[:8]:
    print(f'  ?? {a["name"]}: {a["status"]} ({a["age_min"]}m old)')

print(f'\nStalled (>5min): {len(stalled)}')
for a in stalled[:8]:
    print(f'  ?? {a["name"]}: {a["status"]} ({a["age_min"]}m old)')

# Determine posture
if len(active) > 8:
    posture = "?? CALM"
elif len(active) > 3:
    posture = "?? MODERATE"
else:
    posture = "?? DISTRESSED"

print(f'\nSystem Posture: {posture}')
print(f'Total Agents Tracked: {len(agents)}')
print('='*40)
