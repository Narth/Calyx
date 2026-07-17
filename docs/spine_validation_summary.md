# Spine Validation Summary

**Directive:** Canonical Spine Validation, Simulation & Hardening  
**Date:** 2026-02-17  
**Status:** Complete

---

## Objective

Validate and harden the runtime spine under adversarial and race conditions:

**Calyx Mail → Intent Artifact → Work Envelope → Contract Gate → Execution → Receipts**

---

## Invariants Validated

| Invariant | Result | Evidence |
|-----------|--------|----------|
| All inbound communication becomes a Calyx Mail Envelope | **Held** | Discord/CLI adapters → router → mail_inbox only |
| Only CBO mints Work Envelopes | **Held** | hub_runner verifies intent status "minted" and hash match; direct work_outbox inject denied |
| All execution passes through contract validation | **Held** | validate_work_envelope before handler; unknown task_type and high_risk without approval denied |
| Every execution produces a receipt | **Held** | append_receipt_line on allow/deny/fail |
| Archived code cannot be imported | **Held** | CI check_spine_invariants fails on archive/station_calyx imports |
| BloomOS does not create reverse dependency into Calyx | **Held** | No bloomos imports in calyx/kernel or calyx/execution |

---

## Phase A — Mail Security & Transport Integrity

- **A1 Signature:** Ingest path accepts structured JSON from allowlisted adapters. Full Calyx Mail v0.1 signature verification is optional when keys are provisioned; not enforced on current adapter payloads.
- **A2 Replay:** Replay ledger implemented (`ingest_ledger.py`). Second submission of same `envelope_id` rejected; rejection receipt written; ledger persists across restarts.
- **A3 Ingest path:** Direct write to work_outbox without CBO mint denied. hub_runner verifies CBO mint via intent artifact status and hash.

**Fixes applied:** Replay ledger, atomic write in router and plan mint, CBO-mint verification in hub_runner.

---

## Phase B — Outbound Delivery Integrity

- Outbound path (CBO → Mail Envelope → outbox → adapter → Discord) not fully implemented. Clarification requests and execution results would be sent via future outbound router. Human testing required only for live Discord send.

---

## Phase C — Intent Pipeline Validation

- **C2 Determinism:** Same Work Envelope canonical input → identical deterministic hash. No timestamp/random in hashed fields.

---

## Phase D — Execution & Contract Hardening

- **D1:** Unknown task_type and high risk without approval token denied; reasons reference contract.
- **D2 Approval token:** Token not yet cryptographically bound to envelope hash + expiry. Documented as future hardening; patch_small checks presence only.

---

## Phase E — Metrics

- `runtime/metrics/spine_validation.json` populated from simulations: parse_success_rate, replay_rejection_rate, contract_deny_rate_distribution, containment_anomalies, determinism_hash_stability.

---

## Phase F — CI & Invariant Penetration

- Spine invariant script fails on import from archive or station_calyx; fails on undocumented top-level directories. Scoped to calyx, tools, benchmarks, station_calyx, scripts.

---

## BloomOS Boundary

- Scan: no import from bloomos/ into calyx/kernel or calyx/execution. Dependency direction confirmed: BloomOS may depend on Calyx; Calyx does not depend on BloomOS.

---

## Deliverables

| Deliverable | Path |
|-------------|------|
| Mail security | `runtime/receipts/spine_validation_mail_security.json` |
| Intent pipeline | `runtime/receipts/spine_validation_intent_pipeline.json` |
| Execution contract | `runtime/receipts/spine_validation_execution_contract.json` |
| Atomic I/O | `runtime/receipts/spine_validation_atomic_io.json` |
| Metrics | `runtime/receipts/spine_validation_metrics.json` |
| Dependency graph | `runtime/receipts/spine_validation_dependency_graph.json` |
| Summary | `docs/spine_validation_summary.md` |
| Report | `runtime/receipts/spine_validation_report.json` |

---

## Unresolved Risks

1. **A1:** Full signature verification on ingest when Calyx Mail v0.1 keys are provisioned.
2. **D2:** Approval token cryptographically bound to envelope hash + expiry + signer.
3. **Stress:** 20–100 concurrent envelope / atomic I/O stress test recommended as nightly or CI.

---

## Stop Conditions

None triggered. No execution bypass, no mail ingress bypass, determinism stable, replay protection in place, contract enforcement validated.
