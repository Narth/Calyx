#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test pattern analysis."""
from station_calyx.core.evidence import load_recent_events
from station_calyx.agents.temporal import analyze_recurring_patterns

events = load_recent_events(500)
print(f"Loaded {len(events)} events")

patterns = analyze_recurring_patterns(events)
print(f"\nFound {len(patterns)} patterns:\n")

for p in patterns:
    print(f"  [{p.confidence.value.upper()}] {p.metric_name}")
    print(f"    {p.description}")
    print(f"    Data points: {p.data_points}, Time span: {p.time_span_hours:.1f}h")
    print()
