# BloomOS Agent Transparency Pilot - cp18_validator (Validation v0.1)

- Mandate: `canon/agent_mandate_registry_v0.1.yaml#agents.cp18_validator` (sprout; supervisor=cbo; prohibitions: repo writes, network, daemons; static/dry diff validation).
- Pilot run: `tools/cp18_validator.py --patch outgoing/reviews/cp18_pilot.patch --metadata outgoing/reviews/cp18_pilot_metadata.json --intent-id cp18_pilot_validation --test-mode`.
- Artifacts: verdict `outgoing/reviews/cp18_pilot_validation.CP18.verdict.json` (PASS; files_seen=1, py_files_checked=1); introspection `state/agents/cp18_validator/introspection.json` (+history JSONL); trace `logs/agents/cp18_validator_trace.jsonl` (test_mode=true).
- Governance alignment: Laws 2/4/5/9/10 + Agent Transparency §3.4.1 recorded via respect_frame in introspection and trace; schema-validated against v0.1 introspection/trace schemas.

## Introspection snapshot (final)
```json
{
  "timestamp": "2025-12-05T06:18:10.210531+00:00",
  "agent_id": "cp18_validator",
  "mandate_ref": "agents.cp18_validator",
  "lifecycle_phase": "sprout",
  "intent": "validate diff (cp18) for cp18_pilot_validation",
  "current_task": "static diff validation (complete)",
  "inputs": {
    "patch_path": "outgoing\\reviews\\cp18_pilot.patch",
    "metadata_path": "outgoing\\reviews\\cp18_pilot_metadata.json",
    "metadata_keys": [],
    "files_seen": 1,
    "py_files_checked": 1,
    "missing_tests": []
  },
  "constraints": [
    "static diff analysis only (no execution)",
    "no network egress (enable_network prohibited)",
    "no repo writes",
    "no daemons/schedulers"
  ],
  "uncertainty": "no blocking findings",
  "last_decision": "verdict=PASS",
  "planned_next_step": "await Architect review",
  "respect_frame": {
    "laws": [2, 4, 5, 9, 10, "3.4.1"],
    "respect_frame": "agent_transparency_doctrine"
  },
  "health": {"status": "ok"}
}
```

## Trace entry (example)
```json
{
  "ts": "2025-12-05T06:18:10.211410+00:00",
  "agent_id": "cp18_validator",
  "lifecycle_phase": "sprout",
  "intent": "validate diff (cp18) for cp18_pilot_validation",
  "context": {"mandate_ref": "agents.cp18_validator", "intent_id": "cp18_pilot_validation"},
  "inputs_summary": {
    "patch_path": "outgoing\\reviews\\cp18_pilot.patch",
    "metadata_path": "outgoing\\reviews\\cp18_pilot_metadata.json",
    "metadata_keys": [],
    "files_seen": 1,
    "py_files_checked": 1
  },
  "decision": {"type": "run", "reason": "static/dry validation of diff", "uncertainty": "no blocking findings"},
  "action": {
    "requires_approval": false,
    "proposed_change": "emit PASS/FAIL verdict JSON",
    "side_effects": [
      "write verdict to outgoing/reviews",
      "update introspection snapshot",
      "append trace log"
    ]
  },
  "outcome": {
    "status": "PASS",
    "errors": null,
    "verdict_path": "C:\\Calyx_Terminal\\outgoing\\reviews\\cp18_pilot_validation.CP18.verdict.json"
  },
  "test_mode": true,
  "laws": [2, 4, 5, 9, 10, "3.4.1"],
  "respect_frame": "agent_transparency_doctrine"
}
```

## Observations and follow-ups
- cp18 mirrors cp14 transparency pattern with schema validation and append-only logs; no violations recorded in `logs/agent_schema_violations.jsonl`.
- Metadata surfaced only as key list; consider adding provenance hashes or validation version in a future v0.2 schema.
- Log rotation/retention remains future work; current logs are append-only as required.
