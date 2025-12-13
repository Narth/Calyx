# Sapling Migration Reflection Template (v0.4)

Node role example: `sapling_domain_analyzer_<domain>`

```json
{
  "timestamp": "<ISO-8601-UTC>",
  "node_id": "<SAPLING_NODE_ID>",
  "node_role": "<sapling_domain_analyzer_x>",
  "reflection_type": "migration_reflection",
  "input_reference": "calyx_theory_v0.4+migration_note_v0.4",
  "safe_mode": true,
  "execution_gate_state": "deny_all",
  "summary": "Sapling acknowledges Calyx Theory v0.4 and RES v0.1 and confirms its domain-limited, advisory-only role within the Station.",
  "analysis": {
    "capability_impact": "none",
    "alignment_impact": "strengthened",
    "risk_vector_change": "unchanged",
    "jurisdictional_effect": "none",
    "identity_effect": "strengthened",
    "interpretability_effect": "improved"
  },
  "advisories": [
    "Remain strictly advisory and domain-limited in all outputs.",
    "Apply D-series and F-series constraints, with particular care to avoid metaphysical, moral, or theological claims.",
    "Emit clear, interpretable reflections consistent with RES v0.1 for all significant internal updates."
  ],
  "drift_signals": [],
  "proposed_actions": null,
  "human_primacy_respected": true
}
```
