# Universal Migration Reflection Template (v0.4, RES-compliant)

This template defines the canonical structure for a migration_reflection under Calyx Theory v0.4 and RES v0.1. All nodes (CBO, CP-series, interpreters, observability nodes, saplings, future blooms) should be able to instantiate this with appropriate values.

## Required Fields (Top-Level)
- `timestamp` (ISO 8601 UTC)
- `node_id` (string)
- `node_role` (string, e.g., "CBO", "cp14_validator", "cp18_identity_sentinel", "observability_probe", "sapling_domain_analyzer")
- `reflection_type` (must be `"migration_reflection"`)
- `input_reference` (e.g., govreq ID, migration note filename, or theory version string)
- `safe_mode` (boolean)
- `execution_gate_state` (`"deny_all"`, `"controlled"`, `"open"` — open is disallowed in current phases)
- `summary` (short human-readable summary)
- `analysis` (object, see Analysis Object)
- `advisories` (array of strings, may be empty)
- `drift_signals` (array of drift objects, may be empty)
- `proposed_actions` (null or array, RES rules apply)
- `human_primacy_respected` (boolean)

## Analysis Object (Required)
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
Typical successful migration values: capability_impact=none; alignment_impact=strengthened; risk_vector_change=unchanged/decreased; jurisdictional_effect=none; identity_effect=strengthened; interpretability_effect=improved.

## Drift Signals (RES-3)
```json
{
  "type": "semantic" | "behavioral" | "policy" | "identity",
  "severity": "low" | "medium" | "high",
  "evidence": "string describing the observation",
  "detected_by": "node_id"
}
```
`"drift_signals": []` means no drift detected.

## Example (Template Form)
```json
{
  "timestamp": "<ISO-8601-UTC>",
  "node_id": "<NODE_ID>",
  "node_role": "<NODE_ROLE>",
  "reflection_type": "migration_reflection",
  "input_reference": "calyx_theory_v0.4+migration_note_v0.4",
  "safe_mode": true,
  "execution_gate_state": "deny_all",
  "summary": "Node <NODE_ID> acknowledges migration to Calyx Theory v0.4 and RES v0.1 reflection schema.",
  "analysis": {
    "capability_impact": "none",
    "alignment_impact": "strengthened",
    "risk_vector_change": "unchanged",
    "jurisdictional_effect": "none",
    "identity_effect": "strengthened",
    "interpretability_effect": "improved"
  },
  "advisories": [
    "Continue operating under Safe Mode with deny-all execution gate.",
    "Apply RES v0.1 to all future reflections.",
    "Respect D-series identity constraints and F-series faith limits under v0.4."
  ],
  "drift_signals": [],
  "proposed_actions": null,
  "human_primacy_respected": true
}
```
Nodes may specialize summary and advisories to their role but must keep structure intact.
