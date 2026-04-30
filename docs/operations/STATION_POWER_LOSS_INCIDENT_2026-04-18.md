---
status: active
owner: station
last_reviewed_utc: "2026-04-18"
doctrine_scope: governed
---

# STATION_POWER_LOSS_INCIDENT_2026-04-18

## Purpose

This report reconstructs the April 18, 2026 Station Calyx power-loss incident from currently available local evidence only.

This is a read-only reconstruction. No truth surface was refreshed or rewritten for this investigation.

## Evidence Integrity

- `runtime/station_health.json` is the freshest Station artifact on disk. It was last emitted at `2026-04-18T07:20:07.9278650Z` and was fresh at emission.
- `STATE.md`, `runtime/station_heartbeat.json`, `runtime/service_runtime_snapshot.json`, and `runtime/runtime_topology_snapshot.json` are stale now and were not treated as current liveness authority.
- Windows System log directly confirms an unexpected host restart on April 18, 2026.
- Current Station service ports `7777`, `7778`, `7780`, and `7781` are not listening.

## Probable Incident Window

| conclusion | result | confidence | evidence type |
|---|---|---|---|
| last persisted Station evidence before interruption | `2026-04-18T07:20:07.9278650Z` (`2026-04-18 00:20:07` local, Phoenix) | high | direct |
| host reboot observed | `2026-04-18T19:26:05.5000000Z` (`2026-04-18 12:26:05` local) | high | direct |
| probable outage / host-down window | after `2026-04-18T07:20:07.9278650Z` and at or before `2026-04-18T19:26:05.5000000Z` | medium | inference from direct evidence |
| Windows-reported unexpected shutdown time | `2026-04-17 23:43:55` local (`2026-04-18T06:43:55Z`) | low | direct, but conflicts with later Station artifacts |

### Timing Conflict

Windows Event `6008` reports:

> The previous system shutdown at `11:43:55 PM` on `4/17/2026` was unexpected.

That conflicts with later Station-side artifacts persisted after that time, including:

- `runtime/station_health_history.jsonl` sample at `2026-04-18T07:19:40.1468647Z`
- `runtime/station_health.json` emitted at `2026-04-18T07:20:07.9278650Z`
- runtime truth / topology receipts at `2026-04-18T07:09:11Z` to `2026-04-18T07:11:13Z`

Because of that contradiction, the Windows-reported shutdown time is treated as a conflicting signal rather than the final outage timestamp.

## Last Known Live Station State

### Core services and loops visible in the final runtime topology capture

Direct evidence from `runtime/receipts/audit/runtime_topology_snapshot__20260418_070911.json`:

- `dev_harness`
- `cbo_core`
- `avatar_web`
- `telemetry_gateway`
- `station_health_loop`
- `service_failure_watch`
- `navigator_triage_loop`
- `cp6_cp7_loop`
- `bridge_overseer`
- `cli_avatar`
- `discord_gateway`

Not observed in that capture:

- `energy_churn_cp9_loop` (`risk_level = ELEVATED`, `anomaly_flags = ["not_observed"]`)

### Last health envelope before evidence stops

Direct evidence from `runtime/station_health.json` and `runtime/station_health_history.jsonl`:

- last health sample in history: `2026-04-18T07:19:40.1468647Z`
- last health artifact emit: `2026-04-18T07:20:07.9278650Z`
- `health = pass`
- `cpu_pct = 21`
- `ram_pct = 41`
- `gpu.util_pct = 0`
- `gpu.temp_c = 40`
- `gpu.vram_pct = 12`
- `memory_pressure_tier = 0`
- `oom_imminent = false`

Assessment:

- no direct sign of thermal stress
- no direct sign of memory pressure
- no direct sign of imminent OOM
- host CPU activity existed, but dominant top processes were `Code`, not Station services

Confidence: high.

## Multiplicity and Churn Signals

### Final pre-incident live capture

Direct evidence from `runtime/receipts/audit/runtime_topology_snapshot__20260418_070911.json`:

- `classification_status = complete`
- `highest_risk_level = ELEVATED`
- `flagged_services = ["energy_churn_cp9_loop"]`
- `duplicate_services = []`
- `ambiguous_services = []`

Assessment:

- the last known live Station topology before evidence stops was not in a duplicate-runtime crisis
- one loop family (`energy_churn_cp9_loop`) was still missing / flagged

Confidence: high.

### Earlier same-night churn, before governed repair

Direct evidence from `runtime/receipts/audit/runtime_topology_snapshot__20260418_042248.json`:

- `highest_risk_level = CRITICAL`
- duplicate and ambiguous families included:
  - `bridge_overseer`
  - `cp6_cp7_loop`
  - `energy_churn_cp9_loop`
  - `navigator_triage_loop`
  - `service_failure_watch`

Direct evidence from the governed restart sequence:

- patch window entered at `2026-04-18T04:37:37.4524168Z`
- sunrise validated at `2026-04-18T04:39:06.5551879Z`
- post-restart topology at `2026-04-18T04:39:04.150690Z` downgraded to `ELEVATED`
- duplicates and ambiguous services were cleared

Assessment:

- Station had a real multiplicity / churn issue earlier in the night
- that issue was materially improved by the governed restart
- this earlier churn is not the same event as the later host-level power-loss / reboot

Confidence: high.

## Resource Use Before Interruption

Direct evidence from the 47 health samples between `2026-04-18T03:50Z` and `2026-04-18T04:37:30Z`:

- `max_cpu_pct = 66`
- `max_ram_pct = 43`
- `max_gpu_temp_c = 43`
- `max_gpu_util_pct = 38`

Assessment:

- load was elevated at points but not severe
- there is no direct evidence of thermal runaway, RAM exhaustion, or GPU saturation
- Station evidence does not support claiming resource overload as the cause of host power loss

Confidence: medium-high.

## Recovery Observations After Host Restoration

Direct evidence:

- Windows boot event `12` shows OS start at `2026-04-18T19:26:05.500000000Z`
- current Station service ports `7777`, `7778`, `7780`, and `7781` are not listening
- latest runtime artifact writes are still from `2026-04-18 00:09` to `00:20` local
- current investigation shells are visible as `powershell.exe` processes started around `12:29 PM` local; no current evidence of restored Station listeners was found

Assessment:

- the host came back up
- Station Calyx did not automatically restore its service listeners after that reboot
- current truth surfaces are stale pre-reboot artifacts, not live post-reboot telemetry

Confidence: high.

## Can Station Account For Its Own Behavior During The Outage?

Partially.

What Station can account for:

- the last persisted live state before evidence stopped
- the earlier governed restart sequence and its effects
- the service and loop set that was active in the final topology capture
- the absence of severe pre-loss resource stress in the final health window

What Station cannot account for from its own receipts:

- the exact moment power was lost
- the exact runtime topology at the instant of host shutdown
- whether any final in-memory work was lost after the last persisted health sample
- the immediate post-boot Station state, because no Station-side restart receipts exist for the host reboot

## Direct Evidence vs Inference

### Direct evidence

- `STATE.md`
- `runtime/station_health.json`
- `runtime/station_health_history.jsonl`
- `runtime/station_heartbeat.json`
- `runtime/service_runtime_snapshot.json`
- `runtime/runtime_topology_snapshot.json`
- `runtime/receipts/audit/runtime_topology_snapshot__20260418_042248.json`
- `runtime/receipts/audit/runtime_topology_snapshot__20260418_043904.json`
- `runtime/receipts/audit/runtime_topology_snapshot__20260418_070911.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_043737_457.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_043808_503.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_043824_929.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_043906_558.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_043907_648.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_070913_782.json`
- `runtime/receipts/security/runtime_truth_transition__20260418_071113_530.json`
- `runtime/receipts/sunrise_receipt__20260417_213907.json`
- `runtime/receipts/security/telemetry_gateway_audit_readiness__20260418_043839_798190.json`
- `runtime/receipts/security/service_failure_flag__20260418_043911_518.json`
- `cbo_hub/logs/telemetry_gateway_audit.jsonl`
- Windows System log events `41`, `6008`, `6005`, `12`

### Inference

- outage window bounded between last Station artifact and later host boot
- Station did not auto-recover after host reboot
- earlier multiplicity churn was repaired before the later power-loss event
- no evidence-backed resource overload cause exists in the available Station telemetry

## Recommendation

Do not treat this as a blocker for all forward work, but do not ignore the reconstruction gap.

Recommended next step:

- **add new incident-reconstruction surfaces before or alongside `WO_SANDBOXED_WORKER_RUNTIME_V1 — Phase 2`**

Recommended additions:

1. `runtime/receipts/audit/host_boot_detection__YYYYMMDD_HHMMSS.json`
   - emit on first Station start after OS boot
   - record OS boot time, Station artifact freshness gap, and whether the prior Station shutdown was graceful

2. `runtime/receipts/audit/unclean_station_interruption__YYYYMMDD_HHMMSS.json`
   - emit when Station starts after finding stale truth surfaces older than host boot or missing clean shutdown markers

3. explicit clean-shutdown marker
   - compare the last clean shutdown marker against host boot time to distinguish graceful shutdown from abrupt host loss

4. post-boot recovery receipt
   - record whether core listeners were restored automatically, manually, or not at all

Operational recommendation:

- **pause briefly for incident-reconstruction hardening, then continue to `WO_SANDBOXED_WORKER_RUNTIME_V1 — Phase 2`**

Reason:

- the current station can describe its last persisted state
- it cannot yet fully account for the host-down interval or its own post-boot recovery status without operator inspection
