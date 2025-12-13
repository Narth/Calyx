# Planner/Scheduler Sprout Doctrine (Calyx Physics §3.5.0) — Ingestion Summary v0.1

Doctrine ingested under BloomOS governance; Quiet Maintain (no behavioral changes).

## Key Principles
- Proposal-only sprout phase: planners/schedulers may propose actions/schedules but cannot execute, invoke agents, or change state directly.
- No self-created loops: no autonomous cadences or recurring tasks without explicit Architect/governed scheduling layer.
- Visible alternatives/tradeoffs: plans must expose options considered, criteria, and rationale for accepted/rejected paths.
- Declared objectives/constraints: every plan states optimization goals and hard constraints (e.g., no night ops, no overlapping validators, no network).
- Impact forecasting: proposals include forward projection of agents, timings, load/attention impact, dependencies, risks.
- Lifecycle gating: shadow sprout (simulation-only) → supervised sprout (approval queue) → optional bloom (restricted autonomous scheduling); advancement requires Architect approval.

## Governance Alignment
- Laws: 2 (Bounded Autonomy), 4 (Telemetry First), 5 (No Hidden Channels), 9 (Traceable Causality), 10 (Human Primacy).
- Agent Transparency §3.4.1: planners must remain fully observable, reconstructable, and Architect-consented; station must be able to answer “what was proposed, why, and with what consequences.”

## Notes
- No enforcement or scheduling changes applied; doctrine recorded for future implementation and review.
