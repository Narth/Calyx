# CBO Overseer Daemon Gate Validation v0.1

## Intended Invariants (Law 2, Law 10)
- Default (Safe Mode): heartbeat-only; no supervisor/metrics/optimizer/housekeeping unless Architect opt-in.
- Daemon Mode (explicit): long-running loops allowed only when --allow-daemons is passed by the Architect.

## Observations
- Safe Mode (python tools/cbo_overseer.py --dry-run):
  - allow_daemons=false
  - Planned loops listed but **not executed** (dry-run prints plan); matches heartbeat-only intent.
- Daemon Mode (python tools/cbo_overseer.py --allow-daemons --dry-run):
  - allow_daemons=true
  - Same planned loops listed; explicit opt-in required.

## Expected vs Actual
- Safe Mode: Expected = no long-running loops. Actual (dry-run) = no loops executed; matches.
- Daemon Mode: Expected = loops permissible when explicitly allowed. Actual (dry-run) = loops would be enabled; opt-in flag required; matches.

## Discrepancies / Edge Cases
- Dry-run validates gating logic but does not exercise real loop start; a live run with --allow-daemons would start supervisor/metrics/optimizer/housekeeping. Recommend a short-timed live check later if needed.
- Scheduler gate is separate (--enable-scheduler); ensure combined use with --allow-daemons is documented.

## Follow-ups
- Add a one-shot health self-check flag (no loop) to validate loop start/stop without sustained run.
- Add explicit log line when loops are skipped because allow_daemons is false.
