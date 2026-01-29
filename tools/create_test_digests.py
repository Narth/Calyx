#!/usr/bin/env python3
"""Create test digests with zero state changes for diminishing returns testing."""

import json
from pathlib import Path
from datetime import datetime, timezone

digests_dir = Path('station_calyx/data/digests/test-node')
digests_dir.mkdir(parents=True, exist_ok=True)

base_time = datetime(2026, 1, 10, tzinfo=timezone.utc)

for i in range(5):
    digest = {
        'digest_version': 'v1',
        'node_id': 'test-node',
        'metric_scope': None,
        'period': {
            'start': base_time.replace(day=10+i).isoformat(),
            'end': base_time.replace(day=11+i).isoformat(),
        },
        'state_changes': [],
        'state_confirmations': [
            {'metric': 'cpu_percent', 'observation_count': 100},
            {'metric': 'memory_percent', 'observation_count': 100},
        ],
    }
    
    path = digests_dir / f'truth_digest_node_test-node_2026011{i}_000000.json'
    path.write_text(json.dumps(digest, indent=2))
    print(f'Created: {path.name}')

print('Done - 5 zero-change digests created')
