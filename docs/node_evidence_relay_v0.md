# Node Evidence Relay v0 Specification

**Version:** v0 (Pre-Alpha)  
**Status:** Contract Definition Only  
**Date:** 2026-01-07

---

## Purpose

Node Evidence Relay enables Station Calyx nodes to exchange append-only evidence envelopes with cryptographic provenance. This is **evidence transport only**:

- ? Share telemetry observations
- ? Verify data integrity
- ? Detect tampering or replay
- ? No remote commands
- ? No task execution
- ? No remote control
- ? No recommendations

---

## Constraints (Non-Negotiable)

| Constraint | Description |
|------------|-------------|
| **Advisory-only** | No execution authority on any node |
| **Deterministic logic** | Same input always produces same output |
| **Append-only storage** | Evidence is never modified or deleted |
| **No LLM usage** | This layer uses deterministic algorithms only |
| **No implied control** | Receiving evidence does not grant control |
| **Verify before ingest** | Receiver must validate envelope integrity |

---

## Evidence Envelope Schema (v1)

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `envelope_version` | `string` | Schema version identifier. Always `"v1"` for this spec. |
| `node_id` | `string` | Unique identifier for the originating node (UUID recommended). |
| `captured_at_iso` | `string` | ISO8601 timestamp of capture (with timezone). |
| `seq` | `integer` | Monotonically increasing sequence number per node. Starts at 0. |
| `event_type` | `string` | Type of event (e.g., `SYSTEM_SNAPSHOT`, `SCHEDULED_SNAPSHOT`). |
| `payload` | `object` | The actual event data (existing event structure). |
| `payload_hash` | `string` | SHA256 hash of canonical JSON payload. |
| `collector_version` | `string` | Version of collecting software (e.g., `"v1.6.0"` or git SHA). |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `node_name` | `string \| null` | Human-readable node name (e.g., `"Laptop-Observer"`). |
| `prev_hash` | `string \| null` | SHA256 hash of previous envelope. `null` for first envelope. |
| `signature` | `string \| null` | Cryptographic signature. `null` in v0; reserved for v1. |

### Example Envelope

```json
{
  "envelope_version": "v1",
  "node_id": "550e8400-e29b-41d4-a716-446655440000",
  "node_name": "Laptop-Observer",
  "captured_at_iso": "2026-01-07T16:30:00+00:00",
  "seq": 42,
  "event_type": "SYSTEM_SNAPSHOT",
  "payload": {
    "cpu_percent": 25.5,
    "memory": {"percent": 42.0, "used_gb": 6.8},
    "disk": {"percent_used": 88.6, "free_gb": 45.2}
  },
  "payload_hash": "a1b2c3d4e5f6...",
  "prev_hash": "9f8e7d6c5b4a...",
  "signature": null,
  "collector_version": "v1.6.0"
}
```

---

## Canonical JSON Serialization

To ensure deterministic hashing, all JSON serialization must be **canonical**:

1. **Keys sorted alphabetically** (recursive, at all nesting levels)
2. **No whitespace** between elements (compact form)
3. **ASCII-safe encoding** (non-ASCII characters escaped)
4. **Consistent number representation** (no trailing zeros)

### Python Implementation

```python
import json

def canonical_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
```

### Hash Computation

```python
import hashlib

def compute_payload_hash(payload: dict) -> str:
    canonical = canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

---

## Append-Only Guarantees

### Local Journal

Each node maintains a local evidence journal:

```
logs/evidence/<node_id>/evidence.jsonl
```

- **Format:** JSON Lines (one envelope per line)
- **Append-only:** New envelopes are appended; existing lines are never modified
- **Hash chain:** Each envelope's `prev_hash` links to the previous envelope

### Chain Integrity

```
Envelope 0: prev_hash = null
Envelope 1: prev_hash = hash(Envelope 0)
Envelope 2: prev_hash = hash(Envelope 1)
...
```

If any envelope is modified, all subsequent `prev_hash` values become invalid.

---

## Sequence Number Guarantees

| Property | Guarantee |
|----------|-----------|
| **Monotonic** | `seq` always increases: `seq[n+1] > seq[n]` |
| **Per-node** | Each node maintains its own sequence |
| **Persistent** | Survives process restarts |
| **Gapless** | Ideally no gaps, but gaps are allowed (replay detection) |

### Replay Detection

If a receiver sees:
- `seq` that is **less than or equal** to last seen `seq` for that `node_id`
- The envelope is a **replay** or **out-of-order** delivery

Action: Log warning, do not ingest duplicate.

---

## Threat Model Notes

### What This Protects Against

| Threat | Mitigation |
|--------|------------|
| **Payload tampering** | `payload_hash` verification fails |
| **Envelope tampering** | `prev_hash` chain breaks |
| **Replay attacks** | Duplicate `seq` detected |
| **Out-of-order delivery** | `seq` gap detection |
| **Node impersonation** | (v1) Signature verification |

### What This Does NOT Protect Against (v0)

| Threat | Status |
|--------|--------|
| **Node key compromise** | No signing in v0 |
| **Man-in-the-middle** | Requires transport encryption (TLS) |
| **Denial of service** | Out of scope for evidence layer |
| **Malicious payload content** | Payload is opaque; validation is receiver's responsibility |

### v1 Improvements (Planned)

- Ed25519 signature in `signature` field
- Node identity certificate exchange
- Signature verification before ingestion

---

## Validation Requirements

### Receiver Must Verify

Before ingesting any envelope, the receiver **must**:

1. ? Check `envelope_version` is supported
2. ? Verify all required fields are present
3. ? Recompute `payload_hash` and compare
4. ? Check `seq` is greater than last seen for `node_id`
5. ? (If not first) Verify `prev_hash` matches expected
6. ? (v1) Verify `signature` if present

### Validation Failure Actions

| Failure | Action |
|---------|--------|
| Hash mismatch | Reject envelope, log error |
| Seq replay | Reject envelope, log warning |
| Missing fields | Reject envelope, log error |
| Unsupported version | Reject envelope, log error |

---

## File Formats

### Evidence Journal (`.jsonl`)

```
{"envelope_version":"v1","node_id":"...","seq":0,...}
{"envelope_version":"v1","node_id":"...","seq":1,...}
{"envelope_version":"v1","node_id":"...","seq":2,...}
```

### Export Bundle (`.jsonl`)

Same format as journal. Contains contiguous range of envelopes for transfer.

```
exports/evidence_bundle_<node_id>_<timestamp>.jsonl
```

---

## API Summary (Planned)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/relay/ingest` | POST | Receive evidence batch from peer |
| `/v1/relay/status` | GET | Report relay status and last seq |

*Note: Network endpoints are not implemented in v0.*

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v0 | 2026-01-07 | Initial contract definition |

---

## References

- [JSON Lines format](https://jsonlines.org/)
- [ISO 8601 timestamps](https://en.wikipedia.org/wiki/ISO_8601)
- [SHA-256](https://en.wikipedia.org/wiki/SHA-2)
- [Canonical JSON](https://wiki.laptop.org/go/Canonical_JSON)
