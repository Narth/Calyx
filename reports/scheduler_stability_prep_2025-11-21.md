# Scheduler Stability Test Kit Prep — 2025-11-21

**Author:** CBO  
**Reference:** `outgoing/CGPT/scheduler_stability_test_kit.md`

## 1. Prerequisite Checklist
| Requirement | Status | Notes |
| --- | --- | --- |
| 10 micro discipline runs complete | ✅ | Logged in `logs/agent_scheduler.log` (tick count = 10). |
| Interceptor wired on scheduler launches | ✅ | `reports/intercepts/20251120-231100-568_agent1_agent_task.json` shows dry-run record with TES/AGII/resources. |
| Mailbox poller auto-ack online | ✅ | `tools/mailbox_poller.py` running (2s cadence), state file at `state/mailbox_poller_state.json`. |
| RAM sustained < 72% for one scheduler cycle | ⚠️ Pending | Need to catch quiet window after log cleanup; currently idling ~74%. |
| CPU sustained < 70% | ✅ | Last 24h baseline ~25–30%. |
| Guardrail locks clean (no stale .lock) | ✅ | `_cleanup_stale_locks()` run at 06:06Z tick. |
| Uptime tracker active | ✅ | `tools/uptime_tracker.py` still writing `outgoing/uptime_tracker.lock`. |

## 2. Instrumentation Plan
1. **Switch Mode:** `python tools/agent_scheduler.py --mode normal --interval 180 --run-once` (with load_mode set to `normal` once RAM <72%).  
2. **Telemetry Hooks:**  
   - Capture `logs/agent_scheduler.log` tail for the cycle.  
   - Dump `psutil` snapshot to `reports/scheduler_exit_metrics.json`.  
   - Record TES before/after from `logs/agent_metrics.csv`.  
3. **Safe-Mode Cycle:** Immediately run `python tools/agent_scheduler.py --mode safe --run-once`.  
4. **Artifacts:**  
   - `/reports/scheduler_exit_test_{ts}.md` (per CGPT schema).  
   - `/reports/scheduler_ready.flag` (single-line `ready_for_phase_1s = true`) after PASS.  
5. **Automation:** small helper script `tools/run_scheduler_stability.py` (todo) will orchestrate the two cycles and write the report template.

## 3. Data Capture Template (`scheduler_exit_test_{ts}.md`)
```
cycle_duration_ms: <int>
cpu_peak: <percent>
ram_peak: <percent>
num_agent_launches: <int>
num_agent_failures: <int>
num_orphan_processes: <int>
heartbeat_avg_ms: <float>
log_growth_kb: <float>
TES_before: <float>
TES_after: <float>
safe_mode_cpu_peak: <percent>
safe_mode_ram_peak: <percent>
verdict: PASS|FAIL
notes: |
  free-form observations
```

## 4. Next Actions
1. Drain RAM to <72% (log cleanup + idle window) so the “normal mode” cycle meets guardrail.  
2. Once condition met, run helper script and drop report + flag into `/reports/`.  
3. Notify User1 + CGPT via `/outgoing/User1/` letter and CGPT alignment update.

_Documented for traceability before triggering the official kit run._
