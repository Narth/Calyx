---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_BUDGET_COVERAGE_GUARANTEE_V2 — Validation Report

**Date:** 2026-02-26
**Status:** PASS

---

## Coverage Matrix (Cases A–F)

| Case | Intent | finalized | budget_evt | JSONL | tools | claims_fail | PASS/FAIL |
|------|--------|-----------|------------|-------|-------|-------------|-----------|
| A | INTENT_HEARTBEAT | yes | yes | yes | 0 | 0 | PASS |
| B | INTENT_FAILURE_EVENT_QUERY | yes | yes | yes | 0 | 0 | PASS |
| C | INTENT_FILE_LOCATION | yes | yes | yes | 1 | 0 | PASS |
| D | INTENT_FILE_LOCATION (compound) | yes | yes | yes | 1 | 0 | PASS |
| E | INTENT_CONFIRMATION | yes | yes | yes | 0 | 0 | PASS |
| F | INTENT_STATE_QUERY | yes | yes | yes | 1 | 0 | PASS |

---

## Coverage Check Script

```bash
python Scripts/governance_budget_coverage_ladder.py
python Scripts/governance_budget_coverage_check.py --corr-ids-file runtime/receipts/budget/last_ladder_corr_ids.txt --since-minutes 10
```

**Result:** exit 0, "Coverage OK: 6/6 governed requests have exactly one budget record"

---

## Self-Enforcing Assertion

- `governance.assertion.failed` (budget_missing) emitted when budget write fails
- FE candidate appended on budget_write failure
- Confirmation path now emits `response.finalized` (was missing)

---

## Cases G–H (Not Producing Budget)

- **G (governance rejection):** With CALYX_GOVERNANCE_REQUIRED=true, direct /chat without gateway/signature → HTTP 403 before intent. No response.finalized, no budget.
- **H (signature replay):** Re-send same signed request → HTTP 403 (governance.signature_replay_detected). No response.finalized, no budget.

---

## Latency

No meaningful increase — budget write is O(1) append. Same as V1.
