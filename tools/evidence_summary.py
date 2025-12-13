#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick evidence summary."""
from station_calyx.core.evidence import load_recent_events

events = load_recent_events(200)
print(f"Total events: {len(events)}")

types = {}
for e in events:
    t = e.get("event_type", "?")
    types[t] = types.get(t, 0) + 1

print("\nEvent types:")
for k, v in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# Get latest snapshot details
snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
if snapshots:
    latest = snapshots[-1]
    payload = latest.get("payload", {})
    print(f"\nLatest snapshot:")
    print(f"  CPU: {payload.get('cpu_percent', '?')}%")
    print(f"  Memory: {payload.get('memory', {}).get('percent', '?')}%")
    print(f"  Disk: {payload.get('disk', {}).get('percent_used', '?')}%")
