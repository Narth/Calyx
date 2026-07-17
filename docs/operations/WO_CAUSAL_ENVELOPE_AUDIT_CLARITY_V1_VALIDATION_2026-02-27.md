---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1 — Validation Report

**Date:** 2026-02-27
**Status:** Implementation complete; validation pending

---

## Implementation Summary

| Component | Status |
|-----------|--------|
| `with_causal_envelope()` central helper | ✅ |
| Task contextvars (set/clear at system.task.*) | ✅ |
| Human auth context (set after governance, clear at request end) | ✅ |
| System phase (preflight, boot) | ✅ |
| Ledger schema (schema, ts_utc, causal_envelope on every line) | ✅ |
| Audit signals (missing, ambiguous, invalid_system_action) | ✅ |

---

## Example Ledger Excerpts

### Human request lifecycle (all lines show causal_envelope)

```json
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"auth_mode": "gateway", "auth_verified": true, "causal_kind": "human", "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "signer_fingerprint": "gateway:calyx-discord"}, "data": {"path": "/chat", "method": "POST"}, "event": "station.smoke", "level": "DEBUG", "msg": "Request POST /chat", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:00:00.000000Z", "ts_utc": "2026-02-27T12:00:00.000000Z"}
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"auth_mode": "gateway", "auth_verified": true, "causal_kind": "human", "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "signer_fingerprint": "gateway:calyx-discord"}, "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "data": {"entry_point": "discord", "session_id": "discord_123"}, "event": "human.request.received", "level": "INFO", "msg": "Human ingress", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:00:01.000000Z", "ts_utc": "2026-02-27T12:00:01.000000Z"}
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"auth_mode": "gateway", "auth_verified": true, "causal_kind": "human", "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "signer_fingerprint": "gateway:calyx-discord"}, "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "data": {"intent": "INTENT_HEARTBEAT"}, "event": "intent.classified", "level": "INFO", "msg": "Intent classified", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:00:02.000000Z", "ts_utc": "2026-02-27T12:00:02.000000Z"}
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"auth_mode": "gateway", "auth_verified": true, "causal_kind": "human", "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "signer_fingerprint": "gateway:calyx-discord"}, "corr_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "data": {"intent": "INTENT_HEARTBEAT"}, "event": "response.finalized", "level": "INFO", "msg": "Response sent (heartbeat fast path)", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:00:03.000000Z", "ts_utc": "2026-02-27T12:00:03.000000Z"}
```

### Task lifecycle (heartbeat push)

```json
{"artifact_refs": [], "component": "calyx_gateway", "causal_envelope": {"causal_kind": "task", "schedule_id": "hb_push_30m", "task_corr_id": "t1t2t3t4-t5t6-7890-task-heartbeat1234", "task_name": "heartbeat_push", "trigger_reason": "interval"}, "data": {"schedule_id": "hb_push_30m", "task_corr_id": "t1t2t3t4-t5t6-7890-task-heartbeat1234", "task_name": "heartbeat_push", "trigger_reason": "interval"}, "event": "system.task.triggered", "level": "INFO", "msg": "System task heartbeat_push started", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:30:00.000000Z", "ts_utc": "2026-02-27T12:30:00.000000Z"}
{"artifact_refs": [], "component": "calyx_gateway", "causal_envelope": {"causal_kind": "task", "schedule_id": "hb_push_30m", "task_corr_id": "t1t2t3t4-t5t6-7890-task-heartbeat1234", "task_name": "heartbeat_push", "trigger_reason": "interval"}, "data": {"task_corr_id": "t1t2t3t4-t5t6-7890-task-heartbeat1234", "task_name": "heartbeat_push"}, "event": "system.task.completed", "level": "INFO", "msg": "System task heartbeat_push completed", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:30:01.000000Z", "ts_utc": "2026-02-27T12:30:01.000000Z"}
```

### System phase (preflight/boot)

```json
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"causal_kind": "system", "system_phase": "preflight"}, "data": {"CALYX_HEARTBEAT_PUSH_DESTINATION": "DM", "CALYX_HEARTBEAT_PUSH_ENABLED": true, "CALYX_HEARTBEAT_PUSH_INTERVAL_MIN": "30"}, "event": "station.config.effective", "level": "INFO", "msg": "Effective config (WO_IDLE_ACTIVITY_GOVERNANCE_V3)", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T11:59:59.000000Z", "ts_utc": "2026-02-27T11:59:59.000000Z"}
{"artifact_refs": [], "component": "cbo", "causal_envelope": {"causal_kind": "system", "system_phase": "boot"}, "data": {}, "event": "station.boot", "level": "INFO", "msg": "CBO Core started successfully", "policy": null, "run_id": null, "schema": "ledger.v1", "ts": "2026-02-27T12:00:00.000000Z", "ts_utc": "2026-02-27T12:00:00.000000Z"}
```

---

## Validation Protocol

### Test A — Human request trace completeness

Send one governed heartbeat request. Verify every event between `human.request.received` and `response.finalized` contains `causal_kind="human"` and same `corr_id`.

### Test B — Task trace completeness

With heartbeat push enabled, observe one scheduled push. Verify every event between `system.task.triggered` and `system.task.completed` contains `causal_kind="task"` and same `task_corr_id`, `task_name`, `schedule_id`.

### Test C — No mixed context

Simulate a task that triggers a human request handler or vice versa (dev-only). Expected: `audit.context.ambiguous` emitted.

### Test D — Context missing detection

Simulate emitting a ledger line with no context set. Expected: `audit.context.missing` emitted.

### Test E — System phase guardrail

During preflight/boot phase, attempt a tool call or outbound send (dev-only). Expected: `audit.context.invalid_system_action`.
