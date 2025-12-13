# Night Cycle Test Block v0.1 (Prepared, Not Executed)

Posture: Quiet Maintain. No new loops. No planner activity. No config changes. No agent promotions. No external dependencies. For Architect-triggered execution only.

## Objective
Run a bounded Night Cycle that performs only passive, low-risk integrity checks and coherence scans, producing a morning summary report.

## Constraints (must hold)
- No scheduling/recurring loops; single bounded execution window.
- No planners/schedulers invoked.
- Validators/Telemetry-only behavior; no code changes, no mandate changes.
- No network use; no external dependencies.
- Append-only logging; respect_frame="night_cycle_doctrine".

## Proposed checks (all passive/read-only)
1) Schema sanity: validate agent introspection/trace schemas against current artifacts (cp14/cp18/cp17) without modifying them.
2) Governance log coherence: ensure `logs/canon_ingestion_log.jsonl` and `logs/investigative_log.md` entries are well-formed (read-only).
3) Report presence check: verify latest compliance/governance reports exist (no content changes).
4) Snapshot consistency: count latest `logs/system_snapshots.jsonl` entries and confirm timestamps are monotonic (no writes).

## Execution notes
- Mode: manual, Architect-triggered.
- Duration: bounded single run; no background processes persist after completion.
- Logging: any findings appended to a dedicated log (e.g., `logs/night_cycle_diagnostics.jsonl`) and summarized in the morning report.

## Morning summary artifact (to be generated after run)
- Path: `reports/night_cycle_morning_summary_pending.md` (placeholder until run is performed).
- Contents: ts window, checks executed, anomalies detected, corrections (if any and within doctrine), respect_frame="night_cycle_doctrine".

## Readiness checklist before running
- Confirm no other maintenance or daemon activity is scheduled during the window.
- Confirm write permissions to `logs/` and `reports/` for summary logging.
- Confirm time window is explicitly bounded by the Architect.
