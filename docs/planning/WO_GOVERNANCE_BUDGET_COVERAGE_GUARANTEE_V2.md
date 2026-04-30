---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GOVERNANCE_BUDGET_COVERAGE_GUARANTEE_V2

**Status:** Implemented 2026-02-26
**Trigger:** Prove and enforce complete budget coverage across all governed request paths

---

## Objective

For every governed human request that reaches response.finalized: exactly one budget record. No exceptions. No silent paths.

---

## Coverage Invariant

For any corr_id where:
- human.request.received
- AND response.finalized

There must exist:
- exactly one budget.request.recorded
- exactly one matching JSONL line in runtime/receipts/budget/

Violation = governance failure.

---

## Deliverables

### 1. Coverage Matrix Test Ladder

`Scripts/governance_budget_coverage_ladder.py` — runs deterministic tests for each response path:

| Case | Intent Path | Expected Tools | Notes |
|------|-------------|----------------|-------|
| A | HEARTBEAT | none | fastpath |
| B | FAILURE_EVENT_QUERY | none | deterministic fastpath |
| C | FILE_LOCATION | repo_search | deterministic |
| D | COMPOUND_QUERY | repo_search x2 | compound |
| E | CONFIRMATION | none | minimal |
| F | FREE_CHAT / STATE_QUERY | model + tools | LLM path |

Cases G–H (governance rejection, signature replay) run separately — must NOT produce budget.

### 2. Invariant Verification Script

`Scripts/governance_budget_coverage_check.py`

- `--since-minutes N` — time window (default 60)
- `--corr-ids-file PATH` — only check these corr_ids (from ladder)

Exit: 0=full coverage, 1=violation, 2=insufficient data, 3=script error.

### 3. Self-Enforcing Assertion

When budget record cannot be written:
- Emit `governance.assertion.failed` (claim_type=budget_missing)
- Append FE candidate
- `write_budget_record` returns None; `_write_governance_budget` returns False

### 4. Confirmation Path Fix

INTENT_CONFIRMATION path now emits `response.finalized` (was missing).

---

## Validation

```bash
python Scripts/governance_budget_coverage_ladder.py
python Scripts/governance_budget_coverage_check.py --corr-ids-file runtime/receipts/budget/last_ladder_corr_ids.txt --since-minutes 10
```

Expect: exit 0, "Coverage OK: 6/6"
