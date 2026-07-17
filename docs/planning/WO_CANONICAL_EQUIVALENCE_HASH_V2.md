---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_CANONICAL_EQUIVALENCE_HASH_V2

**Status:** Implemented 2026-02-27
**Trigger:** Separate receipt hash from parity hash; make cross-channel parity meaningful

---

## Objective

Two hash types per response:
- **Receipt hash** — unique per event, chronological chain, auditability
- **Equivalence hash** — stable across entry points when intent, evidence, response match

---

## Hash Types

| Hash | Event | Purpose |
|------|-------|---------|
| Receipt | response.canonical_hash | Chronological chain, non-repudiation |
| Equivalence | response.equivalence_hash | Cross-channel parity |

---

## Equivalence Bundle (stable fields only)

Schema: crh.equiv.v1

| Field | Included |
|-------|----------|
| schema | crh.equiv.v1 |
| intent | Yes |
| normalized_request_sha256 | Yes |
| evidence | Yes (sorted by kind, path) |
| policy_flags | governance_required, canonical_response_mode, fastpath_used, tooling_allowed |
| response_sha256 | Yes |
| node_id | Yes |

**Excluded:** ts_utc, corr_id, request_id, entry_point

---

## Parity Checker

- Reads `response.equivalence_hash` events
- Compares `equivalence_hash_sha256` (never receipt_hash)
- Output: equivalence_hash, receipt_hash, intent, response_sha256, evidence_count
- Exit: 0 if equivalence matches, 1 if mismatch, 2 insufficient data

---

## Verified Claims

- claim.attempted(equivalence_hash) — computation-only
- claim.verified(equivalence_hash) — computation-only (no artifact)

---

## Validation Protocol

1. 3-channel heartbeat: equivalence_hash identical, receipt_hash can differ
2. Failure Event query: same
3. File location query: same

---

## Non-Negotiable Rule

Parity checks must never compare receipt hashes. Receipt hashes prove "this exact event happened." Equivalence hashes prove "these events produced the same canonical result."
