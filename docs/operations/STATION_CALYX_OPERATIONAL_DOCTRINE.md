---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Station Calyx Operational Doctrine

**Version:** 2026-02-27
**Scope:** Governed mode
**Applies to:** Sunrise, Contract, Intake, API, Ingest, Secrets

---

## 0. Purpose

Station Calyx exists to convert human intent into safe, governed execution.
This doctrine defines the operational invariants that must hold at runtime.

This is not a feature document.
This is a behavioral contract between the system and its operator.

---

## 1. Foundational Principles

### 1.1 Contract is Authority

CALYX_CONTRACT.yaml defines allowed tasks, sources, and execution policy.

The contract hash (contract_sha256) must match its canonical serialization.

If integrity fails, the system halts.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Doctrine Rule:** If the contract is invalid, nothing governed executes.

### 1.2 Intake Must Derive From Contract

Discord intake does not maintain independent allowlists.

Allowlists are loaded from the contract.

Parity is enforced by tests.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Doctrine Rule:** No policy may exist in two places.

### 1.3 Loopback By Default

API binds to 127.0.0.1 by default.

Public bind requires explicit override.

Override emits audit.runtime.network.bind_override.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Doctrine Rule:** Exposure is opt-in, never default.

### 1.4 Ingest Must Resolve Deterministically

Repo root resolution uses resolve_repo_root().

If root cannot be determined, ingest fails closed.

Emits audit.ingest.repo_root.unresolved.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Doctrine Rule:** Ambiguity is an error state, not a fallback.

### 1.5 Secrets Do Not Persist Unnecessarily

DISCORD_BOT_TOKEN is not written to openclaw.json.

Secrets must be sourced from environment or controlled secret stores.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Doctrine Rule:** Secrets belong to environment, not versioned config.

---

## 2. Sunrise Doctrine

Sunrise is the canonical boot path.

**Order:**

1. External emitter gate
2. Contract integrity load
3. Core services start
4. Station health loop start (background; live CPU/RAM/GPU for STATE and heartbeats)
5. Navigator + Triage loop start (background; ship's wheel + medical unit; CBO gates on pause)
6. Energy Churn + CP9 loop start (background; trend analysis and tuning recommendations)
7. CP6 + CP7 loop start (background; harmony and drift; Phase 3)
8. Discord Gateway start
9. audit_health verification
10. Receipt issuance

**If any step fails:**

- Sunrise fails closed.
- System does not report healthy.
- There is no secondary boot path.

### 2.1 Sunset–Sunrise Parity

Every sunset is as important as a sunrise.

- **Sunset** — Prepare for rest: stop loops cleanly, preserve state, leave resumable.
- **Sunrise** — Verify continuity, then proceed with creation: preflight, gate, validate, receipt.

Both halves of the cycle matter. A rushed sunset leaves bad state for sunrise. A sunrise that skips verification can build on a broken base.

### 2.2 Refinement Over Restart

Restarting services is trivial. The leverage is in the mechanisms that refine them — loops, feedback paths, continuity. Maximize each sunrise performance gain by maintaining and evolving those refinement mechanisms, not just restarting processes.

---

## 3. Audit Doctrine

The audit layer is not optional telemetry.
It is the truth source.

The system must be able to answer:

- Which contract version is active?
- What is its hash?
- Which tasks are allowed?
- Which intake source authorized this execution?
- Was network exposure explicit?
- Was any ingest ambiguous?
- Were any secrets persisted improperly?

If the audit layer cannot answer these, the system is not in governed state.

---

## 4. Phase Discipline

CALYX_CONTRACT_PHASE controls operational strictness.

- **phase_a** → strict source allowlist
- **phase_b** → broader allowance

**Doctrine Rule:** Phase selection must be intentional. Defaults must reflect actual operating reality.

If the system is Discord-only governed ingress, default should match that reality.

---

### 4.1 Safe Travels (50% CPU Target)

**Purpose:** Preserve hardware life; balance above and below 50% CPU. Station Calyx shoots for 50% at all times by committing more activities to ML when under target and holding back when over.

**Target:** 50% CPU. Zone: 40–60% = safe_travels. Under 40% = allow ML. Over 60% = hold back. Over 75% = pause.

**Mechanism:** station_health_loop emits `cpu_target` (under | safe_travels | over), `safe_travels_zone`, `cadence_55`. Navigator reads these; CBO gates on pause when over. Heartbeats include cpu_target.

**Doctrine Rule:** Dancing above and below the 50% line focuses on preserving hardware life. Quality of outputs improves when the Station operates in the Safe Travels zone.

**Evidence:** docs/HARDWARE_OPTIMIZATION.md, Scripts/station_health_loop.ps1, Scripts/navigator.ps1

---

## 5. Integrity Evolution

Contract changes must:

- Be intentional.
- Be hashed.
- Be reproducible.
- Be attributable.

**Current mechanism:** Scripts/update_contract_hash.py recomputes contract_sha256.

**Evidence:** WO_GOVERNANCE_CONTRACT_INTAKE_PARITY_AND_LOOPBACK_HARDENING_V1_VALIDATION_2026-02-27.md

**Future mechanism (next phase):** Contract change receipts (who, when, why, diff, resulting hash).

Chronology is not bureaucracy. It is evolutionary memory.

---

## 6. Failure Doctrine

The system must fail closed under:

- Contract integrity failure
- Intake/contract parity mismatch
- Unresolved repo root
- Unauthorized network exposure
- Missing required secrets
- External emitter detection

A "healthy" report while in violation is unacceptable.

---

## 7. Operational Guarantees

If this doctrine holds, then:

- Governance claims are real, not symbolic.
- Audit receipts are trustworthy.
- Network posture is predictable.
- Execution policy cannot silently drift.
- You, the architect, remain sovereign and accountable.

---

## 8. What This Does Not Yet Guarantee

- Human approval token is still auto-approved (intentional, temporary).
- Contract changes are not yet receipt-tracked (next step).
- OpenClaw is disabled but not fully erased (gated, not absorbed). OpenClaw helped bring Station Calyx to fruition; it is remembered. Significant work remains before testing can be considered again.

Those are known edges, not hidden weaknesses.

---

## 9. Closing Principle

Station Calyx must never rely on:

- Memory
- Assumptions
- Manual discipline
- "It should be fine"

It must rely on:

- Deterministic enforcement
- Canonical receipts
- Explicit configuration
- Verifiable invariants
