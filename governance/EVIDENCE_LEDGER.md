# EVIDENCE_LEDGER.md

## Evidence Ledger

> **Purpose:** Append-only, hash-chained, schema-validated ledger for governance evidence. Deny-by-default on malformed entries.

### Requirements

- **Append-only:** Records are never modified or deleted.
- **Hash-chained:** Each record includes `prev_hash` (link to previous) and `record_hash` (SHA256 of canonical JSON).
- **Schema validated:** Records must conform to schema_v1.json before append.
- **Deny-by-default:** Malformed YAML, missing required fields, or tampered chain → reject.
- **Deterministic canonical JSON:** `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` for hash computation.

### Ledger Path

`runtime/evidence_ledger/ledger.jsonl`

### Schema v1 (minimal)

Required fields for chaining + provenance:

- `ts_utc` — ISO8601 timestamp
- `event_name` — string
- `severity` — low | medium | high | critical
- `wo_id` or `context_tag` — work order or context identifier
- `payload_hash` or `payload_summary` — fingerprint of payload
- `prev_hash` — hash of previous record (null for first)
- `record_hash` — SHA256 of canonical JSON (all fields except record_hash)

### verify_chain()

Walks ledger records in order:

1. Validates schema for each record.
2. Recomputes `record_hash`.
3. Checks `prev_hash` linkage.
4. Fails on any mismatch, tamper, or parse error.
