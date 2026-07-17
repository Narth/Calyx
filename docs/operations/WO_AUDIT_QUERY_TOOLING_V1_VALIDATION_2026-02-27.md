---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_AUDIT_QUERY_TOOLING_V1 — Validation Report

**Date:** 2026-02-27
**Status:** Implementation complete

---

## Deliverables

| Script | Purpose |
|--------|---------|
| `Scripts/audit_trace.py` | Trace by `--corr-id` or `--task-corr-id` |
| `Scripts/audit_anomalies.py` | Find audit anomalies with context window |
| `Scripts/audit_health.py` | Coverage quick checks |

---

## Usage

```bash
# Human request trace
python Scripts/audit_trace.py --corr-id <id>
python Scripts/audit_trace.py --corr-id <id> --json

# Task trace
python Scripts/audit_trace.py --task-corr-id <id>

# Anomalies (audit.context.*, budget.violation, governance.assertion.failed)
python Scripts/audit_anomalies.py --since-minutes 60
python Scripts/audit_anomalies.py --since-minutes 60 --context 10

# Health coverage
python Scripts/audit_health.py --since-minutes 60
```

---

## Validation Protocol

1. **Human trace:** Run governed heartbeat request, capture `corr_id` from ledger tail. `audit_trace.py --corr-id <corr>` must return full chain from ingress → finalized.

2. **Task trace:** Let one scheduled heartbeat push run, capture `task_corr_id`. `audit_trace.py --task-corr-id <task>` must show `system.task.triggered` → `system.task.completed` + `budget.task.recorded`.

3. **Anomalies:** Intentionally trigger Test D (emit with missing context). `audit_anomalies.py --since-minutes 10` must show it with context window.

---

## Constraints Met

- Works offline from `runtime/ledger/*.jsonl`
- No external services
- Handles truncated/rotated ledgers (scans multiple `station_events__YYYYMMDD.jsonl` files)
- Fast for "last 60 minutes" usage
