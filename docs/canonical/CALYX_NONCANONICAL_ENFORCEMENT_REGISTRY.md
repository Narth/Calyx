# Calyx Noncanonical Enforcement Registry

Status: canonical registry
Date: 2026-04-23
Work order: `WO_CALYX_NONCANONICAL_PATH_DEMOTION_AND_QUARANTINE_ENFORCEMENT_V1`

This registry records executable/operator-facing enforcement for systems already classified as noncanonical, quarantined, deprecated, historical, or unresolved. It does not grant new authority to any target.

## Enforcement Table

| target name | path(s) | prior implied authority | implemented action | operator impact | runtime impact | rollback notes | further work required |
|---|---|---|---|---|---|---|---|
| Bridge Overseer direct runtime | `calyx/cbo/bridge_overseer.py` | Central orchestration/control-plane authority | refusal added | Direct launch fails closed with quarantine explanation. | No effect until next direct launch. | `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1` for explicit diagnostics. | Later archive/remove/rehabilitate decision. |
| Bridge Overseer sunrise residency | `Scripts/start_calyx_core_services.ps1` | Normal sunrise participation implied canonical runtime authority. | quarantined | Sunrise output states Bridge Overseer is not started unless explicitly overridden. | Next sunrise skips Bridge Overseer by default. | `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1`. | Later remove from service lists/docs if approved. |
| Bridge Overseer scoped restart | `Scripts/restart_service.ps1` | Restart helper treated Bridge Overseer like normal service. | refusal added | Restart command refuses by default. | Future restart attempts fail closed. | `CALYX_ALLOW_QUARANTINED_BRIDGE_OVERSEER=1`. | Later remove from restart allowlist. |
| Workspace planning UI/API | `cbo_hub/avatar_web/workspace_v0.html`, `cbo_hub/avatar_web/app.py`, `cbo_hub/avatar_web/workspace_v0.py` | Planning/control surface could appear current/canonical. | warning added | UI banner and state API authority metadata mark it quarantined noncanonical. | No endpoint disabled. | Remove labels only if later rehabilitated. | Decide archive/read-only/disable policy later. |
| Legacy Discord intake | `calyx/cbo/discord_intake.py`, `Scripts/start_station_calyx.ps1` | Alternate Discord transport could present as Station ingress. | refusal added | Direct/legacy launch refuses unless explicit override. | Next launch exits before Discord connection. | `CALYX_ALLOW_LEGACY_DISCORD_INTAKE=1`. | Later archive/remove legacy launcher. |
| OpenClaw launch/setup/preflight | `Scripts/start_station_calyx.ps1`, `Scripts/setup_openclaw_calyx.ps1`, `Scripts/openclaw_preflight.ps1` | External integration path could present as Station authority. | refusal added | Setup/preflight/legacy launch refuse unless explicit override. | Future actions exit before OpenClaw setup or launch. | `CALYX_ALLOW_QUARANTINED_OPENCLAW=1`. | Later move/archive OpenClaw scripts and skills. |
| Navigator/Triage loop | `Scripts/navigator_triage_loop.ps1` | Active loop may imply canonical authority. | left unchanged pending evidence | No new fence. | No change. | Not applicable. | Simplification/final authority decision required. |
| Energy Churn/CP9 loop | `Scripts/energy_churn_cp9_loop.ps1` | Active loop may imply tuning authority. | left unchanged pending evidence | No new fence. | No change. | Not applicable. | Simplification/final authority decision required. |
| CP6/CP7 loop | `Scripts/cp6_cp7_loop.ps1` | Active loop may imply CP authority. | left unchanged pending evidence | No new fence. | No change. | Not applicable. | Simplification/final authority decision required. |
| CP8/CP10 stale claims | `docs/AGENT_REPOSITORY.md`, missing `tools/cp8_quartermaster.py`, missing `tools/cp10_whisperer.py` | Documented-but-missing CP agents. | left unchanged pending evidence | Already demoted in docs; no executable path to fence. | No runtime path exists. | Not applicable. | Remove stale docs in later cleanup if desired. |

## Enforcement Rule

Quarantine overrides do not make a target canonical. They only allow explicit historical or diagnostic use while preserving the visible noncanonical boundary.
