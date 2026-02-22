# STATE.md — what to add before automating heartbeat (three-voice run)

**Run:** 2026-02-21 after CBO Core restart.  
**Voices:** Architect (Claude), Workhorse (OpenAI), Second opinion (Kimi K2.5). Kimi wiring fixed: `KIMI_MODEL` fallback + `temperature=1` for K2.5.

---

## Usage and cost (this run)

| Voice   | Provider   | Usage (tokens)                    | request_latency_ms |
|---------|------------|-----------------------------------|--------------------|
| Architect | anthropic | input 105, output 178, total 283  | ~5.6s              |
| Workhorse  | openai   | total 333                         | ~6.6s              |
| Second opinion | kimi | (see below)                       | ~23s               |

**Cost estimate:** `cost_estimate_usd` was not set in receipts because the optional rate env vars (`*_INPUT_PER_MILLION`, `*_OUTPUT_PER_MILLION`) were not set for this CBO Core process. To get cost estimates on the next run, set e.g. in the terminal before starting CBO Core:

```powershell
$env:ANTHROPIC_INPUT_PER_MILLION = "3.0"
$env:ANTHROPIC_OUTPUT_PER_MILLION = "15.0"
$env:OPENAI_INPUT_PER_MILLION = "2.5"
$env:OPENAI_OUTPUT_PER_MILLION = "10.0"
```

---

## Consolidated recommendations (Architect + Workhorse)

Items to add to STATE.md before automating heartbeat status:

### From Architect (Claude)

1. **System health metrics** — CPU, memory, disk usage thresholds and current values  
2. **Service dependencies** — External APIs, databases, critical integrations with their status  
3. **Error rate tracking** — Recent error counts, failure rates, alert thresholds  
4. **Performance benchmarks** — Response times, throughput, SLA compliance  
5. **Resource availability** — Capacity, queue depths, connection pools  
6. **Last successful operations** — Timestamps for key system functions and data flows  
7. **Automated check results** — Self-diagnostic test outcomes and validation statuses  

### From Workhorse (OpenAI)

1. **Explicit status field** — One canonical line, e.g. `Status: healthy | degraded | failing | maintenance` with date/time and who set it  
2. **Last heartbeat metadata** — Last heartbeat time, source (script/tool), last successful check ID/version  
3. **Checks summary section** — Each automated check: name, description, cadence, owner; pass/fail/unknown  
4. **Error/degradation log stub** — Short rolling list: timestamp, component, symptom, link to logs  
5. **Dependencies & contracts** — Critical upstream/downstream and what “up/OK” means for each  
6. **Manual override** — e.g. `Automation override: on/off` with rationale  
7. **Update protocol** — Who/what may edit STATE.md; format for automated vs manual updates  

### From Second opinion (Kimi K2.5)

1. **Health check endpoints** — Specific probe paths (e.g. `/health`, `/ready`) per service beyond base URLs  
2. **Last heartbeat timestamp** — ISO-8601 field updated by automation to detect stale state  
3. **API connectivity matrix** — Last-known HTTP status + latency per model provider (not just routing config)  
4. **Service dependency graph** — Declared upstream/downstream (e.g. CLI Avatar → CBO Core) for cascade failure logic  
5. **Resource thresholds** — Disk % and memory limits that trigger warnings before write operations fail  
6. **Automation lock field** — Mutex (locked/unlocked + PID/timestamp) to prevent concurrent heartbeat updates  
7. **Alert counter** — Consecutive failure tally per service for escalation (page vs. log)  

### Overlap / suggested combined sections for STATE.md

- **Status** — Single canonical status line + last heartbeat time and source  
- **Checks** — List of automated checks with cadence, owner, pass/fail/unknown  
- **Dependencies** — Critical services/APIs and their status or “OK” definition  
- **Health metrics** — CPU, memory, disk (and optionally error rates, latency)  
- **Recent issues** — Short rolling error/degradation log with timestamps  
- **Override** — Manual override flag and rationale  
- **Update protocol** — Who updates STATE.md and in what format  
- **Health endpoints** — Per-service probe paths (e.g. `/health`, `/ready`)  
- **API connectivity matrix** — Last-known status + latency per provider  
- **Dependency graph** — Upstream/downstream for cascade logic  
- **Automation lock** — Mutex (locked/unlocked, PID/timestamp) for concurrent updates  
- **Alert counter** — Consecutive failure tally per service for escalation  

---

**Done:** STATE.md now has a minimal **Status (BloomOS: read this first)** block: `Status`, `heartbeat_ts`, `override`, `lock`, `checks`. Placeholders ready for heartbeat automation. One line at bottom instructs BloomOS agents: use Status + heartbeat_ts + checks only; act on unhealthy or stale. Rest is context—minimal tokens, maximum room for work.
