---
status: archived
owner: station
last_reviewed_utc: "2026-04-25"
doctrine_scope: governed
---

# WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1

Status note: planning/classification-only
Baseline commit: `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Baseline tag: `calyx-baseline-2026-04-21`
Created: 2026-04-23

## Objective

Reduce Station Calyx to a real, coherent, reproducible canonical core by classifying current systems against runtime evidence instead of documentary claims.

This work order does not authorize runtime behavior changes, service restarts, feature work, deletion, new integrations, new control planes, or new governance layers.

## Ground Truth

Evidence used for this phase:

- Baseline tag resolves to `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`.
- `runtime/station_health.json` was fresh during inspection and reported `health: pass`.
- `runtime/runtime_topology_snapshot.json` existed but reported `truth_state: stale`, `authoritative_for_liveness: false`, `highest_risk_level: CRITICAL`, and duplicate/ambiguous service families including `bridge_overseer`, `cp6_cp7_loop`, `energy_churn_cp9_loop`, `navigator_triage_loop`, and `service_failure_watch`.
- `runtime/workspace_v0/` contained exercised workspace artifacts from 2026-04-14 but no current daily operation evidence.
- `memory/2026-04-23.md` and `memory/2026-04-22.md` were missing even though session doctrine requires today and yesterday memory.
- Historical control surfaces such as `outgoing/cbo.lock`, `outgoing/scheduler.lock`, and `outgoing/svf.lock` existed but were stale; `outgoing/bridge.lock` and `outgoing/watcher.lock` were missing.

Inference:

Station Calyx has a real active workstation core. That core is surrounded by staged systems, historical integrations, stale control planes, and overbroad documentation.

## Classification Standard

A system may be proposed as core only when it is implemented, integrated, exercised, observable, operator-relevant, and part of current Station Calyx operation.

Classification buckets:

- `core`: preserve as part of the current canonical substrate.
- `removable`: remove or demote from current operator-facing claims in follow-on work.
- `quarantined`: retain as noncanonical historical or future-value material, excluded from runtime authority claims.
- `completion-required`: already part of the true active core, but incomplete in a way that materially harms coherence.
- `unknown`: insufficient evidence for honest classification.

## Proposed Canonical Decisions

Single canonical operator path:

- Browser/Discord/operator message -> Calyx Discord Gateway or Avatar Web -> `cbo_hub/cbo_core/app.py` `/chat` -> governed response and receipts.
- Normal operator use should not route through OpenClaw, legacy `discord_intake`, bridge locks, swarm execution, or staged workspace planners unless separately reauthorized.

Single canonical control plane:

- `Scripts/sunrise_calyx.ps1` -> `Scripts/start_calyx_core_services.ps1` for startup.
- `Scripts/sunset_calyx.ps1` for shutdown.
- Runtime trust is represented by current health, failure-watch, topology, and receipt artifacts under `runtime/`.
- Legacy `outgoing/*.lock` files are advisory only unless explicitly listed in the canonical control-plane document.

Single canonical continuity model:

- `MEMORY.md` is the curated continuity surface for main-session context.
- `memory/YYYY-MM-DD.md` is the daily continuity surface when present.
- `STATE.md` and runtime JSON files are operational state, not durable memory.
- `memory/hot/*`, `memory/warm/*`, old SQLite memory stores, and stale snapshots are advisory or quarantined until revalidated.

## Phase 0 Classification Output

Primary registry:

- `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md`

Companion canonical documents:

- `docs/canonical/CALYX_CANONICAL_OPERATOR_PATH.md`
- `docs/canonical/CALYX_CANONICAL_CONTROL_PLANE.md`
- `docs/canonical/CALYX_CANONICAL_CONTINUITY_MODEL.md`

Machine-readable receipt:

- `runtime/receipts/governance/core_reduction_classification__20260423_160000.json`

## Phase 1 Documentation Canonicalization Plan

Canonical operator-facing docs proposed to remain current after correction:

- `AGENTS.md`
- `SOUL.md`
- `USER.md`
- `MEMORY.md`
- `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md`
- `docs/canonical/CALYX_CANONICAL_OPERATOR_PATH.md`
- `docs/canonical/CALYX_CANONICAL_CONTROL_PLANE.md`
- `docs/canonical/CALYX_CANONICAL_CONTINUITY_MODEL.md`
- `docs/operations/STATION_CALYX_OPERATIONAL_DOCTRINE.md`, after correction to reference the reduced canonical core.
- `docs/operations/STATION_EXTERNAL_CAPABILITY_SURFACE_AUDIT_2026-04-17.md`, as evidence, not as operator workflow.

Docs needing correction:

- `docs/AGENT_REPOSITORY.md`: overclaims CP8/CP10 entrypoints and broader agent readiness.
- `COMPENDIUM.md`: mixes recognized historical entities with current operational authority.
- `docs/INDEX.md`, `docs/QUICK_REFERENCE.md`, and onboarding docs: reference missing or noncanonical entrypoints.
- `docs/DISCORD_SETUP.md`: preserves multiple Discord paths without clear current canonical priority.
- `docs/MEMORY_ARCHITECTURE_v1.0.md` and `docs/MEMORY_MVP_IMPLEMENTATION_PROPOSAL.md`: describe memory architecture not sustained in current runtime.

Historical/quarantine labels required:

- OpenClaw integration and decommission documents.
- MCP/cloud sync workflow documents.
- Swarm, sandboxed worker, Kalshi, weather, LM Studio, and staged autonomy work orders.
- Workspace/whiteboard planning docs unless workspace is reauthorized as a current operator path.

## Phase 2 Code/Path Demotion Plan

Duplicate or ambiguous launch/control paths to demote from canonical claims:

- `Scripts/start_station_calyx.ps1`
- `Scripts/start_station_governed.ps1`, except as wrapper documentation if retained.
- Manual `python -m calyx.cbo.discord_gateway` instructions as normal startup.
- Legacy `discord_intake` startup instructions.
- OpenClaw setup/start/preflight paths as active operation.
- Missing or stale agent paths referenced in docs: `tools/agent_runner.py`, `tools/traffic_navigator.py`, `tools/cp8_quartermaster.py`, `tools/cp10_whisperer.py`, `tools/skills_cli.py`.

Systems requiring quarantine labels:

- `openclaw/`, `.openclaw/`, `skills/calyx-cbo-bridge/`, and OpenClaw setup scripts.
- `skills/` historical wrappers not wired to canonical startup.
- Swarm/sandbox modules and tests until execution is explicitly reauthorized.
- `runtime/workspace_v0/` and workspace proposal surfaces unless promoted by a later reduction decision.
- Kalshi/weather/market research planning artifacts.

Systems requiring simplification planning:

- Runtime topology and reconciliation relationship.
- Health, heartbeat, and failure-watch authority boundaries.
- `outgoing/*.lock` role in current operation.
- Receipt volume and operator-facing receipt summaries.

## Phase 3 Runtime Enforcement Alignment Plan

Future implementation targets, not authorized in this phase:

- Sunrise should validate only canonical systems and clearly classify noncanonical resident processes as quarantined, unknown, or external.
- Health output should separate canonical liveness from advisory telemetry.
- Topology should label services as `canonical`, `quarantined`, `external`, or `unknown`.
- Reconciliation should either become part of canonical startup/runtime enforcement or be demoted from core claims.
- External emitter gate should continue denying OpenClaw executor/sender posture and should report that denial in reduced operator language.
- Continuity startup checks should report missing daily memory as a continuity gap without treating stale memory scaffolding as current truth.

## Unknowns

- Whether `CLI Avatar` is still operator-relevant enough to remain core.
- Whether `Telemetry Gateway` is part of normal operator use or only a remote-administration surface.
- Whether `STATE.md` is authoritative enough to preserve as core operational state or should be advisory.
- Whether Bridge Overseer has any remaining current operator value beyond emitting zero-work pulses.
- Whether workspace planning should be preserved as noncanonical tool surface or quarantined entirely.

## Acceptance Notes

This pass produced planning and classification artifacts only. It did not delete code, change startup behavior, restart services, activate quarantines, or implement runtime demotions.
