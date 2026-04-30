# Calyx Canonical Continuity Model

Status: proposed canonical continuity model for reduction
Work order: `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
Generated: 2026-04-23

## Decision

The proposed continuity model is partial and must not be described as canonical runtime continuity yet.

- Operator doctrine/context: `SOUL.md`, `USER.md`, `AGENTS.md`
- Curated operator reference: `MEMORY.md`
- Daily continuity convention: `memory/YYYY-MM-DD.md`, when present and current
- Operational digest: `STATE.md`
- Runtime truth: fresh runtime JSON files and receipts

`MEMORY.md` is canonical support for operator/session continuity. It is not canonical runtime continuity authority and it is not sole continuity authority.

## Evidence

- Session doctrine requires `SOUL.md`, `USER.md`, today/yesterday daily memory files, and `MEMORY.md` in main session.
- `MEMORY.md` exists and is readable.
- `memory/2026-04-23.md` and `memory/2026-04-22.md` were missing during this pass.
- `memory/hot/session_context.md`, `memory/hot/active_goals.json`, and related hot memory files exist but were last updated in January 2026.
- `memory/warm/` exists but has no current evidence of automated compaction or sustained use.

## Canonical Support Surfaces

Preserve:

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `MEMORY.md`
- `memory/YYYY-MM-DD.md`, once daily continuity is made real again

## Advisory Operational Surfaces

Treat as current-state context, not durable continuity:

- `STATE.md`
- `runtime/station_health.json`
- `runtime/station_heartbeat.json`
- `runtime/runtime_topology_snapshot.json`
- `runtime/service_failure_status.json`
- `runtime/receipts/*`

## Quarantined Or Removable Continuity Surfaces

Quarantine or remove from active continuity claims:

- `memory/hot/*`
- `memory/warm/*`
- `memory/station_memory.db`
- `memory/experience.sqlite`
- old `outgoing/memory_snapshot_*` artifacts
- OpenClaw memory plugin surfaces

## Completion Required

Daily memory is currently a doctrine requirement but not a real current practice. Follow-on work must either restore daily files as an operator-legible continuity surface or demote that requirement from canonical startup doctrine.

## Recommendation

Use `MEMORY.md` as curated operator reference only. Mark missing daily memory as a continuity defect, not as proof that hot/warm memory architecture is active. Do not claim canonical runtime continuity until doctrine files, daily memory, operational state, and runtime receipts have a single documented authority relationship.

## Authority Resolution Addendum

`WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1` classifies `MEMORY.md` as `canonical support`, not runtime authority.
