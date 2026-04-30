---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# gov.budget.task.v1 — Task Budget Schema

**WO_IDLE_ACTIVITY_GOVERNANCE_V3**

---

## Purpose

Every non-human (system) action must produce a budget record. This schema defines the JSONL record format for system tasks (e.g., heartbeat push).

---

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | `"gov.budget.task.v1"` |
| `ts_utc` | string | ISO timestamp (UTC) |
| `task_corr_id` | string | Unique per run; do NOT reuse human corr_id |
| `task_name` | string | e.g., `heartbeat_push` |
| `schedule_id` | string | Stable identifier, e.g., `hb_push_30m` |
| `node_id` | string | Station node (e.g., `gateway`) |
| `entry_point` | string | `scheduler`, `startup`, `manual_admin` |
| `wall_time_ms` | int | Wall-clock duration |
| `tool_calls` | array | `[{"name":"…","count":0}]` |
| `tool_calls_total` | int | Total tool invocations |
| `claims` | object | `{attempted, verified, failed}` |
| `outbound` | object | `{kind, destination, message_type}` |
| `receipts` | object | `{canonical_receipt_written}` |

---

## Example

```json
{
  "schema": "gov.budget.task.v1",
  "ts_utc": "2026-02-27T12:00:00Z",
  "task_corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_name": "heartbeat_push",
  "schedule_id": "hb_push_30m",
  "node_id": "gateway",
  "entry_point": "scheduler",
  "wall_time_ms": 123,
  "tool_calls": [],
  "tool_calls_total": 0,
  "claims": {"attempted": 0, "verified": 0, "failed": 0},
  "outbound": {
    "kind": "discord_dm",
    "destination": "redacted_or_id",
    "message_type": "heartbeat"
  },
  "receipts": {"canonical_receipt_written": false}
}
```

---

## File Path

`runtime/receipts/budget/task_budget__YYYYMMDD.jsonl`
