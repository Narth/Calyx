---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Energy Churn Analysis — Planning

**Purpose:** Flush out planning for energy churn analysis and ensuring we maximize every bit of life and data we are given, without blowing a gasket. Development proceeds after this plan is approved.

**Principle:** Constant energy-intensive churn wastes hardware life and burns data/compute without proportional value. We want to detect it, attribute it, and direct energy to high-value work while protecting the machine.

---

## 1. What We Mean by "Energy Churn"

**Churn** = processes consuming CPU, RAM, GPU, or disk I/O without proportional value to the current objective.

| Type | Example | Cost |
|------|---------|------|
| **Over-utilized** | Ollama loaded but idle; CorsairCpuIdService spiking; SearchIndexer indexing; Defender scanning | Burns energy, thermal load, shortens component life |
| **Under-utilized** | Idle cores while one process maxes; GPU sitting cold while CPU burns | Wasted capacity; could offload or batch |
| **Spinning** | Polling loops, frequent health checks, redundant reads | CPU cycles for no new information |
| **Redundant** | Multiple instances of same service; duplicate workers | Memory + CPU contention |

**Maximizing life and data:**
- **Life** = hardware longevity (thermal cycles, sustained load, rest periods)
- **Data** = every bit of compute and storage we have; use it for value, not waste

**Without blowing a gasket:**
- Thermal limits respected
- Sustained 100% avoided when possible
- Cooldown periods between heavy runs
- No crash loops, no OOM kills

---

## 2. Current Data Sources

| Source | Cadence | Contents | Use for churn |
|--------|---------|----------|---------------|
| `runtime/station_health.json` | ~1s | cpu_pct, ram_pct, gpu, entropy_sources, health | Real-time snapshot; who is burning |
| `runtime/station_health_history.jsonl` | 60s append | ts, health, cpu_pct, ram_pct, entropy_tier, cadence_70, baseline_cpu, gpu_* | 24h trend; patterns over time |
| `runtime/carbon_intensity.json` | On heartbeat | gCO2eq/kWh, power_window | When to defer non-urgent work |
| `cbo_hub/receipts/cbo_core.jsonl` | Per request | usage, latency, providers_called | Value delivered per unit energy |

**Gaps:**
- No per-process history (we see top 5 now, but not over time)
- No disk I/O or network attribution
- No "value per joule" metric (work completed vs energy spent)

---

## 3. Churn Detection — What to Surface

### 3.1 Pattern detection (from history)

| Pattern | Signal | Action |
|---------|--------|--------|
| **Sustained high entropy** | cadence_70 > 10 for 5+ consecutive history samples | "Repeatedly maxing; cooldown recommended" |
| **Baseline drift** | baseline_cpu increases over 30+ min without explicit work | "Idle load creeping up; investigate entropy_sources" |
| **Spike clusters** | cpu_pct spikes (e.g. 50→95→50) on regular cadence | "Periodic spike; possible polling or scheduled task" |
| **Ollama dominance** | entropy_sources consistently show ollama#* at 100% when no CBO request | "Ollama burning without directed work" |
| **New persistent source** | New process in top 5 for 10+ samples that wasn't there before | "New churn source: &lt;name&gt;" |

### 3.2 Attribution (from entropy_sources)

| Process | Typical role | Churn when |
|---------|--------------|------------|
| Ollama | LLM inference | Loaded, idle, still at 100% |
| CorsairCpuIdService | Hardware/RGB | Spiking without user action |
| SearchIndexer | Windows search | Indexing during work |
| AntimalwareServiceExecutable | Defender | Scanning during work |
| Cursor | IDE + agent | Background when user idle |
| WmiPrvSE | WMI queries | Our health loop; keep minimal |
| Discord | Notifications | Presence + notifications |

**Churn score (conceptual):** `(cpu_pct_capped * time_at_level) / value_delivered`. High when process burns a lot for little output.

### 3.3 Life maximization signals

| Signal | Meaning |
|--------|---------|
| **Rest opportunity** | cpu_pct < baseline + 10 for 5+ min → machine can cool |
| **Thermal headroom** | gpu_temp_c < 70, cpu not throttled → safe to add load |
| **Cooldown needed** | cadence_70 high, gpu_temp rising → defer heavy work |
| **Efficiency window** | power_window=clean, entropy_tier=pass → good time for batch work |

---

## 4. Maximizing Life and Data

### 4.1 Life (hardware longevity)

- **Thermal cycles:** Avoid rapid heat-up/cool-down. Prefer sustained moderate load over burst/rest/burst.
- **Sustained max:** Avoid 100% CPU for >10 min when avoidable. Cadence gate already defers at cadence_70 > 10.
- **Rest periods:** After heavy work, allow baseline to return before next heavy run.
- **GPU care:** VRAM and temp limits in build_safety_check; respect them.

### 4.2 Data (compute and storage)

- **Direct energy to writing:** Per airflow principle — throttle ingestion, direct energy to accomplishing the task.
- **Batch when possible:** Group similar work; avoid repeated small operations that each incur overhead.
- **Cache what we can:** CBO_STATE_CACHE_SEC, navigator.lock — reduce redundant reads.
- **Kill waste first:** Before adding load, reduce churn (unload Ollama model, pause indexing, etc.).

### 4.3 Without blowing a gasket

- **Pre-flight:** build_safety_check, patch_readiness before heavy work.
- **Single heavy LLM at a time:** Don't stack Ollama + cloud model + tools at max.
- **Escalation:** If health=fail or entropy=unacceptable, defer. No override without explicit confirmation.
- **Observability:** When we add load, we can see who is burning. When we defer, we know why.

---

## 5. Proposed Components

### 5.1 Energy churn analyzer (script or small service)

**Inputs:** `station_health.json`, `station_health_history.jsonl`
**Outputs:** Structured report (JSON + human-readable summary)

**Responsibilities:**
- Read last N history samples (e.g. 60 = 1 hour at 1/min)
- Detect patterns: sustained high, baseline drift, spike clusters, dominant source
- Compute simple metrics: avg cpu, max cadence_70, top entropy_sources by frequency
- Emit: `runtime/deployment/energy_churn_report.json` + optional `.txt` summary

**Cadence:** On-demand, or on a schedule (e.g. every 15–30 min via cron/task). Not in the hot path.

### 5.2 Discord notification (when build ready)

**Requirement:** Notify operator via Discord when the energy churn analysis build is done or ready for testing.

**Mechanism:**
- **Discord webhook** — Create webhook for a channel (e.g. #station-health or DM). POST JSON to webhook URL.
- **Trigger:** When analyzer completes a run, or when a "build complete" script runs.
- **Payload:** Short message, e.g. "Energy churn analysis build ready for testing. Run `Scripts/energy_churn_analyzer.ps1` or see runtime/deployment/energy_churn_report.json"
- **Config:** Webhook URL in `.env.cbo` or `private/` (DISCORD_CHURN_WEBHOOK_URL). Gitignored.

**Scope:** Notification only. No new inbound commands. Deny-by-default preserved.

### 5.3 Integration points

| Component | Reads | Writes | Trigger |
|-----------|-------|--------|---------|
| Analyzer | station_health*.jsonl | energy_churn_report.json | Cron, manual, or post-heartbeat |
| Discord notify | — | POST to webhook | On analyzer completion or explicit "build ready" |
| Navigator / patch_readiness | (existing) | — | Unchanged; may later consume churn report for richer defer reasons |

---

## 6. Phased Implementation

### Phase 0: Planning (this document)
- Flush out plan
- Architect review
- No code

### Phase 1: Analyzer core
- Script: `Scripts/energy_churn_analyzer.ps1` (or Python equivalent)
- Reads history, detects patterns, writes report
- No Discord yet
- Manual run for validation

### Phase 2: Discord notification
- Add webhook config
- On "build ready" or analyzer completion: POST to Discord
- Test with real channel

### Phase 3: Scheduled runs (optional)
- Cron or Task Scheduler: run analyzer every N min
- Only if Phase 1–2 prove useful

### Phase 4: Integration (optional)
- Navigator or patch_readiness reads churn report for richer defer messages
- "Defer: sustained churn (Ollama 100% for 20 min); cooldown recommended"

---

## 7. Success Criteria

- **Detect:** We can identify sustained churn, dominant sources, and rest opportunities from existing data.
- **Report:** Human-readable summary + machine-readable JSON for downstream use.
- **Notify:** Operator receives Discord message when build is ready for testing.
- **Life:** No new sustained 100% load from the analyzer itself; it runs briefly and exits.
- **Governance:** No new network endpoints; no new side effects beyond report + optional Discord POST. Deny-by-default preserved.

---

## 8. References

- `docs/operations/ENTROPY_AND_ENERGY_BASELINE.md` — Entropy tiers, cadence, baseline
- `docs/planning/BUILD_SAFETY_CHECK.md` — Hardware limits, when to defer
- `docs/HARDWARE_OPTIMIZATION.md` — Ollama levers, CBO tuning
- `docs/operations/STATION_HEALTH_BLOOMOS_AUDIT.md` — Health loop, data flow
- `USER.md` — Discord DM and #station-health as primary touchpoints

---

*Planning complete. Development proceeds after Architect approval. Discord notification included as deliverable for "build ready" signal.*

---

## 9. Build-ready flow (implemented)

1. **Sunrise Station Calyx** — start_calyx_core_services, station_health_loop, update_state_checks
2. **Run analyzer** — `Scripts\energy_churn_analyzer.ps1 -NotifyDiscord`
3. **Discord** — If `DISCORD_CHURN_WEBHOOK_URL` is set in `.env.cbo`, POSTs build-ready message

**Webhook setup:** Discord channel → Settings → Integrations → Webhooks → New webhook. Copy URL to `.env.cbo` as `DISCORD_CHURN_WEBHOOK_URL=...`
