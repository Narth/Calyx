# BloomOS Agent Schema Validation (cp14_validator) v0.1

## Schemas established
- Introspection schema: `canon/schemas/agent_introspection_schema_v0.1.json` (required: timestamp, agent_id, mandate_ref, lifecycle_phase, intent, current_task, inputs, constraints, uncertainty, last_decision, planned_next_step, respect_frame{laws,respect_frame}, health).
- Trace schema: `canon/schemas/agent_trace_schema_v0.1.json` (required: ts, agent_id, lifecycle_phase, intent, context{mandate_ref, intent_id?}, inputs_summary, decision{type,reason,uncertainty?}, action{requires_approval, proposed_change, side_effects?}, outcome{status, errors?, verdict_path?}, test_mode, laws, respect_frame).
- Violation sink: `logs/agent_schema_violations.jsonl` (append-only, populated only on validation failures).

## Validation hooks implemented
- Introspection writes (cp14_sentinel): snapshot validated before write; on failure → violation log entry, skip write.
- Trace writes (cp14_sentinel): entry validated before append; on failure → violation log entry, skip append.
- Introspection reads (`tools/agent_introspect.py`): validates current + history entries; on failure → violation log entry and warning surfaced in output.

## Passing examples (cp14_pilot_validation run @ 2025-12-05T06:08:46Z)
- Introspection snapshot (state/agents/cp14_validator/introspection.json):
```json
{
  "timestamp": "2025-12-05T06:08:46.711704+00:00",
  "agent_id": "cp14_validator",
  "mandate_ref": "agents.cp14_validator",
  "lifecycle_phase": "sprout",
  "intent": "validate diff for cp14_pilot_validation",
  "current_task": "static diff scan (complete)",
  "inputs": {
    "patch_path": "outgoing\\reviews\\cp14_pilot.patch",
    "metadata_path": "outgoing\\reviews\\cp14_pilot_metadata.json",
    "metadata_keys": [],
    "added_lines": 4
  },
  "constraints": [
    "static diff scan only (no execution)",
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
- Trace entry (logs/agents/cp14_validator_trace.jsonl):
```json
{
  "ts": "2025-12-05T06:08:46.712411+00:00",
  "agent_id": "cp14_validator",
  "lifecycle_phase": "sprout",
  "intent": "validate diff for cp14_pilot_validation",
  "context": {"mandate_ref": "agents.cp14_validator", "intent_id": "cp14_pilot_validation"},
  "inputs_summary": {
    "patch_path": "outgoing\\reviews\\cp14_pilot.patch",
    "metadata_path": "outgoing\\reviews\\cp14_pilot_metadata.json",
    "metadata_keys": [],
    "added_lines": 4
  },
  "decision": {"type": "run", "reason": "static diff scan", "uncertainty": "no blocking findings"},
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
    "verdict_path": "C:\\Calyx_Terminal\\outgoing\\reviews\\cp14_pilot_validation.CP14.verdict.json"
  },
  "test_mode": true,
  "laws": [2, 4, 5, 9, 10, "3.4.1"],
  "respect_frame": "agent_transparency_doctrine"
}
```

## Retro-validation results
- Current cp14 introspection and trace artifacts pass v0.1 schemas; no violations recorded (logs/agent_schema_violations.jsonl absent).
- History entries validated on read; no decode or schema errors encountered.

## Recommendations for v0.2
- Add optional schema fields for provenance hashes (e.g., source patch sha), and validation version tag per entry.
- Introduce rotation/retention policy (size- or time-based) with immutable archives.
- Provide a small `tools/agent_schema_check.py` to batch-validate all agents’ artifacts and gate CI/manual reviews.
- Consider enforcing ISO8601 with timezone (tz-aware) explicitly in schema and validator for ts/timestamp fields.
