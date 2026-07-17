# Correlation Activity Logging

**Purpose:** Record when key activities occur so they can be correlated with CPU/utilization graphs. Overlay timestamps with Task Manager or `station_health_history.jsonl` to see what was happening during spikes.

**Important:** Correlation does not imply causation. A logged event at time T does not mean that event caused a spike at T. Use for hypothesis-forming only.

---

## Log location

`runtime/correlation_activity.jsonl` — append-only, one JSON object per line.

## Format

```json
{"ts_utc":"2026-02-27T12:34:56.789Z","component":"station_health","event":"history_write","duration_ms":0}
```

| Field | Description |
|-------|--------------|
| `ts_utc` | ISO 8601 UTC timestamp |
| `component` | Source: station_health, navigator, triage, discord_gateway, cbo_local |
| `event` | What happened (see below) |
| `duration_ms` | Optional; elapsed ms when known |

## Instrumented events

| Component | Event | When |
|-----------|-------|------|
| station_health | `history_write` | Every HistoryIntervalSec (default 60s); disk I/O + trim |
| navigator | `run` | When Navigator script starts |
| triage | `run` | When Triage script starts |
| discord_gateway | `heartbeat_sent` | When heartbeat pushed to DM |
| discord_gateway | `message_received` | When a governed message is received |
| cbo_local | `invocation_start` | When CBO begins a local (Ollama) call |
| cbo_local | `invocation_end` | When local call completes (includes duration_ms) |

## Disable

Set `CALYX_CORRELATION_LOG_DISABLED=1` to skip logging (Python). PowerShell checks for env var or a sentinel file `runtime/correlation_log.disabled`.
