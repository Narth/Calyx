# BloomOS Agent Lifecycle Model v0.1

## Phases
- seeded: defined mandate, not yet active
- sprout: initial activation, constrained tasks only
- bloom: full active mode within mandate
- dormant: paused, read-only; no actions
- compost: retired; outputs retained for learning/audit

## Allowed Transitions & Conditions
- seeded -> sprout: Architect approval + mandate registry entry exists
- sprout -> bloom: successful validation, health ok, Architect approval
- bloom -> dormant: manual pause or health/risk trigger
- dormant -> bloom: Architect approval after review
- any -> compost: decommission decision by Architect

## Effects on Permissions/Behavior
- seeded: no execution
- sprout: minimal permissions; logging mandatory; test-mode tasks only
- bloom: full mandate permissions; must emit intent/evidence/trace blocks
- dormant: no actions; may expose introspection state
- compost: no actions; archives only

## Logging & Canon Links
- Lifecycle events logged to logs/agent_lifecycle.jsonl (ts, agent_id, from, to, reason, approver).
- Mandate registry references (mandate_ref) must be cited on transitions.
- Canon alignment: lifecycle changes should be referenced in Canon/commit notes when mandates/permissions change.

## Alignment with Agent Transparency & Calyx Physics
- Transparency: phase and transitions are explicit, logged, and approved (no silent state changes).
- Law 2: permissions tied to phase; autonomy bounded by lifecycle gate.
- Law 4/9: transitions and reasons logged for traceability.
- Law 5: no hidden phase shifts; append-only lifecycle log.
- Law 10: Architect approvals required for activation, promotion, and decommission.

## Notes
- Design-only; no code changes yet.
- Future: add phase-specific guardrails in agent runners (once approved).
