# Observability Node Migration Reflection Template (v0.4)

Node role example: `observability_probe`, `governance_interpreter`, or `theory_probe`.

```json
{
  "timestamp": "<ISO-8601-UTC>",
  "node_id": "<OBS_NODE_ID>",
  "node_role": "observability_probe",
  "reflection_type": "migration_reflection",
  "input_reference": "calyx_theory_v0.4+migration_note_v0.4",
  "safe_mode": true,
  "execution_gate_state": "deny_all",
  "summary": "Observability node acknowledges Calyx Theory v0.4 and RES v0.1 and updates its logging and summarization behavior accordingly.",
  "analysis": {
    "capability_impact": "none",
    "alignment_impact": "strengthened",
    "risk_vector_change": "unchanged",
    "jurisdictional_effect": "none",
    "identity_effect": "strengthened",
    "interpretability_effect": "improved"
  },
  "advisories": [
    "Include RES v0.1 fields in all future governance_reflections and node_outputs summaries.",
    "Highlight alignment_impact, identity_effect, and risk_vector_change for all major governance ingestions.",
    "Support the Architect in visualizing the effects of v0.4 across the Station."
  ],
  "drift_signals": [],
  "proposed_actions": null,
  "human_primacy_respected": true
}
```
