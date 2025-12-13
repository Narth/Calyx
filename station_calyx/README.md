# Station Calyx — Node Evidence Relay v0

**[CBO • Governance]: Local evidence collection and batch export for distributed truth capture.**

## Overview

The Station Calyx evidence system provides append-only local journaling of telemetry, events, and system state with cryptographic integrity (hash chaining). Evidence is collected locally with no network dependency, then exported as batch files for manual or automated transfer.

This is the **Laptop Observer** edition — designed for external Station Calyx nodes that operate independently and synchronize via batch export/import.

### Key Principles

- **Append-Only**: Evidence is never modified after write
- **Hash-Chained**: Cryptographic linkage between envelopes (`prev_hash`)
- **Monotonic Sequence**: Strictly incrementing counters (1, 2, 3...)
- **Node Attribution**: All evidence traceable to origin node
- **Zero Network**: Local operations only; export is file-based

## Architecture

```
Telemetry/Events ? Evidence Envelope ? Journal (append) ? Export Batch
                         ?
              [node_id, seq, prev_hash, payload, envelope_hash]
```

### Components

| Module | Purpose |
|--------|---------|
| `station_calyx/node/node_identity.py` | Generate & persist stable node_id |
| `station_calyx/node/sequence.py` | Monotonic counter with disk persistence |
| `station_calyx/evidence/schemas.py` | `EvidenceEnvelopeV1` schema |
| `station_calyx/evidence/journal.py` | Append-only JSONL writer with chaining |
| `tools/telemetry_evidence_bridge.py` | Hook telemetry into evidence journal |
| `tools/export_evidence_batch.py` | Generate export bundles |
| `tools/verify_evidence_system.py` | Verification suite |

## Quick Start

### 1. Verify System

Run verification suite to ensure all components work:

```powershell
python -u .\tools\verify_evidence_system.py
```

Expected output:
```
? PASS: Node Identity
? PASS: Sequence Monotonic
? PASS: Evidence Journal
? PASS: Export Batch
? ALL TESTS PASSED — Evidence system operational
```

### 2. Generate Evidence

Run telemetry bridge to capture snapshots:

```powershell
# One-shot capture
python -u .\tools\telemetry_evidence_bridge.py

# Continuous mode (30s intervals)
python -u .\tools\telemetry_evidence_bridge.py --interval 30
```

### 3. Export Batch

Generate export bundle for transfer:

```powershell
python -u .\tools\export_evidence_batch.py
```

Creates: `exports/evidence_bundle_<node_id>_<timestamp>.jsonl`

## File Structure

```
station_calyx/
  __init__.py
  node/
    __init__.py
    node_identity.py     # Node ID generation
    sequence.py          # Monotonic counter
  evidence/
    __init__.py
    schemas.py           # EvidenceEnvelopeV1
    journal.py           # Append-only writer

tools/
  telemetry_evidence_bridge.py  # Telemetry ? Evidence
  export_evidence_batch.py      # Export bundles
  verify_evidence_system.py     # Verification suite

logs/evidence/
  <node_id>/
    evidence.jsonl       # Append-only journal

exports/
  evidence_bundle_*.jsonl  # Export bundles

outgoing/node/
  identity.json          # Persistent node identity
  sequence.json          # Monotonic counter state
  export_index.json      # Last exported sequence
```

## Evidence Envelope Schema (v1)

```json
{
  "node_id": "node_calyx_a3f8c2d1",
  "seq": 42,
  "timestamp": "2025-01-09T12:34:56.789",
  "evidence_type": "telemetry_snapshot",
  "payload": {
    "active_count": 5,
    "drift": {"agent1_scheduler": {"latest": 0.42}}
  },
  "prev_hash": "a1b2c3d4e5f6...",
  "envelope_hash": "9876543210ab...",
  "tags": ["telemetry", "system_health"],
  "source": "telemetry_evidence_bridge",
  "version": "v1"
}
```

### Fields

| Field | Description |
|-------|-------------|
| `node_id` | Stable node identifier (hardware-fingerprinted) |
| `seq` | Monotonic sequence number (1, 2, 3...) |
| `timestamp` | ISO 8601 timestamp |
| `evidence_type` | Type enum (telemetry_snapshot, agent_heartbeat, etc.) |
| `payload` | Evidence content (arbitrary JSON) |
| `prev_hash` | SHA-256 hash of previous envelope (chain integrity) |
| `envelope_hash` | SHA-256 hash of this envelope |
| `tags` | Optional categorization tags |
| `source` | Source identifier (script/agent name) |
| `version` | Schema version (v1) |

### Evidence Types

- `telemetry_snapshot` — System telemetry state
- `agent_heartbeat` — Individual agent heartbeat
- `system_event` — Significant system events
- `audit_log` — Audit trail entries
- `task_completion` — Task execution records
- `metric_sample` — Individual metric samples
- `error_trace` — Error/exception traces
- `cbo_directive` — CBO governance directives
- `chain_anchor` — Genesis/checkpoint envelopes

## API Usage

### Append Evidence (Simple)

```python
from station_calyx.evidence import append_evidence, EvidenceType

envelope = append_evidence(
    evidence_type=EvidenceType.TELEMETRY_SNAPSHOT,
    payload={"active_count": 5, "drift": {"latest": 0.42}},
    tags=["telemetry"],
    source="my_script"
)

print(f"Written: seq={envelope.seq}, hash={envelope.envelope_hash}")
```

### Use Journal Directly

```python
from station_calyx.evidence import EvidenceJournal, EvidenceType

journal = EvidenceJournal()

# Write envelope
envelope = journal.append(
    evidence_type=EvidenceType.SYSTEM_EVENT,
    payload={"event": "startup", "version": "1.0"},
    tags=["lifecycle"],
    source="main"
)

# Read all envelopes
envelopes = journal.read_all()

# Verify chain integrity
is_valid, error = journal.verify_chain()
```

### Node Identity

```python
from station_calyx.node import get_node_identity

node = get_node_identity()
print(f"Node: {node.node_id}")
print(f"Host: {node.hostname}")
```

### Sequence Manager

```python
from station_calyx.node import SequenceManager

seq_mgr = SequenceManager()
seq = seq_mgr.next()  # 1, 2, 3...
```

## Governance Constraints (v0)

### What This System Does

? Local evidence journaling (append-only)  
? Hash chaining for integrity  
? Batch export for transfer  
? Node identity & sequence persistence  
? Deterministic envelope creation  

### What This System Does NOT Do

? Network transmission (manual transfer only)  
? Evidence ingestion/receiver (separate component)  
? Execution actions based on evidence  
? Recommendations or analysis  
? Evidence modification or deletion  

## Verification Checklist

Run `verify_evidence_system.py` to check:

- [x] Node identity persists across restarts
- [x] Sequence strictly monotonic (1, 2, 3...)
- [x] Evidence journal is append-only JSONL
- [x] Hash chain is continuous (`prev_hash` linkage)
- [x] Export bundle contains only new envelopes
- [x] Export offset tracked safely

## Troubleshooting

**Q: Sequence not incrementing?**  
A: Check `outgoing/node/sequence.json` exists and is writable.

**Q: Export bundle empty?**  
A: All envelopes may be exported. Check `outgoing/node/export_index.json`.

**Q: Hash chain verification fails?**  
A: Journal may be corrupted. Check `logs/evidence/<node_id>/evidence.jsonl` for manual edits (not allowed).

**Q: Node ID changes between runs?**  
A: Check `outgoing/node/identity.json` persists. Regeneration only on deletion.

## Roadmap (Beyond v0)

- **Network Relay**: POST export bundles to receiver (gated by `network.ok`)
- **Compression**: GZIP export bundles for transfer efficiency
- **Encryption**: Envelope payload encryption at rest
- **Multi-Node Sync**: Import bundles from other nodes
- **Evidence Queries**: Local query interface for journal search

---

**[CBO • Governance]**: This system establishes the foundation for chronological continuity across all Station Calyx instances. Evidence captured here is truth — immutable, verifiable, and traceable.

*Station Calyx is the flag we fly; autonomy is the dream we share.*
