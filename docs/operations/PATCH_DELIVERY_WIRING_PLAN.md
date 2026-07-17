---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Patch Delivery Wiring Plan — Items 2–5

**Purpose:** Wiring plan for minimal sunrise, standalone repair, deferred patch queue, and single-service restart. Retains Station Calyx and BloomOS expectations. Supports autonomous operation when human is away.

**Prerequisite:** Patch readiness gate (`Scripts\patch_readiness.ps1`) — validated. All items 2–5 depend on it.

---

## BloomOS and Station Calyx Expectations (retained)

| Source | Expectation |
|--------|-------------|
| **BloomOS** | Reads STATE.md: Status, heartbeat_ts, checks, health, entropy_tier. Acts on unhealthy, stale, health=fail, entropy_tier=unacceptable. Rest is context. |
| **Station Calyx** | Contract gate, spine, receipts, CBO Core. Services: Dev Harness (7777), CBO Core (7778), Avatar Web (7780), Telemetry Gateway (7781). Governance: sponsorship, stamping, integrity gate. |
| **HEARTBEAT** | Runs update_state_checks; reads STATE; notes check=fail or health=fail. |
| **Entropy** | pass &lt; 50% CPU; high 50–70%; unacceptable ≥ 70%. Concentrated runs during defined Station intervals; unattended = stricter limits. |

---

## Item 2: Minimal Sunrise (service subsets)

**Goal:** Start only the services needed for a given operation. Reduces load vs full sunrise.

**Script:** `Scripts\start_minimal.ps1 -Mode <patch|bridge|full> [-StopFirst]`

| Mode | Services started | Use case |
|------|------------------|----------|
| `patch` | Dev Harness (7777), CBO Core (7778) | Patch delivery, spine execution, tool repairs that need CBO |
| `bridge` | CBO Core (7778) | OpenClaw bridge, get_state, send_to_cbo only (no repo tools) |
| `full` | All four (7777, 7778, 7780, 7781) | Full sunrise; same as start_calyx_core_services.ps1 |

**Wiring:**
- Reuse `start_calyx_core_services.ps1` logic: port stop, venv python, uvicorn.
- `start_minimal.ps1` filters `$services` by mode before the foreach.
- **Dependency:** Dev Harness before CBO Core for patch mode (CBO calls /repo/list).
- **Bridge mode:** CBO Core alone — no Dev Harness if caller only needs /state, /chat, /sponsorship, /execute.
- **Validation:** Run check_calyx_core_services.ps1 for started ports only; update_state_checks.

**BloomOS:** No change. checks= still reports all four ports; started ports=ok, others=fail when minimal. Or: extend checks to support "partial" (e.g. `checks: dev_harness=ok,cbo_core=ok,avatar_web=skip,telemetry_gateway=skip`). Prefer: keep checks as-is; BloomOS sees fail for unstarted services — acceptable for minimal mode.

---

## Item 3: Standalone Repair Pattern (no CBO)

**Goal:** Repairs that don't need CBO Core — config edits, pip installs, script fixes. Run without any Calyx services.

**Pattern:**
1. Run `patch_readiness.ps1`; if exit 1, defer.
2. Run repair (e.g. pip install, file edit, script fix).
3. Exit.

**Script template:** `Scripts\repair_<name>.ps1`

```powershell
# Example: Scripts\repair_venv_deps.ps1
& "$PSScriptRoot\..\Scripts\patch_readiness.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }
# ... repair logic ...
```

**Wiring:**
- No new service startup. Repair scripts are one-shot.
- Document in STATE.md Health section: "Standalone repair: run patch_readiness first; no services required."
- Add `docs/operations/STANDALONE_REPAIR_PATTERN.md` with template and examples.

**BloomOS:** No change. Standalone repairs don't touch STATE checks.

---

## Item 4: Deferred Patch Queue

**Goal:** When entropy_tier=unacceptable or health=fail, queue patch/repair intents. Process when entropy allows.

**Artifacts:**
- `runtime/patch_queue.jsonl` — append-only queue. Each line: JSON object `{ "ts": "ISO", "intent": "description", "action": "patch|repair|restart", "payload": {...} }`.
- `Scripts\process_patch_queue.ps1` — reads queue; for each entry: run patch_readiness; if ready, execute (or invoke handler); remove entry; else leave and retry next run.

**Queue entry schema:**
```json
{"ts":"2026-02-24T19:00:00Z","intent":"Apply config fix","action":"patch","payload":{"script":"Scripts\\apply_config_fix.ps1"}}
```

**Wiring:**
- **Enqueue:** Patch/repair scripts (or agents) append to `runtime/patch_queue.jsonl` when patch_readiness fails. Or: explicit `Scripts\enqueue_patch.ps1 -Intent "..." -Action patch -Payload '{"script":"..."}'`.
- **Process:** `process_patch_queue.ps1` runs on heartbeat when entropy_tier=pass and health!=fail. Limit: process at most N entries per run (e.g. 1–2) to avoid burst.
- **Heartbeat hook:** HEARTBEAT.md step: "If patch_queue.jsonl has entries and patch_readiness passes, run process_patch_queue.ps1 (max 1–2 items)."
- **Unattended:** When human away, BloomOS/agent runs heartbeat; sees entropy pass; processes queue. Self-preservation: if patch_readiness fails during process, stop and defer remaining.

**BloomOS:** No change to STATE fields. HEARTBEAT.md gains one conditional step.

---

## Item 5: Single-Service Restart

**Goal:** Restart only the service that was patched. Avoid full sunrise for targeted fixes.

**Script:** `Scripts\restart_service.ps1 -Service <dev_harness|cbo_core|avatar_web|telemetry_gateway>`

**Wiring:**
- Reuse `Stop-ProcessOnPort` and uvicorn start from `start_calyx_core_services.ps1`.
- Map service name → port, module. Restart that one only.
- **Pre-check:** Run patch_readiness; if not ready, exit 1 with "Defer restart; entropy high."
- **Post-check:** Wait ~5s; run check_calyx_core_services.ps1 for that port; update_state_checks.

**Service map:**
| Service | Port | Module |
|---------|------|--------|
| dev_harness | 7777 | cbo_hub.dev_harness.app:app |
| cbo_core | 7778 | cbo_hub.cbo_core.app:app |
| avatar_web | 7780 | cbo_hub.avatar_web.app:app |
| telemetry_gateway | 7781 | cbo_hub.telemetry_gateway.app:app |

**BloomOS:** No change. checks= updated by update_state_checks after restart.

---

## Integration Summary

| Item | Script(s) | Depends on | BloomOS / STATE |
|------|-----------|------------|-----------------|
| 2. Minimal sunrise | start_minimal.ps1 | patch_readiness (optional pre-check) | checks= for started ports |
| 3. Standalone repair | repair_*.ps1 (template) | patch_readiness | None |
| 4. Deferred queue | enqueue_patch.ps1, process_patch_queue.ps1 | patch_readiness | HEARTBEAT hook |
| 5. Single-service restart | restart_service.ps1 | patch_readiness | update_state_checks |

---

## Unattended / Autonomous Operation

When Station runs without human presence:

1. **Concentrated runs** — Heavy work (LLM, tool loops, patches) during defined Station intervals. Don't spread across the day.
2. **Stricter entropy** — When unattended, treat entropy_tier=high as defer (use -Strict for patch_readiness in queue processing).
3. **Self-preservation** — If patch_readiness fails, defer. Don't push through. Queue and retry when pass.
4. **Heartbeat drives queue** — process_patch_queue runs on heartbeat when ready. Max 1–2 items per heartbeat to avoid burst.

**Future:** `runtime/station_intervals.json` or STATE override: `unattended: true` → BloomOS uses -Strict for all patch/queue operations.

---

## Navigator and Triage (minimal sunrise)

- **Navigator:** `Scripts/navigator.ps1` — cadence/interval control; uses patch_readiness. Wires first.
- **Triage Orchestrator:** `Scripts/triage_orchestrator.ps1` — health probe; uses patch_readiness. Goes live after Architect review.
- **Design:** `docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md`
- **Test:** `Scripts/test_navigator_triage.ps1`

## Implementation Order

1. **Item 5** — restart_service.ps1 (smallest; reuses existing logic)
2. **Item 2** — start_minimal.ps1 ✓ (implemented)
3. **Navigator + Triage** ✓ (implemented; Navigator first, Triage after review)
4. **Item 3** — STANDALONE_REPAIR_PATTERN.md + one example repair script
5. **Item 4** — patch_queue.jsonl, enqueue_patch.ps1, process_patch_queue.ps1, HEARTBEAT hook

---

## References

- `Scripts/patch_readiness.ps1` — gate for all items
- `Scripts/start_calyx_core_services.ps1` — source for minimal/restart logic
- `docs/operations/ENTROPY_AND_ENERGY_BASELINE.md` — thresholds, autonomy
- `cbo_hub/docs/CALYX_CORE_SERVICES.md` — service list
- `HEARTBEAT.md` — heartbeat steps
- `STATE.md` — BloomOS expectations
