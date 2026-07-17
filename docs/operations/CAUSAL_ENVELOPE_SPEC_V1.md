---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Causal Envelope Spec (WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1)

**Objective:** Every ledger event is unambiguously traceable to a human request, a system task, or an internal Station lifecycle phase.

---

## Contract

Every ledger event emitted by Station Calyx must include exactly one causal identity via the `causal_envelope` field.

### A) Human context (request)

| Field | Required | Description |
|-------|----------|-------------|
| `causal_kind` | yes | `"human"` |
| `corr_id` | yes | Request correlation ID |
| `request_id` | optional | Same as corr_id if not distinguished |
| `auth_mode` | yes | `gateway` \| `signature` |
| `auth_verified` | yes | bool |
| `signer_fingerprint` | optional | Receipt-level; may be redacted |

### B) Task context (scheduler/system)

| Field | Required | Description |
|-------|----------|-------------|
| `causal_kind` | yes | `"task"` |
| `task_corr_id` | yes | Unique per run |
| `task_name` | yes | e.g., `heartbeat_push` |
| `schedule_id` | yes | Stable identifier |
| `trigger_reason` | yes | `interval` \| `startup` \| `manual_admin` |

### C) System context (preflight/boot/runtime)

| Field | Required | Description |
|-------|----------|-------------|
| `causal_kind` | yes | `"system"` |
| `system_phase` | yes | `preflight` \| `boot` \| `runtime` |

`runtime` is reserved for internally generated, non-human, non-task, non-tool, non-outbound lifecycle telemetry from explicitly whitelisted Station emitters.

No tools or outbound sends allowed in this context.

### D) Missing (audit failure)

| Field | Description |
|-------|-------------|
| `causal_kind` | `"missing"` |

Emitted when no causal context is set. Triggers `audit.context.missing`.

---

## Ledger Line Schema (minimum common fields)

Every event line carries:

- `schema` — ledger line schema version (e.g., `ledger.v1`)
- `ts` / `ts_utc` — ISO timestamp (UTC)
- `level` — DEBUG, INFO, WARN, ERROR, CRITICAL
- `component` — emitter (cbo, calyx_gateway, kernel, etc.)
- `event` — event name
- `msg` — message
- `causal_envelope` — one of A, B, C, or D above

---

## Audit Signals (observe-only)

| Event | When |
|-------|------|
| `audit.context.missing` | Emit attempted without causal context |
| `audit.context.ambiguous` | Both corr_id and task_corr_id set |
| `audit.context.invalid_system_action` | Tool/outbound during system phase |

---

## Context Management

- **Human:** `set_corr_id()` (middleware), `set_human_auth_context()` (after governance check), `clear_human_auth_context()` (request end)
- **Task:** `set_task_context()` at `system.task.triggered`, `clear_task_context()` at completion/failure
- **System:** `set_system_phase("preflight"|"boot"|"runtime")`, `clear_system_phase()` when done
