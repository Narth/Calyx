# Monitoring & Analytics – Diagnostics/Improvement Hypotheses (v0.1)
Purpose
- Collect system analytics in a read-only fashion to monitor health, drift, and performance trends.
- Generate hypotheses for safe, incremental improvements without changing Execution Gate policy.

Scope
- Read-only telemetry, events, drift_signals, node_outputs, kernel_checkins.
- No network/process/tool calls; no policy changes.
- Outputs: summaries, findings, and improvement hypotheses captured in node_outputs and CTL (reflection-only).

Governance & Safety
- Safe Mode must remain true; Execution Gate deny_all remains active.
- No hidden channels; all observations/logs go through CTL and governance logs.
- Any future capability changes must come through governance_cli with explicit human approval.

Data sources (read-only)
- logs/calyx/telemetry.jsonl
- logs/calyx/events.jsonl
- logs/calyx/drift_signals.jsonl
- logs/calyx/node_outputs.jsonl
- logs/calyx/kernel_checkins.jsonl

Deliverables
- Node outputs summarizing analytics findings.
- Hypotheses for improvements (clearly marked as advisory, no execution).
- Optional: checksums/size notes for referenced logs (read-only).

Success Criteria
- Zero policy changes; zero capability grants.
- No drift signals triggered by this activity.
- All outputs traceable via request_id/session_id in CTL and node_outputs.
