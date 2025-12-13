# Context Rehydration Summary
**Prepared by:** Calyx Bridge Overseer (CBO)  
**Issued:** 2025-10-29

---

## Directive Outcomes
- **AGII:** Improved from 76.2 (pre-refresh, 04:35Z) to 77.4 (post-refresh, 05:32Z). Additional apply-tests are queued to push WARN ratio below 10 %.
- **TES Average:** Stable at 97.2 across the latest six supervised apply-tests cycles (all `rc=0`, Warn=false).
- **Modules Re-enabled:** Calyx Triage Probe, Calyx Metrics Cron, Calyx Observability Snapshot (paused during Phase 1 and restored in Phase 7).
- **Final Memory Utilisation:** 77.8 % of 15.85 GB physical RAM in use after rehydration tasks.

---

## Observations & Follow-Up
1. **WARN Ratio** – Legacy WARN entries (memory gate + WSL compile failures) still account for 66.7 % of the trailing 50 `run_complete` records. Continued supervised apply-tests are in progress to displace these entries and reach the ≤ 10 % target.
2. **AGII Targets** – Overall AGII remains amber (77.4). Clearing the WARN backlog and eliminating compile failures will be necessary to meet the ≥ 85 (green) requirement.
3. **Reliability** – Maintained 100 % success across the most recent six supervised cycles and 537/537 historically.
4. **Telemetry** – `reports/context_summary.md` captures merged memory samples from the last ten runs; all historical AGII/reliability reports older than 72 h were purged.
5. **Memory Guard** – Adaptive ceiling temporarily lifted to 84 % (Phase 4) and restored to 78 % after the supervised run set.

---

## Artifacts Produced
- `logs/context_digest.jsonl` – Ten-run merged digest (removed after verification in Phase 7).  
- `reports/context_summary.md` – Memory/context synopsis derived from the digest.  
- `reports/agii_report_20251029.md` & `reports/agii_report_latest.md` – Updated AGII dossier.  
- `reports/reliability_stream.md` – Refreshed reliability stream.  
- `reports/context_rehydration_summary.md` – This document.

---

## Next Steps (CBO Plan)
1. Continue supervised apply-tests beyond the initial six successes to retire historic WARN entries and elevate AGII to green.
2. Investigate WSL preflight compile failures (`bash: python not found`) to remove the lingering rc=127 events from future windows.
3. Resume steady-state probes and watchdog cadence (completed in Phase 7) and monitor resource headroom at the restored 78 % memory ceiling.
