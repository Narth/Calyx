# Calyx Path And Entrypoint Demotion Registry

Status: canonical registry
Date: 2026-04-23
Work order: `WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1`

This registry identifies paths whose names, locations, launchers, or documentation may imply more authority than the resolved Station Calyx model permits. This is not an implementation plan by itself; it is a target list for later approved runtime enforcement, demotion, removal, or labeling.

Status vocabulary: `canonical core`, `canonical support`, `quarantined noncanonical`, `deprecated`, `historical`, `unknown`.

| path | previous implied status | corrected status | reason for correction | change type | further runtime enforcement needed | recommended later action |
|---|---|---|---|---|---|---|
| `Scripts/sunrise_calyx.ps1` | Canonical startup path | canonical core | Current normal startup wrapper. | reviewed-only | yes, status classes should be reflected during validation | preserve |
| `Scripts/start_calyx_core_services.ps1` | Starts all core services | canonical core | Starts core services plus support surfaces; name may overstate all launched services as core. | reviewed-only | yes | simplify labels or output |
| `Scripts/sunset_calyx.ps1` | Canonical shutdown path | canonical core | Current shutdown counterpart. | reviewed-only | no | preserve |
| `cbo_hub/dev_harness/app.py` | Core service | canonical core | CBO Core dependency and local service substrate. | reviewed-only | no | preserve |
| `cbo_hub/cbo_core/app.py` | Core CBO service | canonical core | Governed `/chat` mediation authority. | reviewed-only | no | preserve |
| `cbo_hub/avatar_web/app.py` | Core local operator UI | canonical core | Local browser client and operator surface. | reviewed-only | no | preserve |
| `cbo_hub/cli_avatar/main.py` | Possible operator surface | canonical support | Optional client only; no independent authority beyond `/chat`. | documentation-only | no | preserve with support label |
| `cbo_hub/telemetry_gateway/app.py` | Core service or remote control plane | canonical support | Remote-support ingress only; not normal operator path. | documentation-only | yes | preserve with support label |
| `STATE.md` | Station truth/state authority | canonical support | Generated operational digest, not sole truth. | documentation-only | yes | preserve with advisory label |
| `MEMORY.md` | Runtime/long-term continuity authority | canonical support | Curated operator reference and partial continuity component only. | documentation-only | no | preserve with support label |
| `calyx/cbo/discord_gateway.py` | Discord relay | canonical core | Current governed Discord transport. | reviewed-only | no | preserve |
| `calyx/cbo/discord_intake.py` | Discord intake authority | quarantined noncanonical | Legacy alternate path superseded by Discord Gateway. | reviewed-only | yes | quarantine or remove from launch docs |
| `Scripts/start_station_calyx.ps1` | Station startup path | quarantined noncanonical | Legacy launcher name implies authority, but not current normal startup path. | reviewed-only | yes | demote/rename/remove claim |
| `calyx/cbo/bridge_overseer.py` | CBO orchestration authority | quarantined noncanonical | Authority resolution found no current canonical orchestration role. | documentation-only | yes | quarantine runtime path or remove from startup |
| `calyx/cbo/api.py` | Bridge Overseer API authority | quarantined noncanonical | Coupled to Bridge Overseer control plane. | documentation-only | yes | quarantine |
| `calyx/cbo/README.md` | Bridge Overseer package authority doc | quarantined noncanonical | Now visibly marked noncanonical. | documentation-only | yes | keep historical or demote further |
| `cbo_hub/avatar_web/workspace_v0.py` | Workspace planning/operator path | quarantined noncanonical | Dormant planning surface, not canonical operator path. | reviewed-only | yes | quarantine label in UI/docs or remove later |
| `runtime/workspace_v0/*` | Workspace planning state | quarantined noncanonical | Historical workspace artifacts only. | reviewed-only | yes | archive/quarantine later |
| `calyx/mail/*` | Canonical mail/intent spine | quarantined noncanonical | Historical/staged path bypassed by governed `/chat`. | reviewed-only | yes | quarantine or remove claims |
| `calyx/cbo/intent_pipeline/*` | Intent pipeline authority | quarantined noncanonical | Not current runtime mediation authority. | reviewed-only | yes | quarantine |
| `calyx/execution/hub_runner.py` | Work-envelope runner authority | quarantined noncanonical | Historical/staged execution path. | reviewed-only | yes | quarantine |
| `calyx/execution/task_handlers/*` | Real task execution handlers | deprecated | Mostly stub execution claims. | reviewed-only | yes | remove or mark stub |
| `calyx/kernel/swarm_*` | Swarm runtime substrate | quarantined noncanonical | Test/staged infrastructure, not active canonical execution. | reviewed-only | yes | quarantine |
| `openclaw/` | External execution/integration surface | quarantined noncanonical | Explicitly outside reduced core. | reviewed-only | yes | quarantine |
| `Scripts/setup_openclaw_calyx.ps1` | OpenClaw setup authority | quarantined noncanonical | Setup launcher implies integration authority not granted. | reviewed-only | yes | demote/remove later |
| `skills/calyx-cbo-bridge/` | Active OpenClaw bridge skill | quarantined noncanonical | Capability-bearing external integration surface. | documentation-only | yes | quarantine |
| `tools/cp8_quartermaster.py` | CP8 entrypoint | deprecated | Referenced in docs but missing. | documentation-only | no runtime path exists | remove claims |
| `tools/cp10_whisperer.py` | CP10 entrypoint | deprecated | Referenced in docs but missing. | documentation-only | no runtime path exists | remove claims |
| `cbo_hub/compose.yaml` | Reproducible deploy topology | deprecated | Placeholder, not current deploy/runtime authority. | reviewed-only | yes | remove deploy claim |

## Later Enforcement Boundary

This registry does not authorize implementation. A later approved pass must decide whether to rename, remove, quarantine in code, exclude from sunrise, or alter runtime health/topology labeling.
