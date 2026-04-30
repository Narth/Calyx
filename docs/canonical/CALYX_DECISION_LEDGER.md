# Calyx Decision Ledger

Status: canonical support
Created: 2026-04-25

This ledger records operator decisions that alter Station Calyx authority, scope, source status, or doctrine. It is append-only in practice: new decisions should add entries rather than silently rewriting older ones.

The ledger does not replace receipts. It gives CBO a human-legible tie-breaker before interpreting scattered documentation, code, runtime state, or historical context.

## Decision Format

Each entry should include:

- decision id
- timestamp
- operator directive
- accepted interpretation
- authority effect
- evidence or receipt
- boundaries

## Decisions

### DEC-20260425-001 - Approved Roots Are Calyx Source Authority

Timestamp: 2026-04-25T22:38:02Z

Operator directive:

Approved roots and their subsequent branches are source authority for Station Calyx operations. There is one Station Calyx, one CBO, and one operational truth path.

Accepted interpretation:

The approved roots are authorized Calyx source material for Station analysis, continuity review, and explicitly scoped retroactive-context work.

Authority effect:

- `C:\Calyx_Terminal`, `C:\Calyx_Test_Temp`, `C:\Calyx_Parking`, `C:\Calyx_Federation_Inbox`, and `D:\Calyx_Data` are approved local source roots.
- CBO may use these roots as source material within delegated Station work.
- This decision does not make every file canonical runtime truth by presence alone.
- This decision does not override existing canonical core/support/quarantine classifications.

Evidence:

- `runtime/receipts/governance/approved_root_source_authority_clarification__20260425_153802.json`
- `memory/2026-04-25.md`

Boundaries:

- Human operator authority remains primary.
- CBO is steward and bounded executor, not independent owner.
- Retroactive ingestion or memory elevation still requires an explicitly scoped pass and receipts.

### DEC-20260425-002 - Confusion Must Be Classified Before Action

Timestamp: 2026-04-25T22:45:00Z

Operator directive:

Reduce CBO confusion and increase confidence by implementing a minimal clarity substrate.

Accepted interpretation:

When authority, source status, runtime truth, or scope is unclear, CBO must classify the uncertainty before acting.

Authority effect:

Confusion is no longer treated as an internal hidden state. It must be resolved through one of:

- `safe_to_infer`
- `needs_receipt`
- `needs_operator_confirmation`
- `deny_until_clear`

Evidence:

- `docs/canonical/CALYX_CONFUSION_ESCALATION_PROTOCOL.md`
- `runtime/active_objective.json`

Boundaries:

- This is governance clarification, not a new autonomy layer.
- It does not authorize external communication, ingestion, deletion, or runtime control changes by itself.
