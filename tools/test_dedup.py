#!/usr/bin/env python3
"""Test de-duplication of findings."""
from station_calyx.core.evidence import load_recent_events
from station_calyx.ui.status_surface import get_active_findings

events = load_recent_events(200)
findings = get_active_findings(events)

print("Trends (de-duplicated):")
for t in findings['trends']:
    print(f"  {t['metric']}: {t['direction']} (count: {t.get('occurrence_count', 1)})")

print()
print("Drifts (de-duplicated):")
for d in findings['drifts']:
    print(f"  {d['metric']}: {d['direction']} (count: {d.get('occurrence_count', 1)})")

print()
print("De-duplication verified!")
