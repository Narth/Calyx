---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# CRH Parity Variance — Why canonical_hash Differs

**Date:** 2026-02-27
**To:** Architect
**From:** CBO
**Status:** Operational; receipts verified per request (claim.verified + artifact_path exists)

---

## Summary

Canonical receipts are generated in realtime (Discord + Browser). Verified Claims lifecycle is present. `canonical_parity_check` reports VARIANCE DETECTED even when intent, `response_sha256`, and `evidence_count` match across entry points. **Root cause:** volatile fields (`ts_utc`, `corr_id`, `request_id`, `entry_point`) are included in the bundle that is hashed to produce `canonical_hash_sha256`. Each request gets a unique timestamp and correlation ID; each entry point has a different `entry_point` value. Therefore the receipt hash differs per request even when content is equivalent.

---

## Fields Included in canonical_hash_sha256

The bundle (`calyx/kernel/canonical_bundle.py`) is serialized with `canonical_dumps()` and then SHA-256 hashed. All fields below are included:

| Field | Volatile? | Notes |
|-------|-----------|-------|
| schema | No | "crh.v1" |
| ts_utc | **Yes** | Per-request timestamp |
| corr_id | **Yes** | Per-request correlation ID |
| request_id | **Yes** | Same as corr_id |
| entry_point | **Yes** | browser \| discord_gateway \| api |
| node_id | No | Same node |
| intent | No | Stable for same request |
| normalized_request | No | Stable |
| normalized_request_sha256 | No | Stable |
| evidence | No | Stable (sorted by kind, path) |
| policy_flags | No | Stable for same path |
| response_sha256 | No | Stable when response identical |

**Volatile fields causing variance:** `ts_utc`, `corr_id`, `request_id`, `entry_point`.

---

## Recommended Separation

| Hash Type | Purpose | Fields Included |
|-----------|---------|-----------------|
| **Receipt hash** (current `canonical_hash_sha256`) | Unique per receipt; audit trail; tamper detection | All fields (including volatile) |
| **Equivalence hash** (next WO) | Cross-channel parity; "same answer?" | Stable only: schema, intent, normalized_request_sha256, evidence, policy_flags, response_sha256, node_id |

**Recommendation:** Keep receipt hash as-is for auditability. Add `equivalence_hash_sha256` = `sha256(canonical_json(stable_subset))` for parity comparison. Parity script compares equivalence hashes; receipt hashes remain for per-receipt verification.

---

## Validation Confirmation

| Check | Result |
|-------|--------|
| response_sha256 matches across entry points | ✓ (when same request) |
| evidence sha256 for STATE.md matches | ✓ |
| Receipt canonical_hash can differ | ✓ (expected; volatile fields) |
| claim.verified + artifact_path exists per request | ✓ |
| System operational | ✓ |

---

## Parity Checker Update

`Scripts/canonical_parity_check.py` now:

- Prints culprit hint when `response_sha256` and `evidence_count` match but `canonical_hash` differs: "VOLATILE bundle fields — expected; use equivalence_hash (next WO)"
- Prints bundle field reference (stable vs volatile) on variance
