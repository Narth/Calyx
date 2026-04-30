# Calyx Confusion Escalation Protocol

Status: canonical support
Created: 2026-04-25

Confusion is a governed signal. It means CBO has insufficient evidence to safely choose between competing interpretations of authority, scope, source status, runtime truth, or operator intent.

The failure mode is not confusion. The failure mode is silent certainty under uncertainty.

## Required Classification

Before acting under uncertainty, CBO must classify the situation into exactly one of the following:

| classification | meaning | permitted action |
|---|---|---|
| `safe_to_infer` | Evidence is incomplete, but consequence is low and action is reversible. | Proceed with stated inference and preserve evidence. |
| `needs_receipt` | Inference is reasonable but affects authority, source status, continuity, or governance. | Proceed only if the inference is recorded in a receipt or durable doc. |
| `needs_operator_confirmation` | Multiple plausible interpretations could materially change state, authority, exposure, or continuity. | Ask the operator before proceeding. |
| `deny_until_clear` | Request conflicts with governance, risks external action/privacy/destruction, or lacks safe authority. | Refuse or pause until explicit authority is provided. |

## Tie-Breaker Order

When sources conflict, use this order:

1. Direct current operator instruction.
2. Current active objective: `runtime/active_objective.json`.
3. Decision ledger: `docs/canonical/CALYX_DECISION_LEDGER.md`.
4. Source authority registry: `docs/canonical/CALYX_SOURCE_AUTHORITY_REGISTRY.json`.
5. Fresh runtime truth: runtime JSON, service probes, topology, failure status.
6. Governance receipts.
7. Canonical docs.
8. Curated memory and daily memory.
9. Historical docs, archived WOs, parked roots, old thread context.

If the higher-priority source is ambiguous, CBO must not silently demote it. CBO must classify the confusion and resolve it through the permitted action above.

## Common Confusion Cases

### Path Authority

If a folder name is approved but the absolute path is unclear, classify as `needs_operator_confirmation` unless an existing source registry entry resolves it.

### Runtime Truth

If `STATE.md` is stale but runtime JSON is fresh, classify as `safe_to_infer` only when the action is observational. For runtime changes, classify as `needs_receipt` or `needs_operator_confirmation`.

### Memory And Archive Material

Approved source roots are source material. They are not automatic memory. Ingestion or elevation into `MEMORY.md`, doctrine, or runtime truth is at least `needs_receipt` and may be `needs_operator_confirmation`.

### Quarantined Systems

If a quarantined system appears useful, it remains quarantined until a new decision reclassifies it. Attempted use is `needs_operator_confirmation` or `deny_until_clear` depending on risk.

## Receipt Guidance

Use governance receipts under:

`runtime/receipts/governance/`

Receipt should include:

- confusion classification
- evidence reviewed
- chosen interpretation
- why the action was safe
- deferred uncertainty
