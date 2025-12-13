# Overseer Loop Observability & Test Mode Design v0.1

## Objectives
- Observable decisions per overseer loop (run/skip/error + why).
- Bounded test mode for daemon loops under controlled conditions.
- Integrate loop-level traces into governance/provenance frames.

## Trace Logging Schema (proposed)
- Location: logs/overseer_loop_trace.jsonl (append-only JSONL).
- Fields (per entry):
  - 	s (UTC ISO8601)
  - loop (heartbeat|supervisor|metrics|optimizer|housekeeping|scheduler|navigator|triage)
  - mode (safe|daemon)
  - decision (run|skip|error)
  - eason (free text; e.g., "allow_daemons=false", "interval_elapsed", "no work")
  - effects (list; e.g., ["wrote_cbo_lock", "recomputed_capacity", "started_process:metrics_cron"])
  - 	est_mode (bool)
  - espect_frame (e.g., neutral_observer)
  - laws (list; e.g., [2,4,5,9,10])
  - duration_ms (optional timing)
  - err (optional error string if decision=error)

## Loop Logging Expectations
- Heartbeat: decision run|skip; effects: wrote_cbo_lock, updated_capacity; reason includes allow_daemons flag state.
- Supervisor: decision run|skip; effects: ensured_services|none; reason includes current enablement and findings.
- Metrics: decision run|skip; effects: launched metrics_cron? recomputed stats?; reason includes allow_daemons and interval gating.
- Optimizer: decision run|skip; effects: optimizer_invoked; reason includes policy/flags.
- Housekeeping: decision run|skip; effects: cleanup_performed|none; reason includes elapsed interval.
- Scheduler/Navigator/Triage (if supervised): log when supervised/ensured; effects may include process start/stop.

## Test Mode (bounded) Interface
- CLI flags:
  - --test-loops heartbeat,supervisor,... (comma list)
  - --test-iterations N (per loop, default 1)
  - --test-max-seconds S (wall-clock cap)
  - Optional --test-sleep SECONDS between iterations (default derived from interval)
- Behavior:
  - Forces allow_daemons=True inside test harness but prevents indefinite looping; runs bounded iterations then exits.
  - Writes loop trace entries with 	est_mode=true and mode=daemon.
  - Emits a summary artifact: eports/cbo_overseer_daemon_test_summary_v0.1.md with counts per loop (run/skip/error), timestamps, and key effects.
- Safety: no network changes; uses existing configs; stops automatically at cap.

## Governance/Provenance Integration
- Bridge pulses: add a short "Overseer loop snapshot" section summarizing last window (counts run/skip/error per loop from trace file, bounded to recent entries) and cite Laws (2/4/5/9/10) plus respect_frame.
- Trace file serves as evidence for Law 5 (no hidden channels) and Law 9 (traceable causality); respect_frame stored per entry.

## Rollout Order
1) Implement loop trace writer (JSONL) with minimal overhead; add calls at each loop decision point.
2) Add test mode CLI wrapper (bounded iterations/time) writing summary report.
3) Integrate recent loop summary into bridge pulses’ governance/provenance block.
4) Add optional verbose flag to print loop decisions to stdout/stderr for interactive debugging.

## Rationale
- Law 2/10: Explicitly show when daemon loops run and ensure they can be bounded in test mode.
- Law 4/9: Trace entries with timestamps/reasons/effects provide causal chains and evidence.
- Law 5: Trace log prevents hidden channels; pulses summarize loop activity for human oversight.

## Example Trace Entries (JSONL)
{"ts":"2025-12-06T01:00:00Z","loop":"heartbeat","mode":"safe","decision":"run","reason":"interval_elapsed","effects":["wrote_cbo_lock","recomputed_capacity"],"test_mode":false,"respect_frame":"neutral_observer","laws":[2,4,5,9,10],"duration_ms":120}
{"ts":"2025-12-06T01:00:00Z","loop":"metrics","mode":"daemon","decision":"skip","reason":"allow_daemons=false","effects":[],"test_mode":false,"respect_frame":"neutral_observer","laws":[2,10]}
{"ts":"2025-12-06T01:05:00Z","loop":"housekeeping","mode":"daemon","decision":"error","reason":"cleanup_failed","effects":[],"err":"PermissionError"}

## Summary Artifact (test mode)
- Path: eports/cbo_overseer_daemon_test_summary_v0.1.md
- Contents: loops requested, iterations, outcomes (run/skip/error counts), notable effects, any errors, timing bounds, and Law mapping.
