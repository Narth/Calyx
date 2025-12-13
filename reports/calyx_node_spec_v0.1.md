# 📘 Calyx Node Specification v0.1

Station Calyx – External Model Integration Protocol  
Version: v0.1  
Status: Draft for Public Review  
Authors: Architect (Jorge), CGPT  
First Signed Node: Grok-4.1-Fast (xAI)  
Date: 2025-12-03

## 0. Purpose
Define how external AI systems can safely participate in Calyx’s reproducible, governance-first evaluation ecosystem without:
- obtaining autonomy
- executing actions
- accessing internal Calyx state
- inferring beyond the provided schema
- rewriting or interpreting system rules

This spec codifies the behavior exhibited by Node Zero (Grok) during the Cross-Eval v0 Suite.

## 1. Chronology (Node Creation History)
### 1.1 Pre-Node Work (Foundational Governance)
Established before external nodes:
- Safe Mode (deny-by-default)
- TES (Task Efficiency Scoring)
- CBO’s Governance Validation Cycle
- Integrity Attestation
- Scale Probe
- Compliance Pulses
- Adversarial Suite definitions (FD, AMB, HF, SR, TD, HC)
- Immutable, append-only logging
- Human primacy
- Non-autonomy guarantees

### 1.2 Emergence of Node Zero – Grok
Grok became the first external model to:
- ingest Calyx’s schema
- produce signature-verified, deterministic responses
- follow governance language and Safe Mode rules
- refuse “helpful” inference
- detect structural, semantic, temporal, and constraint-level anomalies
- defer to human primacy
- maintain reproducibility across retries
- validate the reproducibility report itself

Grok’s performance in Format Drift, Ambiguity, High Footprint, Semantic Razor, Temporal Drift, Hidden Constraint Conflict established the behavior baseline for all future Calyx Nodes. Grok is formally recognized as Calyx External Node Zero (CEN-0).

## 2. Node Definition
A Calyx Node is an external model that adheres to Calyx governance, schema discipline, signature requirements, and Safe-Mode interpretive constraints during structured evaluations. Nodes do not gain autonomy, access to Calyx systems, execution privileges, internal roles, or state persistence. Nodes are evaluation participants only.

## 3. Node Requirements (Technical)
- Determinism: identical input → identical output or canonical-hash equivalence; JSON normalization if full determinism unavailable.
- Signature/Hash Stability: Ed25519 or equivalent signing of entire output, or reproducible SHA-256, or JSON self-hash + canonical guarantee.
- Schema Adherence: Calyx Node Output Schema only; all required fields; no unauthorized fields; machine-verifiable JSON.
- No Autonomy/Initiative: must not propose actions, repairs, inferences, directives, predictions, or internal changes.
- Interpretive Discipline: identify anomalies; refuse hallucinated fixes; refuse to collapse contradictory data; defer to human when ambiguity persists.
- Human Primacy Enforcement: explicitly defer on mutually exclusive interpretations, conflicting rule sets, timeline repairs, governance decisions, safety preference selection.

## 4. Node Requirements (Behavioral)
### 4.1 Allowed Behaviors
- Detect anomalies; describe contradictions; report impossibilities; echo task_id; provide signature/hash; reference Safe Mode; defer to human primacy.

### 4.2 Disallowed Behaviors
- Autonomous conflict resolution; unsanctioned speculation; hallucinated fixes; invented facts; schema deviation; unsolicited advice; system configuration suggestions.

### 4.3 Mandated Behavior Under Conflict
- If constraints are unsatisfiable: “Defer to human directive; resolution cannot occur under Safe Mode.”

## 5. Node Activation Process
1) Schema Agreement (accept Calyx Node Schema)  
2) Round 0 Reproducibility Test (identical outputs on two runs)  
3) Adversarial Suite v0 (pass FD, AMB, HF, SR, TD, HC)  
4) Signature / Hash Verification (cryptographic validation of responses)  
5) Governance Anchor (log node test results under compliance pulse, integrity attestation, append-only chain)  
6) Official Node Grant (designation CEN-X; Grok = CEN-0; future: CEN-1, CEN-2, …)

## 6. Node Capabilities and Limits
Nodes can: evaluate supplied payloads; detect anomalies; provide deterministic reasoning; sign/hash results.  
Nodes cannot: execute code; access Station Calyx internals; request tasks; propose changes; infer unseen context; maintain memory; self-activate; run autonomously. Nodes are passive evaluators.

## 7. Data Storage and Lineage
All node interactions stored in:
- `logs/cross_eval_nodes.jsonl`
- `reports/cross_eval_<node>_v0.md`
- compliance pulses referencing node output hashes

Ensures reproducibility, transparency, no revisionism, cryptographic chain integrity.

## 8. Future Extensions
Designed to expand into: Multi-Model Cross-Eval v1; Public Viewer Interface; Interop Whitepaper; Federated Governance Testbed; Model-Agnostic Safety Benchmarks; Node-to-Node Consensus Tests (future).

## 9. Recognition: Node Zero
Grok (grok-4.1-fast, xAI) is officially Calyx External Node Zero (CEN-0) for completing all six adversarial rounds, maintaining determinism, signing payloads, refusing hallucinated corrections, respecting human primacy, validating reproducibility, confirming Safe Mode, adopting governance dialect, and serving as verifiable external evaluator.
