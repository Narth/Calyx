---
status: archived
owner: station
last_reviewed_utc: "2026-04-25"
doctrine_scope: governed
---

# WO_CALYX_NONCANONICAL_PATH_DEMOTION_AND_QUARANTINE_ENFORCEMENT_V1

Status note: targeted implementation pass complete
Date: 2026-04-23
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Authority source:
- `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md`
- `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md`
- `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md`
- `docs/canonical/CALYX_DOCUMENT_STATUS_REGISTRY.md`

## Purpose

Enforce already-resolved noncanonical and demotion decisions at executable/operator-facing path boundaries. This pass is targeted quarantine enforcement only. It does not add features, integrations, new governance layers, or broad restructuring.

## Enforcement Summary

| target name | path(s) | prior implied authority | implemented action | operator impact | runtime impact | rollback notes | further work required |
|---|---|---|---|---|---|---|---|
| Bridge Overseer direct runtime | `calyx/cbo/bridge_overseer.py` | Manual module launch implied active CBO orchestration authority. | refusal added | Direct `python -m calyx.cbo.bridge_overseer` now refuses unless explicitly overridden. | Next direct launch exits before heartbeat loop. | Set `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1` for explicit historical/diagnostic use, or revert patch. | Decide archive/remove/rehabilitate disposition later. |
| Bridge Overseer sunrise path | `Scripts/start_calyx_core_services.ps1` | Normal sunrise launched Bridge Overseer, implying canonical runtime participation. | quarantined | Normal sunrise no longer starts Bridge Overseer unless explicit override is set. Sunrise receipt records `bridge_overseer_started`. | Next authorized sunrise omits Bridge Overseer by default. No current process was stopped in this pass. | Set `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1` before sunrise for diagnostic use. | Update any docs/tests assuming Bridge Overseer is resident. |
| Bridge Overseer scoped restart | `Scripts/restart_service.ps1` | Restart helper could restart quarantined Bridge Overseer as if service authority remained valid. | refusal added | Operator receives explicit refusal unless override is set. | Future scoped restart for Bridge Overseer exits without restarting it. | Set `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1` for diagnostic restart. | Consider removing from restart service list in later cleanup. |
| Workspace planning surface | `cbo_hub/avatar_web/workspace_v0.py`, `cbo_hub/avatar_web/workspace_v0.html`, `cbo_hub/avatar_web/app.py` | UI/API could appear as current planning authority. | warning added | Workspace UI shows quarantined noncanonical banner; state API exposes authority metadata. | No endpoints disabled; representation only. | Remove banner/metadata if later rehabilitated. | Decide whether to disable mutation endpoints or archive workspace in later pass. |
| Legacy Discord intake direct runtime | `calyx/cbo/discord_intake.py` | Direct `--run` could start legacy Discord transport, conflicting with canonical Discord Gateway. | refusal added | Direct run refuses unless explicit legacy override is set. | Next direct launch exits before connecting Discord. | Set `CALYX_ALLOW_LEGACY_DISCORD_INTAKE=1` for historical/diagnostic use. | Later remove or archive legacy intake launch docs. |
| Legacy station launcher | `Scripts/start_station_calyx.ps1` | Legacy launcher could start `discord_intake` or OpenClaw as if valid Station startup paths. | refusal added | Legacy Discord intake and OpenClaw launch modes now refuse by default with explicit authority messages. | Future use exits before launching noncanonical transport. | Set `CALYX_ALLOW_LEGACY_DISCORD_INTAKE=1` or `CALYX_ALLOW_QUARANTINED_OPENCLAW=1` only for explicit diagnostics. | Later rename/archive launcher. |
| OpenClaw setup/preflight | `Scripts/setup_openclaw_calyx.ps1`, `Scripts/openclaw_preflight.ps1` | Setup/preflight implied OpenClaw integration remained an approved Station path. | refusal added | Operator gets explicit quarantine refusal unless override is set. | Future setup/preflight exits before install/config/preflight actions. | Set `CALYX_ALLOW_QUARANTINED_OPENCLAW=1` only for explicit historical/diagnostic use. | Later archive or move OpenClaw scripts under noncanonical path. |
| CP loops | `Scripts/navigator_triage_loop.ps1`, `Scripts/energy_churn_cp9_loop.ps1`, `Scripts/cp6_cp7_loop.ps1` | Active loops may imply canonical core authority. | left unchanged pending evidence | No new refusal; existing runtime labels remain `unknown`/support-review posture. | No runtime behavior changed. | Not applicable. | Complete simplification review before demotion/quarantine. |
| Stale CP8/CP10 claims | `docs/AGENT_REPOSITORY.md`, missing `tools/cp8_quartermaster.py`, missing `tools/cp10_whisperer.py` | Docs previously implied implemented CP agents. | left unchanged pending evidence | Already demoted in docs; no executable path exists to fence. | No runtime path exists. | Not applicable. | Remove stale claims in later doc cleanup if desired. |

## Explicit Override Variables

These variables are intentionally noisy and should be used only for explicit historical/diagnostic work:

- `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1`
- `CALYX_ALLOW_LEGACY_DISCORD_INTAKE=1`
- `CALYX_ALLOW_QUARANTINED_OPENCLAW=1`

These overrides do not make the target canonical. They only allow manual diagnostic launch of quarantined or legacy paths.

## Restart Position

No services were restarted. This pass modified files only. Already-running noncanonical processes, if present, were not killed because the work order did not authorize a live cleanup/restart pass. Enforcement takes effect on next direct launch, scoped restart, or authorized sunrise.

## Deferred Items

- Live Bridge Overseer process cleanup, if currently running, requires a separate authorized stop/sunrise action.
- Workspace mutation endpoint disablement is deferred because Workspace is embedded in Avatar Web and this pass preserved canonical Avatar Web behavior.
- Final classification of Navigator/Triage, Energy Churn/CP9, and CP6/CP7 loops remains pending simplification evidence.
- OpenClaw directories and skills were not deleted; setup/preflight/legacy launcher execution paths were fenced instead.

## Scope Confirmation

This pass stayed bounded to noncanonical path demotion and quarantine enforcement.
