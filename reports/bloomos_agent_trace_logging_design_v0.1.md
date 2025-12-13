# BloomOS Agent Trace Logging Design v0.1

## Trace Path & Format
- Path: logs/agents/<agent_id>_trace.jsonl
- Format: JSONL, append-only

## Required Fields (per entry)
- ts (UTC ISO8601)
- agent_id
- lifecycle_phase (seeded|sprout|bloom|dormant|compost)
- intent (current goal)
- context/mandate_ref
- inputs_summary (key signals/data refs)
- decision (run/skip/error/plan)
- action (proposed or executed)
- outcome (result or N/A if plan)
- uncertainty (optional notes)
- test_mode (bool)
- respect_frame/laws (e.g., [2,5,9,10,3.4.1])

## Integration
- Overseer traces: can correlate agent traces with logs/overseer_loop_trace.jsonl via timestamps/agent_id.
- Governance/provenance: bridge pulses can summarize recent agent traces (counts, last decision, last action) for visibility.
- Append-only, privacy-aware: redact sensitive payloads; store summaries/refs rather than raw data when needed.

## Alignment with Laws & Agent Transparency
- Law 2: lifecycle_phase and mandate_ref bound autonomy.
- Law 4: inputs_summary/outcome provide telemetry for decisions.
- Law 5: no hidden channels; logs are discoverable and append-only.
- Law 9: intent+decision+action+outcome gives causal chain.
- Law 10: respect_frame/laws and test_mode distinguish human-reviewed vs bounded runs.
- Agent Transparency (§3.4.1): enforces visibility of intent, evidence, reasoning (via decision/action/outcome), constraints (mandate_ref/lifecycle), and uncertainty.

## Guidelines
- Keep entries concise; link to larger artifacts (reports/run directories) instead of embedding bulk data.
- Rotate/compress archives while preserving append-only semantics (no in-place edits).
- Tag test_mode=true for simulations/validations.

## Notes
- Design-only; no code changes yet.
- Future: define a small validation tool to check schema compliance per agent.
