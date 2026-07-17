---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Canonical Response Hash — Parity Verification

**WO:** WO_CANONICAL_RESPONSE_HASH_V1 + WO_CANONICAL_EQUIVALENCE_HASH_V2
**Purpose:** Mechanical verification that Browser, Discord DM, and Public channel produce the same canonical answer for the same request.

---

## Two Hash Types

| Hash | Purpose |
|------|---------|
| **Receipt hash** | Unique per event; chronological chain; auditability |
| **Equivalence hash** | Stable across entry points when intent, evidence, response match |

**Parity checks compare equivalence_hash only.** Never compare receipt hashes.

---

## What CRH Receipts Are

A **canonical bundle** (receipt) contains volatile + stable fields. The **equivalence bundle** (parity) contains only stable fields: schema, intent, normalized_request_sha256, evidence, policy_flags, response_sha256, node_id. Excludes ts_utc, corr_id, request_id, entry_point.

---

## Where Receipts Live

| Artifact | Location |
|----------|----------|
| Ledger events | `runtime/ledger/station_events__YYYYMMDD.jsonl` — event `response.canonical_hash` |
| Bundle files | `runtime/receipts/canonical/canonical_bundle__{ts}_{corr_id}.json` |

---

## How to Verify Parity

### 1. Run a 3-channel smoke test

Send the same prompt from:

- Browser (Avatar Web)
- Discord DM
- Public channel (if allowed)

Example prompts:

- *"Produce the latest Station heartbeat."* → intent HEARTBEAT, evidence STATE.md
- *"Confirm what a failure event looks like."* → intent FAILURE_EVENT_QUERY, evidence FAILURE_EVENT_LOG.md

### 2. Run the parity check script

```powershell
# By correlation ID (from ledger or logs)
python Scripts/canonical_parity_check.py --corr-id <corr_id>

# By time window (last 60 minutes)
python Scripts/canonical_parity_check.py --since-minutes 60
```

### 3. Interpret exit codes

| Code | Meaning |
|------|---------|
| 0 | Equivalence hashes match — parity OK |
| 1 | Equivalence hash mismatch — see variance diagnostics |
| 2 | Insufficient data (no response.equivalence_hash events) |

### 4. Variance diagnostics (when mismatch)

The script compares equivalence_hash only. If mismatch:

- **Different response_sha256** → synthesis nondeterminism or different STATE
- **Different evidence_count** → different evidence hashes (STATE drift, repo diff)
- **Different policy flag** → different mode (e.g. fastpath vs LLM)

Receipt hashes are allowed to differ (they include ts_utc, corr_id, entry_point).

---

## Cross-node parity

For desktop vs laptop:

1. Align repo and STATE.md (sync, same commit).
2. Run the same Test A and B on both nodes.
3. Run parity check with `--since-minutes` to capture both.
4. If mismatch: evidence hashes reveal which artifact differs.
