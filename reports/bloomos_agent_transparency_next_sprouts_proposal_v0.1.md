# BloomOS Agent Transparency - Next Sprout Candidates v0.1

## Candidate 1: cp18_validator
- Role: static/dry diff analysis for syntax sanity and test marker integrity; writes verdicts to `outgoing/reviews/*.CP18.verdict.json`.
- Mandate_ref (proposed): `agents.cp18_validator` in `canon/agent_mandate_registry_v0.1.yaml`.
- Fit for early transparency: complements cp14_validator; deterministic, read-only, Architect-invoked; easy to instrument without autonomy.
- Minimal work:
  - Mandate entry: permissions read repo/logs/reports/outgoing, write outgoing/reviews; prohibitions: repo writes, network, daemons; lifecycle_phase `sprout`; supervisor `cbo`; transparency fields same as cp14.
  - Introspection: add `state/agents/cp18_validator/introspection.json` with inputs (patch, metadata, files parsed), constraints, last_decision, planned_next_step, respect_frame (Laws 2/4/5/9/10, 3.4.1).
  - Trace log: `logs/agents/cp18_validator_trace.jsonl` mirroring cp14 schema, logging decision (run/skip/error) and outcomes.
  - Lifecycle: set to `sprout`; no new autonomy or schedulers.

## Candidate 2: cp17_report_generator
- Role: generates human-readable intent reports into outgoing reports/proposals; Architect-triggered content synthesis.
- Mandate_ref (proposed): `agents.cp17_report_generator` in registry.
- Fit for early transparency: produces human-facing narratives; intent/evidence/constraints logging improves governance of generated artifacts and prevents silent drift in summaries.
- Minimal work:
  - Mandate entry: permissions read intents/metadata/reports, write outgoing/reports; prohibitions: repo writes, network, daemons; lifecycle_phase `sprout`; supervisor `cbo`; transparency fields include intent, evidence, constraints, action_proposal, post_reflection.
  - Introspection: `state/agents/cp17_report_generator/introspection.json` capturing source inputs (intent id, metadata), current_task (draft/generate), uncertainty (coverage gaps), planned_next_step (deliver draft).
  - Trace log: `logs/agents/cp17_report_generator_trace.jsonl` recording decision (generate/skip), action (report path), outcome (status/errors), test_mode flag if used for dry-runs.
  - Lifecycle: remain `sprout`; no autonomous scheduling; Architect-invoked only.

## Prioritization
1) Start with cp18_validator (closest analogue to cp14, low side-effects, clear mandate).  
2) Follow with cp17_report_generator to cover content-producing agent before expanding to planners/schedulers.  
Both keep transparency surface small and high-value while we refine schemas and rotation policies.
