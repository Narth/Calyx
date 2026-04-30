---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Station Health — BloomOS audit and build path safety

**Purpose:** Audit the Station health check build path for BloomOS alignment and safety. CBO monitors this path; BloomOS agents use Status + heartbeat_ts + checks + health from STATE.md.

**Airflow principle (2026-02-25):** Regulate execution by controlling **ingestion** (when/how much data) vs **writing** (accomplishing the task). Throttle ingestion; direct energy to writing. Health and State on 1s timer (needed to detect when Station comes down after load). Hardware ingestion committed to Station Calyx on this node during maintenance. Crucial compute reserved for Station Calyx and CBO.

---

## BloomOS expectations (from STATE.md)

BloomOS agents read the **Status (BloomOS: read this first)** block and use **only**:

- **Status** — maintenance | healthy | degraded | failing
- **heartbeat_ts** — last heartbeat UTC ISO
- **checks** — dev_harness, cbo_core, avatar_web, telemetry_gateway (=ok or =fail)
- **health** — pass | warn | fail | unknown (from station_health_loop)

**Action:** Act on unhealthy, stale, or health=fail. Rest is context.

---

## Build path (data flow)

```
station_health_loop.ps1 (1s)  →  runtime/station_health.json
                                        ↓
                              runtime/station_health_history.jsonl (every 60s, last 24h)
                                        ↓
update_state_checks.ps1 (on heartbeat)  →  STATE.md (health, health_ts)
                                        ↓
HEARTBEAT.md (agent reads STATE)  →  BloomOS / CBO response
```

1. **station_health_loop.ps1** — Lightweight loop (CPU, RAM, GPU, top 3 processes, entropy). Writes `runtime/station_health.json` every ~1s (default). Appends compact snapshot to `runtime/station_health_history.jsonl` every 60s (configurable via `-HistoryIntervalSec`); keeps last 24h (1440 entries). Thresholds: CPU 75/92%; RAM 80/92%; GPU util 70/88%, VRAM 80/95%, temp 80/90°C. Entropy: tier (pass|high|unacceptable), baseline_cpu (rolling median), cadence_70, entropy_sources (top 5 by current CPU %; per-process capped at 100% for decision-making; cpu_pct_raw when raw > 100). GPU via nvidia-smi (same as Task Manager); null if no NVIDIA.
2. **update_state_checks.ps1** — Runs on each heartbeat. Reads `runtime/station_health.json`, merges `health`, `health_ts`, and `entropy_tier` into STATE.md. Also runs check_calyx_core_services.ps1 for port checks.
3. **HEARTBEAT.md** — Instructs agent to run update_state_checks, read STATE (Status + checks + health), and note if health=fail or any check=fail.

---

## Safety audit

| Criterion | Status | Notes |
|-----------|--------|-------|
| **No destructive writes** | OK | Loop writes only runtime/station_health.json; update_state_checks rewrites only STATE.md (checks, heartbeat_ts, health, health_ts). |
| **No secrets** | OK | station_health.json contains cpu_pct, ram_pct, gpu (util_pct, vram_pct, temp_c), top process names/PIDs, health, timestamps. No tokens, keys, or PII. |
| **Minimal CPU impact** | OK | Loop uses Get-CimInstance for CPU (non-blocking; Get-Counter -SampleInterval 1 caused periodic CPU spikes on loop cadence), RAM, nvidia-smi (GPU), Get-Process (top 3). Single PowerShell process. |
| **Stop mechanism** | OK | Create `runtime/station_health.stop` to stop the loop. Loop removes file on exit. |
| **BloomOS boundary** | OK | Calyx produces STATE; BloomOS consumes. No reverse dependency. |
| **Stale handling** | OK | If loop not running, health=unknown. update_state_checks still runs; BloomOS sees unknown and can act (e.g. prompt to start loop). |
| **Threshold alignment** | OK | CPU/RAM match build_safety_check. GPU: more conservative (util 70/88%, VRAM 80/95%, temp 80/90°C) — activity decision-making; too much GPU = entropy, crash. |

---

## CBO monitoring

CBO monitors this build path by:

1. **On heartbeat:** Running update_state_checks (per HEARTBEAT.md), reading STATE, and responding to health=fail or check=fail.
2. **On request:** Running station_health_check.ps1 or build_safety_check.ps1 before heavy work.
3. **Audit:** This doc. Update when the build path or BloomOS expectations change.

---

## Start / stop

**Start health loop (background):**
```powershell
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','Scripts\station_health_loop.ps1' -WindowStyle Hidden
```

**Stop health loop:**
```powershell
New-Item -ItemType File -Path runtime\station_health.stop -Force
```

**Verify:** Check `runtime/station_health.json` exists and has recent `health_ts`.

---

## Station health history

`runtime/station_health_history.jsonl` — JSON Lines (one JSON object per line), compact snapshots every 60s. Retention: last 24h (1440 entries). Fields: `ts`, `health`, `cpu_pct`, `ram_pct`, `entropy_tier`, `cadence_70`, `baseline_cpu`, `gpu_util_pct`, `gpu_vram_pct`, `gpu_temp_c`. Use for trend analysis and entropy audits.
