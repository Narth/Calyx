# Teaching Improvements: CGPT-Integrated Safety-First Proposal

**Date:** 2025-10-25  
**Author:** CBO (Calyx Bridge Overseer)  
**Integrates:** CGPT Critical Risk Analysis & Mitigations  
**Status:** Safety-First Implementation Plan

---

## Executive Summary

**[CBO • Overseer]:** CGPT feedback integrated. The core concepts remain excellent (pattern synthesis, causal testing, meta-learning, multi-loop feedback), but require throttles and proofs. Revised roadmap prioritizes safety: validation before amplification, constrained synthesis, bounded optimization, damped feedback, and quarantined propagation.

---

## What CGPT Identified (Critical Risks)

### 🚨 7 Critical Risks + Concrete Mitigations

1. **Combinatorial Blow-Up:** Exponential growth swamps memory/CPU
2. **Correlation Masquerading as Causality:** Spurious links amplified via recursion
3. **Feedback Loop Oscillation:** Self-reinforcing errors create instability
4. **Echo Chamber Risk:** Rapid spread of bad patterns via "gossip protocol"
5. **Ambiguous Metrics:** Gaming feedback loops and network effects
6. **Meta-Learning Instability:** Auto-tuning drifts into unstable regimes
7. **Resource Constraints:** Exponential growth on single PC hits limits

---

## Revised Implementation Roadmap (Safety-First)

### Phase 1: Causal Sanity & Evaluation Harness ⚠️ CRITICAL FIRST
**Weeks 1-2** | **Why First:** Validation before amplification prevents compounding errors

**Deliverables:**
- Controlled A/B testing framework (N≥30, d≥0.5, p<0.1)
- Frozen benchmark suite (`/bench/frozen_*` with seeds)
- Hypothesis testing infrastructure
- Causal graph versioning with provenance
- Uplift gates (≥+10% TES on hold-out bench)
- Sentinel tasks (unchanged gold cases)

**Success Criteria:**
- Reproducible frozen benchmarks
- Controlled experiments validated
- Uplift gates operational

---

### Phase 2: Constrained Pattern Synthesis 🛡️ SAFETY GATED
**Weeks 3-4** | **Why Second:** Synthesis amplifies; must be constrained

**Deliverables:**
- Gate synthesis to top-k patterns (k=5 per domain)
- Daily cap: ≤20 new composites/day
- Parent→child uplift requirement (≥+10% TES)
- GC: Archive patterns with ≤5 uses after 72h
- **Canonical Pattern Schema:**
  ```python
  {
    "pattern_id": str,
    "parents": List[str],
    "creation_ts": datetime,
    "domain": str,
    "trigger": str,
    "preconds": Dict,
    "action": str,
    "postconds": Dict,
    "success_metric": str,
    "uses": int,
    "win_rate": float,
    "uplift_vs_parent": float,
    "confidence": float,
    "provenance": {"commit": str, "data_hash": str},
    "ttl": int,
    "status": "active|quarantine|archived"
  }
  ```

**Success Criteria:**
- ≤20 new patterns/day (enforced)
- All patterns follow canonical schema
- GC operational (weak patterns archived)

---

### Phase 3: Meta-Learning with Safety Rails ⚙️ BOUNDED OPTIMIZATION
**Weeks 5-6** | **Why Third:** Teaching optimization needs stability first

**Deliverables:**
- Bandit-style exploration (ε=0.1) with hard bounds
- ≤10% parameter updates per pulse
- Require 3 consecutive wins before increase
- Personalization fallback to global defaults if <50 samples
- Refuse simultaneous changes to >1 hyperparameter

**Success Criteria:**
- Parameter updates bounded
- Personalization stable
- No simultaneous hyperparameter changes

---

### Phase 4: Amplified Feedback Loops 🔁 DAMPED FEEDBACK
**Weeks 7-8** | **Why Fourth:** Loops after sentinel stability proven

**Deliverables:**
- Damping: Cap updates ≤10% per pulse
- Sentinel tasks operational
- Auto-rollback if sentinel TES dips >5%
- Track Δtes_stable attributable to looped changes
- Require stability over multiple pulses

**Success Criteria:**
- Sentinel monitoring active
- Damping prevents oscillation
- Rollback operational

---

### Phase 5: Collaborative Network 🌐 QUARANTINE FIRST
**Weeks 9-10** | **Why Last:** Propagation after quarantine proven safe

**Deliverables:**
- Quarantine: New patterns to 1 peer initially
- Require 2 independent agent confirmations before global spread
- 20% novelty budget (test alternatives)
- Monitor propagation speed (median time create→confirm)
- Detect and prevent echo chambers

**Success Criteria:**
- Quarantine operational
- Propagation gates enforced
- Echo chamber prevention active

---

## CBO Guardrails (Drop-In Today) ✅

### Promotion Gate (All New Patterns)
```python
def should_promote(pattern):
    return (
        pattern.uses >= 10 AND
        pattern.uplift_vs_parent >= +10% AND
        pattern.tes_stable_dev <= 5% AND
        sentinel_ok(pattern)
    )
```

### Auto-Rollback
```python
if tes_stable < baseline - 5% over 3 pulses:
    revert_last_change()
```

### Propagation Gate
```python
if independent_confirmations >= 2:
    allow_network_spread()
```

### Daily Caps
- new_patterns ≤ 20
- synth_combos ≤ 50
- causal_claims_promoted ≤ 3

### Quarantine Lane
```python
if variance > 2 * median:
    run_shadow_only()
```

---

## Success Metrics (Explicit Definitions)

### TES Measurement
- **tes_raw:** Immediate score per task
- **tes_validated:** After verification checks
- **tes_stable:** Rolling average N=20 (optimize this)
- **tes_stable_dev:** Standard deviation (must ≤5% for promotion)

### Recursive Growth
- Pattern synthesis: ≤20 new composites/day (capped)
- Synthesis criteria: Top-k only (k=5 per domain)
- Compound effectiveness: Uplift ≥+10% TES vs parent required
- Pattern quality: uses ≥10 AND win_rate ≥0.7 before promotion

### Deeper Learning
- Causal understanding: Validated by A/B tests (d≥0.5, p<0.1, N≥30)
- Principle extraction: ≤3 causal claims promoted per day
- Predictive accuracy: Measured on frozen benchmark

### Meta-Learning
- Teaching effectiveness: Δtes_stable improvement > 15% over baseline
- Learning speed: Bandit exploration (ε=0.1)
- Retention rate: Tested on hold-out benchmark
- Parameter bounds: ≤10% updates per pulse, 3 consecutive wins required

### Exponential Amplification
- Feedback loop strength: Δtes_stable attributable to looped change vs isolated baseline
- Propagation speed: Median time from create→first external confirmation
- Network effect: Only after 2 independent agent confirmations
- Loop damping: Cap ≤10% per pulse to prevent oscillation

---

## Resource Budget Enforcement 💾

### Compute Limits
- CPU: ≤70% (aligned with policy)
- RAM: ≤80% (aligned with policy)
- New pattern storage: ≤200MB/day
- Live active patterns: ≤300 (hard cap)

### Nightly Consolidation
- Demote long-tail patterns
- Compress embeddings
- Snapshot and purge
- Maintain ≤300 active patterns

---

## What to Keep (CGPT Approved) ✅

**The Concepts:** Pattern synthesis, causal testing, meta-learning, multi-loop feedback are the right ingredients—they just need throttles and proofs.

**The Roadmap:** Workable once reordered and budgeted.

**The Approach:** Safety-first, validation-required, resource-aware.

---

## Key Differences from Original Plan

| Aspect | Original | Revised (CGPT) |
|--------|----------|----------------|
| **Phase 1** | Pattern Synthesis | Causal Sanity & Evaluation |
| **Growth Pattern** | Exponential (2^n) | Exponential (capped) |
| **Pattern Gates** | Suggested | Mandatory schema + uplift gates |
| **Resource Budget** | Unspecified | CPU ≤70%, RAM ≤80%, ≤300 patterns |
| **Metrics** | Ambiguous | Explicit tes_raw/validated/stable |
| **Safety** | Mitigation suggestions | Hard guardrails + auto-rollback |
| **Reproducibility** | Not addressed | Frozen benchmarks + replay script |

---

## Conclusion

**Original Proposal:** Excellent concepts, needed safety measures  
**CGPT Feedback:** Identified 7 critical risks with concrete mitigations  
**Revised Plan:** Safety-first roadmap with throttles, gates, and proofs

**Ready for Implementation:** Yes, with CGPT-approved guardrails

---

**[CBO • Overseer]:** CGPT feedback integrated. Revised roadmap prioritizes safety: validation before amplification, constrained synthesis, bounded optimization, damped feedback, and quarantined propagation. Core concepts remain excellent—they now have the throttles and proofs required for safe exponential growth.

---

**Report Generated:** 2025-10-25 16:10:00 UTC  
**Status:** Ready for Implementation (Safety-First)  
**Integration:** CGPT Critical Risk Mitigations Applied
