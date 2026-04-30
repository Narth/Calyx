---
status: active
owner: station
last_reviewed_utc: "2026-04-10"
doctrine_scope: governed
---

# WO_OPERATOR_INTERVENTION_PROTOCOL_V1

## Purpose

Define a governed, manual, receipt-backed operator intervention protocol for Station Calyx runtime so the operator can act under load or anomaly without sacrificing attribution, auditability, or safety.

## Status

Planning and staging-implementation definition only.

This work order does not authorize autonomous intervention, silent runtime correction, or blind process control.

## Scope

This work order governs:

- manual operator intervention tiers
- required intervention receipts
- evidence references to runtime capture, classification, and summary artifacts
- safety constraints for process-targeted intervention
- compatibility with existing runtime governance and operator visibility surfaces

This work order applies to:

- runtime capture artifacts
- runtime governance bundles
- runtime operator summary artifacts
- staging-only intervention schemas, fixtures, and validation surfaces

This work order does not:

- authorize automated intervention
- authorize self-correction by Station
- authorize hidden restarts or silent process termination
- redefine existing multiplicity, health, or bridge governance

## Background

Recent runtime observation work established:

- read-only capture of real workstation state
- governed multiplicity and topology classification
- operator-facing summaries that separate:
  - workstation load
  - Station-governed runtime posture
  - attribution and compliance gaps

That visibility creates a new governance need:

When the operator decides to act, the action must remain:

- intentional
- attributable
- reconstructable

The protocol target is therefore not "make intervention easy."

It is "make intervention manual, explicit, and reviewable."

## Core Principles

### The Operator Remains the Final Authority

Intervention authority originates from the operator.

The system may record and structure intervention.

It may not initiate intervention on its own.

### Observation Before Intervention

Intervention should follow review of current evidence, not intuition alone.

At minimum, operator action should be grounded in:

- runtime capture
- runtime classification
- runtime operator summary

### Receipt Before Forgetting

If an intervention is not recorded, later review loses the chain between:

- observed anomaly
- decision
- action

### No Blind Manual Disruption

Human intervention is allowed.

Blind intervention is not legitimate merely because it is human.

The protocol must discourage:

- killing all Python or Node processes
- terminating protected system processes without high confidence
- acting without written reasoning

### Classification Before Action

The intervention pathway should preserve the existing governance order:

- observe
- classify
- decide
- act
- record

## Intervention Tiers

### Tier 0 — Observe

- operator reviewed evidence and chose not to intervene
- no runtime mutation
- optional receipt when the observation should remain reviewable

### Tier 1 — Soft Intervention

- targeted, bounded manual action against a specific process or narrow set of processes
- acceptable examples:
  - terminate a duplicate script instance
  - stop a non-canonical runtime surface
  - inspect a suspicious process and record the command used
- unacceptable examples:
  - broad kill patterns against unknown runtime classes
  - unbounded process-family shutdown without precise target evidence

### Tier 2 — Hard Intervention

- broader action taken when load remains elevated, causation is unclear, or operator confidence has materially degraded
- acceptable examples:
  - stop multiple Station services
  - halt Station activity
  - restart the workstation

## Required Decision Framework

Before intervention, the operator should explicitly consider:

- Is system load elevated?
- Is the load attributable to Station processes?
- Is governance compliant?
- Is the behavior expected?

## Required Receipt

Each intervention should be representable as:

- `runtime.operator.intervention`

Required fields should include:

- timestamp
- intervention tier
- triggering conditions
- observed evidence references
- relevant processes
- action taken
- commands executed
- operator reasoning

## Safety Constraints

The protocol must preserve explicit friction around protected system surfaces.

Protected examples include:

- `System`
- `Client Server Runtime Process`
- Windows Management Instrumentation surfaces

The protocol should also reject obviously blind intervention patterns such as:

- terminating all Python processes by image name
- terminating all Node processes by image name
- broad wildcard process-family kills without explicit PID targeting

## Validation Expectations

Any staging implementation shaped by this work order should validate at minimum:

- observe-only receipt with no action
- targeted duplicate-process intervention
- targeted non-canonical runtime intervention
- hard intervention with broader scope
- protected-process safety friction
- rejection of blind kill commands
- deterministic receipt generation from the same evidence and operator input

## Constraints

Hard constraints:

- no autonomous intervention
- no hidden restarts
- no silent process termination
- no receipt-less manual intervention pathway in the staging protocol design
- no intervention receipt that invents evidence not present in upstream artifacts

## Desired Outcome

When the system looks wrong, the operator has a governed answer to:

"What is the safe way to act?"

That answer should remain:

- manual
- visible
- receipt-backed
- and clearly attributable to human authority rather than Station autonomy.
