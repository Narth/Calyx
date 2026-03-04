# ADR-0001: Canonical Runtime Spine

**Status:** Accepted  
**Date:** 2026-02-17  
**Deciders:** Architect / CBO Directive  
**Context:** Institutionalization of Station Calyx canonical runtime spine and repo reorganization.

---

## Context

Station Calyx had multiple ingress paths (Discord writing directly to intent outbox, coordinator pipeline depending on missing `station_calyx.core`), fragmented envelope types (Mail vs Intent vs execution), and no single authority for minting executable work. This led to:

- Execution possible without consistent contract validation
- Raw payloads interpreted by subsystems
- Broken imports and legacy drift

A directive was issued to establish a single canonical spine and eliminate fragmentation.

---

## Decision

We adopt a **single canonical runtime spine**:

```
Calyx Mail → Intent Artifact → Work Envelope → Contract Gate → Execution → Receipts
```

- **All inbound communication** becomes a **Calyx Mail Envelope** first. No subsystem may directly interpret Discord/CLI payloads.
- **Only CBO** may mint **Work Envelopes**. Workers execute Work Envelopes only.
- **All execution** passes through **Contract** validation (deny-by-default).
- **Every execution** produces a **canonical, schema-validated receipt**.
- **Non-operational or broken** modules are **migrated** into the spine or **moved to `/archive/`** and marked non-operational. CI fails on imports of missing namespaces (e.g. `station_calyx.core`) unless the importer is under `/archive/`.

Supporting structural decisions:

- **Kernel** under `calyx/kernel/`: envelope, contract, receipts, toolsurface, paths — minimal, no transport or execution logic.
- **Calyx Mail** as sole transport; **adapters** (Discord, CLI) convert raw input to Mail Envelopes and route through CBO ingest only.
- **Intent pipeline** under `calyx/cbo/intent_pipeline/` with persisted artifacts under `runtime/cbo/intents/<intent_id>/`.
- **Execution** under `calyx/execution/` (hub_runner, task_handlers); initial task types: `repo_readonly_review`, `test_run_safe`, `patch_small`.
- **BloomOS** remains conceptual; spec-only materials under `bloomos/specs/`. BloomOS may depend on Calyx; Calyx must not depend on BloomOS.
- **New top-level directories** must be documented in `docs/INDEX.md` or CI fails.

---

## Consequences

- **Positive:** Single path for all execution; clear authority (CBO) for work minting; contract and receipts enforced; no raw-payload interpretation; legacy isolated in archive.
- **Negative:** Migration effort; Discord and other adapters must be refactored to emit Mail Envelopes and go through ingest; coordinator code that depended on `station_calyx.core` must be migrated or archived.
- **Risks:** Phase-by-phase rollout required; invariants must be validated at each phase; stop conditions (e.g. execution outside Work Envelope, raw Discord bypass) must trigger escalation.

---

## References

- `docs/SPINE.md` — Canonical object flow and definitions
- CBO Directive: Institutionalize Canonical Spine & Repo Reorganization
- `CALYX_CONTRACT.yaml` — Contract and tool surface
