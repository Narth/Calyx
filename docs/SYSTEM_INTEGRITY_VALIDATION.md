# System Integrity Validation

**Version:** 1.0  
**Status:** Institutional (non-negotiable)  
**Authority:** CBO Directive — Canonical Spine Security

---

## 1. Purpose

Every action within Station Calyx must be preceded by a **system integrity validation check**. No spine operation may proceed unless:

1. All spine components respond and are reachable (pulse check).
2. The station is operating against a single canonical process (no split coordination).
3. If any component fails to respond, report, or confirm a pulse → **assume all tasks will fail** and block.

This prevents:
- Changes occurring in isolation or non-parallel with system goals/intents.
- Mail transports being lost or pulled through multiple coordinators (e.g. one message → three envelopes).
- Benign tasks proceeding when the system is in an inconsistent state.

---

## 2. Fail-Closed Policy

**If the integrity gate fails, no operation proceeds.** Even the most trivial task is blocked. Rationale: a broken spine component means execution results may be lost, receipts may not be written, or mail may be duplicated/corrupted. Proceeding would violate spine invariants.

---

## 3. Component Pulse Check

Before any spine operation, the following must succeed:

| Component | Check | Failure Mode |
|-----------|-------|--------------|
| Mail inbox | Path exists, writable | Mail cannot be delivered; reject delivery |
| Intent artifacts dir | Path exists, writable | Intent pipeline cannot persist; reject ingest |
| Replay ledger | Path reachable, appendable | Replay protection degraded; reject |
| Contract | CALYX_CONTRACT.yaml loads | Execution validation impossible; reject |
| Receipts dir | Path exists, writable | Execution cannot be receipted; reject |
| Work outbox (execution path only) | Path exists, readable | Cannot process Work Envelopes; reject |

Any single failure → gate closed → no operation.

---

## 4. Single Coordinator Lease (Implemented)

**Operational policy:** Only one coordinator process may perform spine operations at a time. Multiple Cursor/agent sessions (or multiple bot instances) cause one message → three envelopes. Mitigations:

1. **Coordinator lease:** An exclusive file lock on `runtime/cbo/.coordinator_lease` is acquired before every spine operation (mail delivery, intent ingest, execution). Only one process may hold it; others fail the integrity gate and do not proceed. Prevents triple-processing when multiple terminal sessions run the bot.
2. **Message-level deduplication** (intake): Before creating an envelope, check `(message_id, channel_id)` — if already seen, skip. Implemented in Discord intake.
3. **Envelope-level replay** (router): Same `envelope_id` rejected via ingest ledger. Implemented.

**Disable lease:** Set `CALYX_COORDINATOR_LEASE=0` (e.g. for multi-node or tests). Default: enabled.

---

## 5. Entry Points

The integrity gate must be invoked **before**:

| Entry point | Location | Gate invocation |
|-------------|----------|-----------------|
| Mail delivery | `calyx.mail.router.deliver_to_cbo_ingest` | At start; fail → return None |
| Intent ingest | `calyx.cbo.intent_pipeline.ingest.ingest_mail_envelope` | At start; fail → return None |
| Work execution | `calyx.execution.hub_runner.run_work_envelope` | At start; fail → deny with reason |
| Work outbox processing | `calyx.execution.hub_runner.process_work_outbox` | At start; fail → return zero counts |
| Discord intake | `calyx.cbo.discord_intake.process_message` | Before delivery; fail → return (False, "integrity_failed", None) |

---

## 6. Bypass (Tests Only)

For CI/tests that use ephemeral runtime dirs, the gate may be bypassed via:

- `CALYX_SKIP_INTEGRITY_GATE=1` (env)  
- Or `skip_integrity_gate=True` (param where supported)

Production and local runs **must not** bypass the gate.

---

## 7. References

- **Spine:** `docs/SPINE.md`
- **ADR:** `docs/ARCHITECTURE_DECISIONS/ADR-0001-canonical-spine.md`
- **Implementation:** `calyx/kernel/integrity_gate.py`

---

*Part of the institutional spine. Changes require Architect/CBO directive.*
