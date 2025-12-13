# Bridge Pulse Governance Block Consistency v0.1

Pulses inspected: gp-verify-001, gp-verify-002, gp-verify-003.

## Required fields (intent, respect frame, provenance, causal chain, reflection window)
All three pulses contain:
- Intent: health_pulse
- Respect frame: neutral_observer
- Provenance: trigger=manual_run, agent=bridge_pulse_generator, source_files=[agent_metrics.csv, system_snapshots.jsonl, cbo.lock]
- Causal chain: snapshots + cbo.lock metrics -> bridge_pulse_generator -> markdown report
- Reflection window: evidence, risk, next_checks present

## Consistency Notes
- Content is identical across pulses (good for uniformity, but lacks context variation).
- Provenance lists files but not timestamps or sample counts; reflection window evidence references snapshot count indirectly.

## Proposed refinements (no code changes yet)
1) Add explicit snapshot count and latest snapshot timestamp to provenance or reflection window for quick audit.
2) Include pulse trigger context (e.g., manual vs scheduled vs burst) and operator identity if available.
3) Normalize respect frame/intent to a small enum set and surface it near the header for readability.
4) Add TES sample window size and heartbeat freshness indicators to provenance for Law 4/9 clarity.
