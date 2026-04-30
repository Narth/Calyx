# COMPETITOR_CLAUSE.md

## Competitor Clause

> **Purpose:** Prevent covert operational drift while enabling controlled relaxation under verified conditions.

### Policy

- **Expiry:** All clauses expire 90 days after creation (unless extended via `relaxation_applied=true` receipt).
- **Max Relaxation Cap:** No policy relaxation exceeds 30% of original constraints.
- **Receipt Requirement:** Any relaxation requires explicit `relaxation_applied=true` in the evidence receipt.

### Validator

```yaml
competitor_clause:
  expiry: "2026-03-01"
  max_relaxation_cap: 30
  relaxation_applied: false
```
