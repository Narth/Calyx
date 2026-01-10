#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a valid test evidence bundle with correct hashes."""

import json
from pathlib import Path

from station_calyx.schemas.evidence_envelope_v1 import create_envelope

# Create a chain of 5 envelopes
envelopes = []
prev_hash = None

payloads = [
    {"cpu_percent": 15.2, "memory": {"percent": 38.5}, "disk": {"percent_used": 72.1}},
    {"cpu_percent": 22.8, "memory": {"percent": 41.2}, "disk": {"percent_used": 72.2}},
    {"cpu_percent": 8.5, "memory": {"percent": 39.8}, "disk": {"percent_used": 72.2}},
    {"cpu_percent": 45.1, "memory": {"percent": 52.3}, "disk": {"percent_used": 72.3}},
    {"cpu_percent": 12.0, "memory": {"percent": 40.1}, "disk": {"percent_used": 72.3}},
]

for i, payload in enumerate(payloads):
    env = create_envelope(
        node_id="laptop-observer-001",
        seq=i,
        event_type="SYSTEM_SNAPSHOT",
        payload=payload,
        collector_version="v1.6.0",
        node_name="Laptop Observer",
        prev_hash=prev_hash,
    )
    
    envelopes.append(env)
    prev_hash = env.compute_envelope_hash()

# Write to file
output_path = Path("tests/fixtures/valid_evidence_bundle.jsonl")
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    for env in envelopes:
        f.write(env.to_canonical_json() + "\n")

print(f"Generated {len(envelopes)} envelopes to {output_path}")

# Also print for verification
for env in envelopes:
    print(f"seq={env.seq}, payload_hash={env.payload_hash[:16]}..., prev_hash={env.prev_hash[:16] if env.prev_hash else 'null'}...")
