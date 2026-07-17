# Calyx Canonical Operator Path

Status: proposed canonical path for reduction
Work order: `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
Generated: 2026-04-23

## Decision

The proposed single canonical operator path is:

`human operator -> Avatar Web or Calyx Discord Gateway -> CBO Core /chat -> governed response -> receipts/runtime truth`

Normal operator interaction should flow through:

- Browser/local UI via `cbo_hub/avatar_web/app.py`.
- Discord via `calyx/cbo/discord_gateway.py`.
- Core reasoning and response through `cbo_hub/cbo_core/app.py` `/chat`.

Canonical support surfaces:

- `cbo_hub/cli_avatar/main.py` may be used as an optional local terminal client to `/chat`.
- `cbo_hub/telemetry_gateway/app.py` may be used as authenticated/audited remote-support ingress.

These support surfaces do not define separate operator authority.

## Evidence

- `Scripts/start_calyx_core_services.ps1` starts the core HTTP services and Discord Gateway.
- `runtime/station_heartbeat.json` and `runtime/runtime_topology_snapshot.json` show the core services and Discord Gateway as current runtime identities.
- `cbo_hub/receipts/cbo_core.jsonl` contains recent `/chat` receipts with routing proofs from `calyx-discord-gateway`.

## Noncanonical Operator Paths

The following must not be described as normal current operator paths:

- OpenClaw gateway or OpenClaw bridge.
- `calyx/cbo/discord_intake.py`.
- Mail/intent/work-envelope execution as the default operator path.
- Workspace proposal flow as the default operator path.
- Swarm worker execution.
- MCP/cloud sync workflows.
- Legacy bridge/outgoing lock control plane.

## Recommendation

Preserve the `/chat` path as the operator-facing core. Quarantine alternate ingress paths in documentation until a later authorized reduction pass either removes them from active claims or proves one should replace the current path.

## Resolved Boundary

`WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1` classifies CLI Avatar and Telemetry Gateway as `canonical support`, not as independent canonical operator paths.
