# Station Calyx Canonical Runtime Spine

**Version:** 1.0  
**Status:** Institutional (non-negotiable)  
**Authority:** CBO Directive — Canonical Spine & Repo Reorganization

---

## 1. Canonical Object Flow

All ingress, coordination, and execution conform to this path. No execution may occur outside it.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌────────────────┐     ┌─────────────┐     ┌───────────┐
│  Calyx Mail     │────▶│  Intent Artifact │────▶│  Work Envelope │────▶│  Contract Gate │────▶│  Execution  │────▶│  Receipts  │
│  Envelope       │     │  (ingest/clarify)│     │  (CBO-minted)   │     │  (allow/deny)   │     │  (workers)  │     │ (canonical)│
└─────────────────┘     └──────────────────┘     └─────────────────┘     └────────────────┘     └─────────────┘     └───────────┘
       │                            │                        │                       │                      │
       │  Sole transport layer      │  Persisted under       │  Only CBO mints       │  Deny-by-default     │  Every execution
       │  for all inbound comms      │  runtime/cbo/intents/  │  Work Envelopes      │  Contract validation │  produces receipt
       └────────────────────────────┴────────────────────────┴───────────────────────┴──────────────────────┘
```

**Flow summary:**

1. **Calyx Mail Envelope** — All inbound communication (Discord, CLI, future transports) becomes a Mail Envelope first. No subsystem may directly interpret raw Discord/CLI payloads.
2. **Intent Artifact** — Mail Envelope is ingested; if clarity is insufficient, clarification is requested via Calyx Mail. Artifact is persisted under `runtime/cbo/intents/<intent_id>/`.
3. **Work Envelope** — Only CBO mints Work Envelopes from clarified Intent Artifacts. Workers never execute raw user intent.
4. **Contract Gate** — Every Work Envelope is validated against CALYX_CONTRACT. Deny-by-default. No execution without allow.
5. **Execution** — Workers execute Work Envelopes only, within the allowlisted tool surface.
6. **Receipts** — Every execution produces a canonical, schema-validated receipt.

---

## 2. Definitions

### Mail Envelope

- **Definition:** The canonical transport object for all inbound communication. Produced by Calyx Mail (codec, crypto, mailbox). May be encrypted/signed per Calyx Mail v0.1.
- **Content:** Opaque to execution; carries sender, recipient, message ID, timestamp, optional subject, and payload (plaintext or ciphertext).
- **Authority:** Created by mail adapters (e.g. Discord adapter, CLI adapter) from raw input. No execution logic interprets Mail Envelope content directly for dispatch.

### Intent Artifact

- **Definition:** A persisted representation of user intent, derived from a Mail Envelope via CBO ingest. May require clarification before it can become a Work Envelope.
- **Location:** `runtime/cbo/intents/<intent_id>/` with `intent.json`, `clarifications.json`, `plan.json`, `status.json`, `receipts/`.
- **Authority:** Created and updated only by CBO intent pipeline (ingest → clarify → score → plan). No direct conversion from Mail Envelope to Work Envelope without Intent Artifact persistence.

### Work Envelope

- **Definition:** The only envelope type that may trigger execution. Contains task_type, scope, constraints, and deterministic hash. Minted solely by CBO from a clarified Intent Artifact.
- **Authority:** Only CBO may mint Work Envelopes. Workers consume Work Envelopes only.
- **Validation:** Must pass Contract Gate (CALYX_CONTRACT.yaml) before execution.

### Receipt

- **Definition:** A canonical, schema-validated record of an execution (or denial). Written to runtime/receipts/ (or task-specific receipt paths). Every execution produces at least one receipt.
- **Authority:** Emitted by kernel receipt writer; schema enforced. No execution is considered complete without a receipt.

---

## 3. Core Invariants (Non-Negotiable)

1. **All inbound communication becomes a Calyx Mail Envelope first.**  
   No subsystem may directly interpret Discord/CLI payloads.

2. **Only CBO may mint Work Envelopes.**  
   Workers execute Work Envelopes only; workers never execute raw user intent.

3. **All execution passes through Contract validation.**  
   Deny-by-default remains enforced.

4. **Every execution produces a receipt.**  
   Receipts must be canonicalized and schema-validated.

5. **Non-operational or broken modules must be migrated into the new spine or moved to `/archive/` and clearly marked as non-operational.**  
   No active code path may depend on archived or missing namespaces (e.g. `station_calyx.core`) unless the importer is under `/archive/`.

6. **System integrity validation runs before every spine action.**  
   If any component fails pulse check (mail inbox, intent artifacts, replay ledger, contract, receipts), no operation proceeds. See `docs/SYSTEM_INTEGRITY_VALIDATION.md`.

---

## 4. References

- **Contract:** `CALYX_CONTRACT.yaml`
- **Kernel:** `calyx/kernel/` (envelope, contract, receipts, toolsurface, paths)
- **Mail:** `calyx/mail/` (codec, crypto, mailbox, router) and `calyx/mail/adapters/`
- **Intent pipeline:** `calyx/cbo/intent_pipeline/`
- **Execution:** `calyx/execution/` (hub_runner, task_handlers)
- **ADR:** `docs/ARCHITECTURE_DECISIONS/ADR-0001-canonical-spine.md`
- **System integrity:** `docs/SYSTEM_INTEGRITY_VALIDATION.md`

---

*This document is part of the institutional spine. Changes require Architect/CBO directive.*
