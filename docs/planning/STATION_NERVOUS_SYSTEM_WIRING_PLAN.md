---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Station Calyx Nervous System Wiring Plan

**Document:** Spinal Stack → Operational Integrity
**Date:** 2026-02-26
**Prepared by:** CBO
**Audience:** CGPT (validation and hardening)
**Status:** Planning — ready for review

---

## 1. Vision: Station Calyx as Spinal Stack

Station Calyx is the **spinal stack** of operational integrity. The Event Ledger is the **spinal cord** — the canonical, append-only, correlation-aware nerve that carries every significant signal from periphery to governance.

**Metaphor:**
- **Spine:** Event Ledger (runtime/ledger/station_events__YYYYMMDD.jsonl)
- **Nerves:** `emit()` calls at every decision point, gate, and action
- **Ganglia:** Components (CBO Core, Dev Harness, Router, Hub Runner, Gates)
- **Reflex arcs:** Governance chains (integrity → lease → contract → execution → receipt)

**Principle:** *Without the ledger, governance is a belief. With it, governance is observable.*

---

## 2. Current State: Gap Analysis

### 2.1 What Emits Today

| Component | Events | Trigger |
|-----------|--------|---------|
| CBO Core lifespan | `station.boot`, `station.boot.error` | Startup |
| CBO Core exception handler | `exception` | Unhandled exception |
| update_state_checks → emit_heartbeat_tick | `heartbeat.tick` | Heartbeat run |
| Mail router | `mail.ingest.accept`, `mail.ingest.reject`, `router.deliver.*` | Only when `/execute` or Discord delivers mail |
| Discord intake | `cbo.discord.inbound` | Only when Discord bot runs |
| Discord response | `cbo.discord.outbound` | Only when Discord bot runs |
| home_node_executor | `toolcall.requested`, `toolcall.allowed`, `toolcall.denied`, `toolcall.error` | Only when Discord CBO executes tools |
| toolsurface | `toolcall.denied` | Only when execution spine runs (patch_small, repo_readonly_review) |
| ledger_health_check | `ledger.stall` | When explicitly invoked |

### 2.2 What Does NOT Emit (Gaps)

**High-traffic paths (user-visible activity):**
- **CBO Core `/chat`** — No emit on request, completion, tool loop, or receipt
- **CBO Core `/state`** — No emit
- **CBO Core `/sponsorship`** — No emit
- **CBO Core `/execute`** — No emit on spine stages (deliver, ingest, mint, process)
- **Dev Harness** — No emit on `/repo/list`, `/repo/search`, `/repo/read`, `/repo/apply_patch`, `/exec/docker`
- **Avatar Web** — No emit on `/api/chat` proxy, whiteboard task add/run
- **Telemetry Gateway** — No emit on `/chat` proxy, `/health`

**Spine / pipeline (internal activity):**
- **Intent pipeline** — ingest, mark_ready, mint_work_envelope — no emit
- **Hub runner** — denied, executed, failed — no emit
- **Task handlers** — repo_readonly_review, patch_small, test_run_safe — no emit

**Gates (decision points):**
- **Integrity gate** — gate_before_action, spine_operation_lease — no emit on pass/fail
- **Ollama gate** — check, release, record_success, record_failure — no emit
- **Stamping / sponsorship** — check_sponsorship — no emit

**Scripts (periodic / one-shot):**
- **station_health_loop** — no emit (health.tick, health.fail, health.recovered)
- **navigator** — no emit (navigator.decision, navigator.pause)
- **patch_readiness** — no emit (patch_readiness.ready, patch_readiness.defer)
- **carbon_intensity** — no emit (carbon.fetch, carbon.fail)

**Calyx CBO (separate API):**
- **calyx/cbo/api** — /heartbeat, /objective, /status, /claim, /report — no emit
- **bridge_overseer** — Reflect → Plan → Act → Critique — no emit

---

## 3. Event Taxonomy (Nervous System Map)

Events are named with dot-notation: `component.event[.subevent]`. All events flow to the same ledger.

### 3.1 Station Layer (Boot / Lifecycle)

| Event | Level | When |
|-------|-------|------|
| `station.boot` | INFO | CBO Core started |
| `station.boot.partial` | WARN | Some services failed to start |
| `station.boot.error` | ERROR | Boot failed |
| `station.shutdown` | INFO | Graceful shutdown |

### 3.2 Heartbeat Layer

| Event | Level | When |
|-------|-------|------|
| `heartbeat.tick` | INFO/DEBUG | update_state_checks run |
| `heartbeat.anomaly` | WARN | Checks or health degraded |
| `heartbeat.stall` | ERROR | No tick within threshold |
| `heartbeat.recovered` | INFO | Stall resolved |

### 3.3 CBO Core Layer (HTTP Entry Points)

| Event | Level | When |
|-------|-------|------|
| `cbo.state.request` | DEBUG | GET /state |
| `cbo.sponsorship.request` | DEBUG | GET /sponsorship |
| `cbo.sponsorship.valid` | INFO | Sponsorship valid |
| `cbo.sponsorship.invalid` | WARN | Sponsorship invalid |
| `cbo.execute.request` | INFO | POST /execute |
| `cbo.execute.integrity_fail` | WARN | Integrity gate blocked |
| `cbo.execute.spine.success` | INFO | Spine completed |
| `cbo.execute.spine.fail` | ERROR | Spine failed (deliver/ingest/mint/process) |
| `cbo.chat.request` | INFO | POST /chat |
| `cbo.chat.integrity_fail` | WARN | Integrity gate blocked |
| `cbo.chat.complete` | INFO | Chat response sent |
| `cbo.chat.tool_loop` | DEBUG | Tool requests executed |
| `cbo.chat.ollama_denied` | WARN | Ollama gate denied local model |

### 3.4 Dev Harness Layer

| Event | Level | When |
|-------|-------|------|
| `dev_harness.repo_list` | INFO | POST /repo/list |
| `dev_harness.repo_search` | INFO | POST /repo/search |
| `dev_harness.repo_read` | INFO | POST /repo/read |
| `dev_harness.patch_apply` | INFO | POST /repo/apply_patch |
| `dev_harness.exec_docker` | WARN | POST /exec/docker (audit) |

### 3.5 Avatar Web Layer

| Event | Level | When |
|-------|-------|------|
| `avatar.chat_proxy` | INFO | POST /api/chat → CBO Core |
| `avatar.whiteboard.task_add` | INFO | POST /api/whiteboard/tasks |
| `avatar.whiteboard.task_run` | INFO | POST /api/whiteboard/tasks/{id}/run |

### 3.6 Telemetry Gateway Layer

| Event | Level | When |
|-------|-------|------|
| `telemetry.chat_proxy` | INFO | POST /chat → CBO Core |
| `telemetry.health_check` | DEBUG | GET /health |

### 3.7 Mail / Router Layer (Already Partially Wired)

| Event | Level | When |
|-------|-------|------|
| `mail.ingest.accept` | INFO | Envelope accepted |
| `mail.ingest.reject` | WARN | Reject (replay, integrity, lease) |
| `router.deliver.success` | INFO | Delivered to CBO ingest |
| `router.deliver.replay` | INFO | Replay detected |
| `router.deliver.atomic_write` | INFO | Atomic write complete |

### 3.8 Intent Pipeline Layer

| Event | Level | When |
|-------|-------|------|
| `intent.ingest.success` | INFO | Mail envelope ingested |
| `intent.ingest.fail` | ERROR | Ingest failed |
| `intent.mark_ready` | INFO | Intent marked ready |
| `work_envelope.minted` | INFO | Work envelope minted |
| `work_envelope.mint_fail` | ERROR | Mint failed |

### 3.9 Execution / Hub Runner Layer

| Event | Level | When |
|-------|-------|------|
| `hub_runner.denied` | WARN | Execution denied (lease, mint, contract, no_handler) |
| `hub_runner.executed` | INFO | Work envelope executed |
| `hub_runner.failed` | ERROR | Handler raised |
| `task.repo_readonly_review` | INFO | Handler started/completed |
| `task.patch_small` | INFO | Handler started/completed |
| `task.test_run_safe` | INFO | Handler started/completed |

### 3.10 Tool Execution Layer (Already Wired)

| Event | Level | When |
|-------|-------|------|
| `toolcall.requested` | INFO | Tool requested |
| `toolcall.allowed` | INFO | Tool allowed |
| `toolcall.denied` | WARN | Tool denied |
| `toolcall.error` | ERROR | Tool execution error |

### 3.11 Gate Layer

| Event | Level | When |
|-------|-------|------|
| `integrity.pass` | DEBUG | gate_before_action passed |
| `integrity.fail` | WARN | gate_before_action failed |
| `lease.acquired` | DEBUG | spine_operation_lease acquired |
| `lease.held` | WARN | Lease held by another |
| `ollama_gate.allow` | DEBUG | Local LLM allowed |
| `ollama_gate.deny` | WARN | Local LLM denied |
| `ollama_gate.slow` | WARN | Inflight exceeded threshold |
| `sponsorship.valid` | DEBUG | check_sponsorship valid |
| `sponsorship.invalid` | WARN | check_sponsorship invalid |

### 3.12 Destructive / Governance Layer

| Event | Level | When |
|-------|-------|------|
| `destructive.preflight` | INFO | Before irreversible op |
| `destructive.commit` | INFO | Irreversible op committed |
| `destructive.rollback` | WARN | Rollback after failure |

### 3.13 Scripts Layer (Periodic / One-Shot)

| Event | Level | When |
|-------|-------|------|
| `health.tick` | DEBUG | station_health_loop iteration |
| `health.fail` | WARN | Health threshold exceeded |
| `health.recovered` | INFO | Health recovered |
| `navigator.decision` | INFO | Navigator hot/pause/cool |
| `patch_readiness.ready` | INFO | Patch readiness pass |
| `patch_readiness.defer` | WARN | Patch readiness defer |
| `carbon.fetch` | INFO | Carbon intensity fetched |
| `carbon.fail` | WARN | Carbon fetch failed |

### 3.14 Calyx CBO API Layer (Optional — Separate Service)

| Event | Level | When |
|-------|-------|------|
| `cbo_api.objective.submit` | INFO | POST /objective |
| `cbo_api.task.claim` | INFO | POST /claim |
| `cbo_api.report` | DEBUG | GET /report |
| `bridge.pulse.start` | INFO | Bridge overseer cycle start |
| `bridge.pulse.complete` | INFO | Bridge overseer cycle complete |

---

## 4. Phased Wiring Plan

### Phase 1: High-Traffic Entry Points (Immediate Visibility)

**Goal:** Every user-visible HTTP request produces at least one ledger event.

| # | Component | Location | Events to Add |
|---|-----------|----------|---------------|
| 1.1 | CBO Core /chat | `cbo_hub/cbo_core/app.py` | `cbo.chat.request`, `cbo.chat.complete`, `cbo.chat.integrity_fail`, `cbo.chat.ollama_denied` |
| 1.2 | CBO Core /execute | `cbo_hub/cbo_core/app.py` | `cbo.execute.request`, `cbo.execute.spine.success`, `cbo.execute.spine.fail`, `cbo.execute.integrity_fail` |
| 1.3 | CBO Core /state, /sponsorship | `cbo_hub/cbo_core/app.py` | `cbo.state.request`, `cbo.sponsorship.request`, `cbo.sponsorship.valid`, `cbo.sponsorship.invalid` |
| 1.4 | Dev Harness | `cbo_hub/dev_harness/app.py` | `dev_harness.repo_list`, `dev_harness.repo_search`, `dev_harness.repo_read`, `dev_harness.patch_apply` |
| 1.5 | Avatar Web | `cbo_hub/avatar_web/app.py` | `avatar.chat_proxy`, `avatar.whiteboard.task_add`, `avatar.whiteboard.task_run` |
| 1.6 | Telemetry Gateway | `cbo_hub/telemetry_gateway/app.py` | `telemetry.chat_proxy`, `telemetry.health_check` |

### Phase 2: Spine Pipeline (End-to-End Traceability)

**Goal:** Mail → Intent → Work Envelope → Execution forms a correlated chain.

| # | Component | Location | Events to Add |
|---|-----------|----------|---------------|
| 2.1 | Intent pipeline ingest | `calyx/cbo/intent_pipeline/ingest.py` | `intent.ingest.success`, `intent.ingest.fail` |
| 2.2 | Intent pipeline mark_ready | `calyx/cbo/intent_pipeline/` | `intent.mark_ready` |
| 2.3 | Intent pipeline mint | `calyx/cbo/intent_pipeline/plan.py` | `work_envelope.minted`, `work_envelope.mint_fail` |
| 2.4 | Hub runner | `calyx/execution/hub_runner.py` | `hub_runner.denied`, `hub_runner.executed`, `hub_runner.failed` |
| 2.5 | Task handlers | `calyx/execution/task_handlers/*.py` | `task.{handler}.start`, `task.{handler}.complete` |

### Phase 3: Gates (Decision Audit Trail)

**Goal:** Every gate pass/fail is recorded.

| # | Component | Location | Events to Add |
|---|-----------|----------|---------------|
| 3.1 | Integrity gate | `calyx/kernel/integrity_gate.py` | `integrity.pass`, `integrity.fail`, `lease.acquired`, `lease.held` |
| 3.2 | Ollama gate | `calyx/kernel/ollama_gate.py` | `ollama_gate.allow`, `ollama_gate.deny`, `ollama_gate.slow` |
| 3.3 | Stamping | `cbo_hub/cbo_core/stamping.py` | `sponsorship.valid`, `sponsorship.invalid` |

### Phase 4: Scripts (Periodic Telemetry)

**Goal:** Scripts that run on heartbeat or schedule emit their outcomes.

| # | Component | Location | Events to Add |
|---|-----------|----------|---------------|
| 4.1 | station_health_loop | `Scripts/station_health_loop.ps1` | Invoke Python helper for `health.tick`, `health.fail`, `health.recovered` |
| 4.2 | navigator | `Scripts/navigator.ps1` | Invoke Python helper for `navigator.decision` |
| 4.3 | patch_readiness | `Scripts/patch_readiness.ps1` | Invoke Python helper for `patch_readiness.ready`, `patch_readiness.defer` |
| 4.4 | carbon_intensity | `Scripts/carbon_intensity.ps1` | Invoke Python helper for `carbon.fetch`, `carbon.fail` |

### Phase 5: Calyx CBO API & Bridge (Optional)

**Goal:** If calyx.cbo.api and bridge_overseer are in use, wire them.

| # | Component | Location | Events to Add |
|---|-----------|----------|---------------|
| 5.1 | calyx/cbo/api | `calyx/cbo/api.py` | `cbo_api.objective.submit`, `cbo_api.task.claim`, `cbo_api.report` |
| 5.2 | bridge_overseer | `calyx/cbo/bridge_overseer.py` | `bridge.pulse.start`, `bridge.pulse.complete` |

---

## 5. Governance Chains (Verifiable Action Flows)

Each chain is a sequence of events that can be correlated via `corr_id` or `envelope_id`.

### Chain 1: Chat Request

```
cbo.chat.request (corr_id=X)
  → [integrity.fail] OR
  → [ollama_gate.deny] OR
  → [cbo.chat.tool_loop] (toolcall.requested, toolcall.allowed, ...)
  → cbo.chat.complete (corr_id=X)
```

### Chain 2: Execute Spine

```
cbo.execute.request (envelope_id=E)
  → mail.ingest.accept (corr_id=E)
  → router.deliver.success (corr_id=E)
  → intent.ingest.success (intent_id=I)
  → intent.mark_ready (intent_id=I)
  → work_envelope.minted (intent_id=I)
  → hub_runner.executed OR hub_runner.denied
  → cbo.execute.spine.success (envelope_id=E)
```

### Chain 3: Execution Denial

```
hub_runner.denied (reason=R, envelope_id=E)
  → cbo.execute.spine.fail (envelope_id=E)
```

### Chain 4: Tool Execution (Discord / Home Node)

```
toolcall.requested (tool=T)
  → toolcall.denied OR toolcall.allowed
  → [toolcall.error] (if allowed but failed)
```

---

## 6. Implementation Constraints

1. **Never throw upstream** — All `emit()` calls must be wrapped in try/except; ledger failure falls back to stderr.
2. **Non-blocking** — Ledger writes must not block main execution.
3. **No circular imports** — `event_ledger` imports only from `paths`; components import `event_ledger` at call site.
4. **Small data** — `data` dict truncated (max 20 keys, 500 chars per value).
5. **Correlation** — Use `corr_id` = envelope_id, intent_id, or request-scoped uuid for chain tracing.
6. **PowerShell scripts** — Invoke `python Scripts/emit_ledger_event.py <event> <msg> [data_json]` for script-originated events.

---

## 7. CGPT Validation Criteria

### 7.1 Completeness

- [ ] Every HTTP entry point (CBO Core, Dev Harness, Avatar Web, Telemetry Gateway) emits on request and outcome.
- [ ] Every spine stage (deliver, ingest, mint, execute) emits.
- [ ] Every gate (integrity, ollama, sponsorship) emits on pass/fail.
- [ ] Scripts that run on heartbeat or schedule emit their outcomes.

### 7.2 Correctness

- [ ] No `emit()` call can raise to caller.
- [ ] `corr_id` is threaded through chains (envelope_id, intent_id, or request uuid).
- [ ] Event names follow taxonomy (component.event[.subevent]).

### 7.3 Observability

- [ ] `ledger_tail.py -n 50` shows activity from all wired components after typical usage.
- [ ] Denials and failures are visible (WARN/ERROR level).
- [ ] Governance chains can be reconstructed by filtering on `corr_id`.

### 7.4 Performance

- [ ] Ledger writes do not add measurable latency to hot paths.
- [ ] No new blocking I/O in request handlers.

---

## 8. Deliverables for CGPT

1. **This plan** — `docs/planning/STATION_NERVOUS_SYSTEM_WIRING_PLAN.md`
2. **Event taxonomy reference** — Section 3 above (can be extracted to standalone doc)
3. **Phased implementation checklist** — Section 4 with checkboxes
4. **Helper script** — `Scripts/emit_ledger_event.py` for PowerShell-invoked events (optional; emit_heartbeat_tick.py pattern)

---

## 9. Next Steps

1. **CGPT review** — Validate taxonomy, phases, and constraints.
2. **Phase 1 implementation** — Wire CBO Core, Dev Harness, Avatar Web, Telemetry Gateway.
3. **Verification** — Run typical flows (chat, execute, Avatar Web) and confirm ledger reflects activity.
4. **Phase 2–4** — Proceed in order; validate after each phase.

---

*The ledger is the spinal cord. Without it, governance is a belief. With it, governance is observable.*
