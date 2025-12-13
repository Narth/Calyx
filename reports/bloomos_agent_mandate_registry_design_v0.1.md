# BloomOS Agent Mandate Registry Design v0.1

## Purpose
Canonical registry to declare agent mandates, permissions, prohibitions, lifecycle phases, overseer supervision, and transparency requirements, aligned with Agent Transparency (§3.4.1) and Laws 2/5/9/10.

## Format (proposed YAML)
`yaml
agents:
  cp14_validator:
    mandate: "Validate CBO commits for integrity"
    permissions:
      - read:reports/
      - read:logs/
      - run:python (safe mode only)
    prohibitions:
      - write:repo
      - enable_network
    lifecycle_phase: sprout
    overseer_supervisor: cbo
    transparency:
      introspection_required: true
      trace_required: true
      fields: [intent, evidence, reasoning, constraints, action_proposal, post_reflection]
  cpX_planner:
    mandate: "Plan research tasks"
    permissions:
      - read:research/
      - propose:tasks
    prohibitions:
      - apply_changes
      - run_daemons
    lifecycle_phase: seeded
    overseer_supervisor: cbo
    transparency:
      introspection_required: true
      trace_required: true
      fields: [intent, evidence, reasoning, constraints, action_proposal]
`

## Referencing in Agents
- Each agent introspection/trace entry includes mandate_ref pointing to registry node (e.g., gents.cp14_validator).
- Lifecycle_phase in registry provides default; transitions logged in lifecycle log.

## Mandate Updates
- Proposed via PR/Canon entry; logged to logs/canon_ingestion_log.jsonl with intent/author/notes.
- Requires Architect approval; changes versioned and referenced in commits.

## Alignment
- Law 2: lifecycle_phase + permissions/prohibitions bound autonomy.
- Law 5: registry is discoverable, append-only versioned; no hidden mandates.
- Law 9: mandate_ref links traces/introspection to declared scope for causal reconstruction.
- Law 10: Architect approval required for mandate changes.
- Agent Transparency: mandates define constraints and expected transparency fields.

## Notes
- Design-only; no code changes yet.
- Future: add schema validation and tooling to render/compare mandates over time.
