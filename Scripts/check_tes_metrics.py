#!/usr/bin/env python3
"""Quick TES metrics analysis"""
import csv
from pathlib import Path

rows = list(csv.DictReader(open('logs/agent_metrics.csv')))
tes_values = [float(r['tes']) for r in rows if r.get('tes')]

print(f"Total rows: {len(rows)}")
print(f"Recent 50 avg: {sum(tes_values[-50:])/50:.2f}")
print(f"Last 20 avg: {sum(tes_values[-20:])/20:.2f}")
print(f"All-time avg: {sum(tes_values)/len(tes_values):.2f}")
print(f"Recent 10: {[f'{v:.1f}' for v in tes_values[-10:]]}")

