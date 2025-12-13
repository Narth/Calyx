# Station Calyx - Current Environment Constraints
**Prepared by:** CBO Bridge Overseer  
**Generated:** 2025-10-29

---

## Access & Privileges
- **Run context:** Admin-elevated maintenance window active (granted 2025-10-28 07:55 local).
  - Windows Task Scheduler now runs autonomy monitor, supervisor adaptive loop, metrics cron, triage probe, watchdog repair, and alerts cleanup as SYSTEM; wrapper logs recorded at `outgoing/tasks/Calyx*_20251028_075918.log`.
  - `tools/process_watchdog.py --apply --once` executed post-install; no stale Python workers remain.
- **Filesystem permissions:** Read/write scope still limited to `C:\Calyx_Terminal\` and the user profile.
  - Scheduled tasks emit telemetry into the shared workspace (`outgoing\tasks\*`); no secondary volumes mounted.
  - Network access remains disabled per harness policy.

## Hardware Snapshot
- **Memory:** 17,019,351,040 bytes (~15.8 GiB) physical RAM.
  - Pagefile pinned to 24,576 MB minimum / 32,768 MB maximum (Win32_PageFileSetting); reboot recommended to ensure the new cap is honored.
  - Adaptive scheduler keeps memory usage below 70-78% via soft-limit scaling.
- **Storage:** Single workspace partition available; concept archives and compression jobs must assume shared disk IO.
- **GPU:** `nvidia-smi -lgc 2115,2115` applied to lock graphics clocks at max boost during the research window.
  - Use `nvidia-smi -rgc` after the window closes to restore adaptive behaviour if desired.

## Active Tooling Baseline
- Adaptive scheduler (`tools/agent_scheduler.py`) promoted to `apply_tests` cadence with `--run-tests` + `--preflight-compile`; runs are managed by `svc_supervisor_adaptive` and logged in `logs/agent_scheduler.log`.
- Granular TES logging (`logs/granular_tes.jsonl`) and daily report scaffold remain in place.
- Watchdog utilities now run with `--apply`; see `outgoing/watchdog/process_watchdog.log` entry `2025-10-28T14:56:34Z`.
- Live dashboard (`reports/live_dashboard.html`) now surfaces LLM latency p50/p95 alongside TES/resource views.
- SYSTEM scheduled tasks verified via `Get-ScheduledTask -TaskName "Calyx*"`; fresh logs available for health audits.
- Observability suite (`tools/observability_phase1.py`) produces reliability, latency, watchdog, TES, and AGII reports on each scheduled run.

## Gaps vs CGPT Production Spec
- Vector database / RAG service (FAISS/Qdrant, Ollama) not yet installed.
- Multi-volume layout (`C:\calyx`, `D:\calyx`) still pending; all data resides on the workspace disk.

---

**Next Review:** Post-research window (<= 10 hours) or after Phase 1 observability hardening to confirm steady-state.  
**Pending Approvals:** None. Inform CBO if GPU clocks should be unlocked or if additional services need elevation.
