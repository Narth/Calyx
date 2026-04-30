---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_IDLE_ACTIVITY_GOVERNANCE_V3 — Validation Report

**Date:** 2026-02-27
**Status:** Implementation complete; validation pending

---

## Implementation Summary

| Component | Status |
|-----------|--------|
| System task events (`system.task.triggered`, `.completed`, `.failed`) | ✅ |
| Task budget schema (`gov.budget.task.v1`) | ✅ |
| Task budget write + `budget.task.recorded` | ✅ |
| No silent outbound (orphan detection) | ✅ |
| Idle compute protection (ungoverned tool execution) | ✅ |
| Operator controls (`CALYX_HEARTBEAT_PUSH_*`) | ✅ |
| Preflight (task budget dir writable, `station.config.effective`) | ✅ |

---

## Validation Protocol

### Test A — Baseline: push enabled

- Set `CALYX_HEARTBEAT_PUSH_ENABLED=true`, `CALYX_HEARTBEAT_PUSH_INTERVAL_MIN=1`
- Sunrise gateway
- Observe 2–3 pushes
- **Expected:** `system.task.triggered`, outbound with `task_corr_id`, `budget.task.recorded`, `tool_calls_total=0`

### Test B — Push disabled

- Set `CALYX_HEARTBEAT_PUSH_ENABLED=false`
- Sunrise / restart gateway
- Observe no outbound heartbeats for >2 intervals
- **Expected:** No `system.task.triggered`, no `budget.task.recorded`, no heartbeat events

### Test C — Orphan outbound detection

- Simulate (dev-only) outbound send without `corr_id`/`task_corr_id`
- **Expected:** `budget.violation` (orphan_outbound_action), `governance.assertion.failed`, FE candidate

### Test D — Ungoverned tool execution detection

- Simulate (dev-only) tool call without `corr_id`/`task_corr_id`
- **Expected:** `budget.violation` (ungoverned_compute), `governance.assertion.failed`, FE candidate

---

## Config Reference

| Env Var | Default | Description |
|---------|---------|-------------|
| `CALYX_HEARTBEAT_PUSH_ENABLED` | true | Enable/disable periodic heartbeat push |
| `CALYX_HEARTBEAT_PUSH_INTERVAL_MIN` | 30 (or DISCORD_HEARTBEAT_INTERVAL_MIN) | Interval in minutes |
| `CALYX_HEARTBEAT_PUSH_DESTINATION` | DM | DM, CHANNEL, or OFF |
