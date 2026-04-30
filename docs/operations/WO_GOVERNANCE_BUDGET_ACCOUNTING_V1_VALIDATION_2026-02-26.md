---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_BUDGET_ACCOUNTING_V1 — Validation Report

**Date:** 2026-02-26
**Status:** PASS

---

## Test A — Heartbeat (fast path)

**Action:** Send HEARTBEAT request via gateway.

**Result:** HTTP 200

**Ledger:** `budget.request.recorded` with intent=INTENT_HEARTBEAT, wall_time_ms=18, tool_calls_total=0, claim_failed_count=0

**Budget record:**
- fastpath_used=true
- tool_calls_total=0
- wall_time_ms=18
- claims.failed=0
- auth_mode=gateway, signer_fingerprint=gateway:calyx-discord-gateway

---

## Test B — File location (repo_search)

**Action:** "Which file defines the emit function?" with allow_tools=true.

**Result:** HTTP 200, reply includes file path

**Budget record:**
- tool_calls_total=1
- tool_calls: [{"name": "repo_search", "count": 1}]
- intent=INTENT_FILE_LOCATION
- canonical_receipt_path present
- hashes populated

---

## Test C — Failure Event query

**Action:** "What is the failure event log format?"

**Result:** HTTP 200

**Budget record:**
- intent=INTENT_FAILURE_EVENT_QUERY
- evidence/receipt hashes present
- governance metadata (auth_mode, signer_fingerprint)

---

## Ledger tail

```bash
python Scripts/ledger_tail.py -n 50
```

Shows `budget.request.recorded` for each of the 3 corr_ids.

---

## JSONL file

`runtime/receipts/budget/governance_budget__20260226.jsonl` — 3 lines (one per request).

---

## Preflight

Sunrise preflight includes `runtime/receipts/budget/`. If directory cannot be created, `station.preflight.failed` emitted and process exits non-zero. Verified via preflight logic; budget dir is in required list.

---

## Overhead

Budget record computation and write is O(1) — single JSON serialize + append. No ledger query. Negligible overhead (<1ms typical).
