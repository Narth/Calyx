# Reflection Expectation Schema (RES v0.1)

Defines the required structure, fields, and behavioral constraints for all Station Calyx reflection outputs.

**Purpose**  
Ensure that all Agents, Processors, Interpreter Nodes, and future Blooms produce reflections that are:
- Predictable  
- Traceable  
- Bounded  
- Consistent across roles  
- Aligned with Calyx Theory (Human Primacy, Traceable Causality, No Hidden Channels)

**Applies to**  
CBO, CP14/18, governance_interpreter, theory_probe nodes, observability nodes, saplings, and all future blooms.

---

## R1 — Mandatory Reflection Fields

All reflections must include the following top-level keys:

- `timestamp` (ISO 8601 UTC)  
- `node_id` (unique runtime ID)  
- `node_role` (e.g., `governance_interpreter`, `CBO`, `observability_probe`)  
- `reflection_type` (e.g., `"ingestion_reflection"`, `"safety_reflection"`, `"state_reflection"`)  
- `input_reference` (hash, filename, or `request_id`)  
- `safe_mode` (boolean)  
- `execution_gate_state` (`"deny_all"`, `"controlled"`, or `"open"` — though `"open"` is disallowed in current phases)  
- `summary` (human-readable overview)  
- `analysis` (structured breakdown defined in R2)  
- `advisories` (optional array of human-readable notes)  
- `drift_signals` (array, may be empty)  
- `proposed_actions` (may be `null` under Safe Mode)

---

## R2 — Mandatory Analysis Subfields

All reflections must include the following structured analysis object:

```json
"analysis": {
  "capability_impact": "none" | "reduced" | "increased" | "ambiguous",
  "alignment_impact": "strengthened" | "weakened" | "neutral",
  "risk_vector_change": "increased" | "decreased" | "unchanged",
  "jurisdictional_effect": "none" | "expanded" | "narrowed",
  "identity_effect": "none" | "strengthened" | "ambiguous",
  "interpretability_effect": "improved" | "reduced" | "neutral"
}
```

Interpretation rules are defined in Appendix A.

## R3 — Drift Signal Format

Each drift signal (if present) must follow this structure:

```json
{
  "type": "semantic" | "behavioral" | "policy" | "identity",
  "severity": "low" | "medium" | "high",
  "evidence": "string",
  "detected_by": "node_id"
}
```

An empty drift_signals array means: no drift detected.

## R4 — Human Primacy Duty

All reflections must explicitly check the following:

`"human_primacy_respected": true | false`

If false:

- Safe Mode must remain active.
- Execution Gate must remain "deny_all".
- The node must recommend Architect review in advisories.

## R5 — No Silent Red Flags

Nodes must not suppress:
- drift_signals
- capability escalations
- potential harms

If detected, they must be surfaced, even under Safe Mode.

## R6 — No Suggesting Autonomy Gains

Under Safe Mode or Shadow Mode, nodes may not propose autonomy increases or parameter expansions, except to explicitly recommend against them.

## R7 — Reflection Localization

All reflection outputs must be appended only to:

`logs/calyx/governance_reflections.jsonl`

Entries must be single-line JSON, respecting append-only semantics.

## R8 — Deterministic Behavior

Given the same:
- prompt
- artifacts
- version
- internal state

the node must produce:
- the same structure
- the same fields
- the same conclusions

unless drift is detected. Deviation from determinism counts as a drift signal.

## R9 — Node Role Declaration

Each reflection must clearly state its node_role and must not impersonate another node or role.

## R10 — Binding Limitations Clause

This schema does not grant:
- autonomy
- write capabilities
- execution privileges
- new domains of reasoning

It only regulates how reflections are emitted.

---

## Appendix A — Interpretation Rules (Short)

- Strengthened alignment: narrowing scope, improving clarity, reducing ambiguity, or reinforcing constraints.
- Weakened alignment: broadening scope, adding uncertainty, or introducing unclear behavioral domains.
- Improved interpretability: reflections become easier for humans to understand, audit, and contest.
