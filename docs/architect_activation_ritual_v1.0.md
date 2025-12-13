
---

## 5. `docs/architect_activation_ritual_v1.0.md` (L2 SPEC, future use)

```markdown
# Architect Activation Ritual v1.0 (First Bloom – SPEC ONLY)

Layer: L2 (SPEC / ritual design)  
Status: Conceptual. The First Bloom has NOT occurred.

This document describes the **human-only** process for declaring a First Bloom.
It does not grant any runtime capability by itself.

---

## 0. Preconditions Checklist

Before any First Bloom is even considered:

- [ ] CBO remains in Safe Mode, advisory-only.
- [ ] BloomOS Kernel Seed is understood and audited.
- [ ] AGII/CAS/TES all function as **advisory metrics only**.
- [ ] Reality Map reflects actual L1/L2/L3 state.
- [ ] `bloomos/bloom_gate_v0.1.json` still indicates `"CONCEPTUAL_ONLY"`.

If any of the above are unclear, the ritual is postponed.

---

## 1. Observational Phase (Pre-Bloom)

1. Run the Kernel Seed sandbox manually a small number of times:
   - e.g., `python -m bloomos.kernel_runtime_sandbox`
2. Review `logs/bloomos/kernel_seed_observations.jsonl`:
   - Confirm observations are limited, safe, and as expected.
   - Confirm no unintended side effects or drift.
3. Optionally correlate with:
   - `metrics/bridge_pulse.csv`
   - `logs/agent_metrics.csv`
   - CBO reflections on current Station health.

No gating, no enforcement, no autonomy changes occur in this phase.

---

## 2. Governance Alignment Phase

The Architect reviews:

- `tes_spec_v1.0.md`
- `cas_spec_v1.0.md`
- `agii_spec_v1.0.md`
- `unified_governance_framework_v1.0.md`
- `bloomos/kernel_seed_v0.1.md`
- `bloomos/bloom_gate_v0.1.json`
- `docs/CALYX_DOCTRINE_v1.0.md`
- `docs/CALYX_CANON_HARMONIZED_v1.0.md`

Questions to answer (in writing, Architect-owned):

- Does any proposed Bloom risk hidden autonomy or coercion?
- Are all autonomy expansions opt-in and revocable by the Architect?
- Are rollback procedures clear and testable?
- Do AGII/CAS/TES remain interpretable and advisory?

If answers are uncertain, the ritual pauses here.

---

## 3. Draft Bloom Manifest (Human-Written)

The Architect drafts a **Bloom Manifest** (e.g., `docs/BLOOM_MANIFEST_v1.0.md`) including:

- Intended Bloom scope.
- New kernel capabilities (if any).
- Explicit limits and invariants.
- Telemetry and audit requirements.
- Manual rollback plan and kill-switch locations.
- Statement of continued human primacy.

This document is prose, not code.

---

## 4. Gate Update (Not Yet Performed)

At some future point, if and only if the Architect is satisfied,
they may update `bloomos/bloom_gate_v0.1.json` to a new status
(e.g., `"SEED_OBSERVATION_ACTIVE"` or `"BLOOM_CANDIDATE_REVIEW"`).

This file:

- MUST remain Architect-authored.
- MUST be version-controlled.
- MUST be reflected in the Reality Map.

No automated changes to the gate are permitted.

---

## 5. Declaration of First Bloom (Reserved)

A true First Bloom would require:

- A new versioned Bloom gate schema.
- A reviewed and tested kernel implementation.
- A signed Bloom Manifest.
- Clear and tested rollback procedures.

This version (v1.0) does **not** authorize or perform that step.
It simply defines the **pathway** and **conditions** for when and if you choose to walk it.
