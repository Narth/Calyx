---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_BUDGET_ACCOUNTING_V1

**Status:** Implemented 2026-02-26
**Trigger:** Log one verified budget record per governed request at response.finalized

---

## Objective

Systematic accounting layer to quantify the cost of turning a governed human request into a verified response. Supports operator questions: "Which intents are expensive?", "Are we doing work without human ingress?", "How often do claims fail?", "Which entry points are producing cost?"

---

## Budget Record Schema (v1)

**Path:** `runtime/receipts/budget/governance_budget__YYYYMMDD.jsonl`

```json
{
  "schema": "gov.budget.v1",
  "ts_utc": "…",
  "corr_id": "…",
  "request_id": "…",
  "entry_point": "api | calyx-discord-gateway | browser | …",
  "node_id": "…",
  "auth_mode": "gateway | signature | none",
  "auth_verified": true,
  "signer_fingerprint": "gateway:<name> | key:<fingerprint>",
  "intent": "INTENT_*",
  "fastpath_used": true,
  "wall_time_ms": 1234,
  "tool_calls": [{"name": "repo_search", "count": 2}, …],
  "tool_calls_total": 3,
  "claims": {"attempted": 2, "verified": 2, "failed": 0},
  "receipts": {
    "canonical_receipt_written": true,
    "canonical_receipt_path": "…",
    "equivalence_hash_emitted": true
  },
  "hashes": {
    "response_sha256": "…",
    "equivalence_hash_sha256": "…",
    "receipt_hash_sha256": "…"
  }
}
```

---

## Integration

- **When:** At response.finalized (after governance + intent + tools + claims + CRH emission)
- **Where:** `_write_governance_budget()` called from every response path (heartbeat, failure event, compound, file location, confirmation, LLM)

---

## Ledger Event

`budget.request.recorded` — payload: corr_id, budget_receipt_path, intent, wall_time_ms, tool_calls_total, claim_failed_count

---

## Tripwires (V1, detection-only)

Emit `budget.violation` and append FE candidate if:

- tool_calls_total > 25
- wall_time_ms > 60000
- claims.failed > 0
- budget record could not be written

---

## Preflight

`runtime/receipts/budget/` created on sunrise. If creation fails → `station.preflight.failed`, exit non-zero.
