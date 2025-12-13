# BloomOS Agent Introspection Framework (Design) v0.1

## Purpose
Define a standard, append-only introspection interface for all agents to expose their state to the Architect, aligning with Agent Transparency Doctrine (Calyx Physics §3.4.1) and Laws 2/4/5/9/10.

## Required Introspection Fields (per agent)
- identity: unique agent_id
- mandate_ref: reference to mandate registry entry
- lifecycle_phase: seeded|sprout|bloom|dormant|compost
- intent: current goal/mission statement
- current_task: short label of active task/run
- inputs: summary of key inputs/signals consumed
- constraints: list of applied boundaries/limits
- uncertainty: known gaps/assumptions/confidence notes
- last_decision: brief description of last choice made
- planned_next_step: proposed next action(s)
- respect_frame: laws/gov frames the agent asserts (e.g., [2,5,9,10,3.4.1])
- health: optional metrics (e.g., heartbeat freshness, error state)

## Suggested Storage Layout
- Path: state/agents/<agent_id>/introspection.json (append-friendly rotation or versioned snapshots)
- Optionally: state/agents/<agent_id>/introspection_history.jsonl for historical snapshots.
- Ownership: agent writes; overseer/CLI reads; append-only rotation to preserve history.

## Introspection CLI/Tool (concept)
- Command: python tools/agent_introspect.py --agent <id> [--history N] [--as-of TS]
- Behavior: read current introspection.json (and history), render in human-friendly table/JSON; highlight missing fields; optionally validate against mandate registry.
- Output: stdout plus optional report eports/agent_<id>_introspection_snapshot_<ts>.md when requested.

## Alignment to Doctrine and Laws
- Agent Transparency: enforces intent/evidence/constraints/reasoning visibility (fields above).
- Law 2 (Bounded Autonomy): lifecycle_phase + constraints + mandate_ref make limits explicit.
- Law 4 (Telemetry First): health + inputs + last_decision provide evidence.
- Law 5 (No Hidden Channels): standard file location and append-only history prevent silent state.
- Law 9 (Traceable Causality): last_decision + planned_next_step + history enable reconstruction.
- Law 10 (Human Primacy): introspection is for Architect oversight; no self-authorization implied.

## Notes
- This is a design artifact only; no code changes yet.
- Recommend small JSON schema validation for consistency, and rotation rules to avoid unbounded growth.
