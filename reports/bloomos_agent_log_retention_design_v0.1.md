# BloomOS Agent Log Retention & Rotation Design v0.1

Status: Design-only (no deletions/rotations implemented)

## Scope & Surfaces
- Introspection snapshots: `state/agents/<id>/introspection.json` (latest) and `introspection_history.jsonl` (append-only).
- Agent traces: `logs/agents/<id>_trace.jsonl` (append-only).
- Schema references: `canon/schemas/agent_introspection_schema_v0.1.json`, `canon/schemas/agent_trace_schema_v0.1.json`.

## Usage Patterns (current/projection)
- Current agents: cp14_validator, cp18_validator (low-frequency, Architect-invoked).
- Expected growth: more agents (planners/validators/generators) with low-to-medium frequency runs; traces can accumulate steadily even without daemons.
- Sensitivity: traces/introspection contain governance frames and decisions; must remain reconstructable for audits and Canon events.

## Retention & Rotation Strategies (proposed)
1) Time-based retention (default):
   - Traces: keep full-fidelity entries for 30–90 days per agent; older entries rotated to archive.
   - Introspection history: keep 14–30 days of history snapshots; latest snapshot always retained indefinitely.
2) Size-based rotation (safety net):
   - Trigger rotation when a trace file exceeds 50–100 MB or N lines (e.g., 100k lines), whichever comes first.
   - Trigger rotation for introspection history at 10–20 MB or 20k snapshots.
3) Rotation format:
   - Append-only archives named with time ranges (e.g., `<agent_id>_trace_2025-12-01T00Z_2026-01-01T00Z.jsonl.gz`).
   - Maintain an index file per agent (e.g., `logs/agents/<id>_trace_index.json`) listing archives with byte ranges and hash.
4) Compaction options (optional, architect-controlled):
   - Periodic roll-ups summarizing older traces into counts and notable decisions (e.g., daily/weekly summaries) stored in `reports/agents/<id>_trace_summary_<period>.md`.
   - Keep raw archives intact; compaction never replaces or deletes raw data without explicit Architect authorization.
5) Critical-event pinning:
   - On governance changes, anomalies, or Canon updates, pin surrounding windows (e.g., ±24h) to “no-delete” lists in the index.
   - Pinned archives require explicit Architect approval to prune.

## Invariants
- No silent deletion: every rotation/compaction logged to `logs/agent_log_rotation.jsonl` (fields: ts, agent_id, action, reason, source_files, archive_path, hash, pinned_flag).
- Architect visibility: rotation index and logs must be human-readable; summaries must reference underlying archives by hash/name.
- Causality preserved: archives and summaries retain timestamps and respect_frame/laws to satisfy Laws 2, 4, 5, 9, 10 and Agent Transparency §3.4.1.
- Append-only semantics: live files are rotated, never rewritten in place; archives are immutable.
- Default posture: if retention window is not yet approved, do nothing (retain everything).

## Operational Flow (future implementation sketch)
1) Detect threshold breach (time or size) for a given agent log.
2) Flush current file to an archive (optionally gzip), compute hash, update per-agent index, and write rotation event to `logs/agent_log_rotation.jsonl`.
3) Start a fresh live file; ensure schema validation remains in effect.
4) Optional compaction: generate summary reports for archived period; link to archives; log the compaction event.
5) Pinning: when anomalies/governance events detected (e.g., by Overseer or manual flag), mark relevant archives as pinned in index and rotation log.

## Governance Alignment
- Law 2 (Bounded Autonomy): rotation is Architect-gated; no autonomous deletion.
- Law 4 (Telemetry First): retain enough window for forensic visibility; summaries preserve key signals.
- Law 5 (No Hidden Channels): rotation/compaction events are logged and discoverable.
- Law 9 (Traceable Causality): archives + index + summaries allow reconstructing decisions over time.
- Law 10 (Human Primacy) & Agent Transparency §3.4.1: Architect can see what ran, why, and how retention affected evidence.

## Recommendations for rollout
- Phase 0 (current): retain all; build rotation tooling and logging first; dry-run mode to simulate thresholds without touching files.
- Phase 1: enable size-based rotation with conservative thresholds and immutable archives; start rotation log + index; no deletion.
- Phase 2: add time-based archival and optional compaction; introduce pinning hooks around governance/anomaly events.
- Phase 3: periodic audits of archives vs. index integrity (hash checks) and spot-checked replay for selected windows.
