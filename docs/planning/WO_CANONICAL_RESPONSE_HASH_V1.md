---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_CANONICAL_RESPONSE_HASH_V1

**Status:** Implemented 2026-02-27
**Trigger:** Cross-channel and cross-node parity verification; auditability without thought leakage

---

## Objective

Add Canonical Response Hash receipts for mechanical parity checking. Answer: "Did Browser/Discord DM/Public channel produce the same canonical answer?" without exposing internal reasoning.

---

## Schema (crh.v1)

| Field | Description |
|-------|-------------|
| schema | "crh.v1" |
| ts_utc | ISO timestamp |
| corr_id | Request correlation ID |
| request_id | Same as corr_id |
| entry_point | browser \| discord_gateway \| api |
| node_id | CALYX_NODE_ID env or "unknown" |
| intent | INTENT_HEARTBEAT, etc. |
| normalized_request | User text (plaintext) |
| normalized_request_sha256 | SHA-256 of normalized request |
| evidence | [{kind, path, sha256}, ...] sorted by (kind, path) |
| policy_flags | governance_required, canonical_response_mode, fastpath_used, tooling_allowed |
| response_sha256 | SHA-256 of reply text |
| canonical_hash_sha256 | SHA-256 of canonical JSON of bundle |

---

## Evidence by Intent

| Intent | Evidence |
|--------|----------|
| HEARTBEAT | STATE.md sha256 |
| FAILURE_EVENT_QUERY | FAILURE_EVENT_LOG.md sha256 |
| FILE_LOCATION | Top repo hit file sha256 |
| COMPOUND | Search target top hit + definition target sha256 |
| CONFIRMATION | [] |
| FREE_CHAT | Top 3 allowed_paths (repo hits) sha256 |

---

## Implementation

| Component | Location |
|-----------|----------|
| canonical_json | calyx/kernel/canonical_json.py |
| canonical_hash | calyx/kernel/canonical_hash.py |
| canonical_bundle | calyx/kernel/canonical_bundle.py |
| Integration | cbo_hub/cbo_core/app.py — _emit_canonical_hash at each response finalization |
| Bundle receipts | runtime/receipts/canonical/canonical_bundle__{ts}_{corr_id}.json |
| Parity check | Scripts/canonical_parity_check.py |

---

## Ledger Event

```
event: response.canonical_hash
data: canonical_hash_sha256, normalized_request_sha256, intent, entry_point, fastpath_used, evidence_count, response_sha256
```

---

## Parity Check

```powershell
python Scripts/canonical_parity_check.py --since-minutes 60
python Scripts/canonical_parity_check.py --corr-id <id>
```

Exit: 0=all match, 1=mismatch, 2=insufficient data.

---

## Variance Diagnostics

When mismatch detected, script suggests:
- Different evidence_count → different evidence hashes (STATE drift, repo diff)
- Different response_sha256 → synthesis nondeterminism or different STATE
- Same response, different canonical_hash → evidence or policy flags differ
