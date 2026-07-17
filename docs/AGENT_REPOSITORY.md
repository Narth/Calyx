# Agent Repository - Station Calyx

Status: historical mixed-status index, 2026-04-23.

This document is not a canonical control plane. It lists agent, skill, and service surfaces built over Station Calyx development, but several entries are now canonical support, quarantined noncanonical, deprecated, or missing. Use `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md` for current authority.

Last updated: 2026-04-23

---

## 1. Runtime Surfaces Observed Around Sunrise

| Component | Entrypoint | BloomOS relevance |
|---|---|---|
| Dev Harness | `uvicorn cbo_hub.dev_harness.app:app` | Repo list/search for CBO |
| CBO Core | `uvicorn cbo_hub.cbo_core.app:app` | `/chat`, intent, governance |
| Avatar Web | `uvicorn cbo_hub.avatar_web.app:app` | Chat + Whiteboard |
| Telemetry Gateway | `uvicorn cbo_hub.telemetry_gateway.app:app` | Canonical support only; remote access |
| Discord Gateway | `python -m calyx.cbo.discord_gateway` | Discord to CBO relay |
| Station health loop | `Scripts\station_health_loop.ps1` | CPU/RAM/GPU to `runtime/station_health.json` |
| Navigator + Triage loop | `Scripts\navigator_triage_loop.ps1` | `navigator.lock`, `triage.lock` |
| Energy Churn + CP9 loop | `Scripts\energy_churn_cp9_loop.ps1` | `energy_churn_report.json`, `cp9.lock` |
| CP6 + CP7 loop | `Scripts\cp6_cp7_loop.ps1` | `cp6.lock` harmony, `cp7.lock` drift |

---

## 2. Support / Completion-Required Surfaces

These agents read/write STATE, station_health, or outgoing locks. They may be active or useful, but this section does not grant canonical core authority.

| Agent | Entrypoint | Output | BloomOS value |
|---|---|---|---|
| Navigator | `Scripts\navigator.ps1` | `outgoing/navigator.lock` | interval_status, entropy_tier, cadence |
| Triage Orchestrator | `Scripts\triage_orchestrator.ps1` | `outgoing/triage.lock` | health_summary, latency_ms, recommendations |
| update_state_checks | `Scripts\update_state_checks.ps1` | `STATE.md` | heartbeat_ts, health, entropy_tier |
| Energy Churn Analyzer | `Scripts\energy_churn_analyzer.ps1` | `energy_churn_report.json` | Trend analysis from station_health_history |
| CP9 Auto-Tuner | `tools\cp9_auto_tuner.py` | `outgoing/cp9.lock` | Tuning from nav/triage/churn |

---

## 3. CP Agents (Legacy / Design - Require Wiring)

From `COMPENDIUM.md`. This section contains mixed statuses. CP6/CP7/CP9 have active loop evidence; CP8 and CP10 entrypoints are documented claims only and should not be treated as implemented authority.

| Agent | Entrypoint | Output | Notes |
|---|---|---|---|
| CP6 Sociologist | `tools/cp6_sociologist.py` | `outgoing/cp6.lock` | Wired via `cp6_cp7_loop`; completion/simplification required |
| CP7 Chronicler | `tools/cp7_chronicler.py`, `Scripts/agent_cp7.py` | `outgoing/cp7.lock` | Wired via `cp6_cp7_loop`; completion/simplification required |
| CP8 Quartermaster | `tools/cp8_quartermaster.py` | `outgoing/cp8.lock` | Deprecated documented claim; entrypoint not verified/present in current reduction evidence |
| CP9 Auto-Tuner | `tools/cp9_auto_tuner.py` | `outgoing/cp9.lock` | Wired via `energy_churn_cp9_loop`; completion/simplification required |
| CP10 Whisperer | `tools/cp10_whisperer.py` | `outgoing/cp10.lock` | Deprecated documented claim; entrypoint not verified/present in current reduction evidence |

---

## 4. Skills (OpenClaw / Agent Integrations)

Status: quarantined noncanonical. These entries must not be treated as current Station Calyx integrations without a later approved authority pass.

| Skill | Path | Purpose |
|---|---|---|
| calyx-cbo-bridge | `skills/calyx-cbo-bridge/` | Historical/quarantined get_state, send_to_cbo, sponsorship, execute surface |
| ai-workstation | `skills/ai-workstation/` | Historical/quarantined Discord, RDP, models, workspace-state surface |

---

## 5. BloomOS Onboarding Priority

Status: historical. This sequence is retained as development history, not current canonical expansion authority.

Phase 1 - Enrich STATE and locks:
1. Run `update_state_checks` on each heartbeat if still authorized by current heartbeat policy.
2. Run Navigator periodically only if its support role remains approved.
3. Run Triage only if its support role remains approved.

Phase 2 - Trend and tuning:
4. Energy Churn Analyzer runs via `energy_churn_cp9_loop` where currently wired.
5. CP9 Auto-Tuner runs after Energy Churn in the same loop where currently wired.

Phase 3 - Chronicler and harmony:
6. CP7 Chronicler is wired via `cp6_cp7_loop`.
7. CP6 Sociologist is wired via `cp6_cp7_loop`.

---

## 6. IDE Toolbox

See `ide_toolbox/` for merged Cursor + VS Code config. Treat IDE tooling as support infrastructure, not Station Calyx runtime authority.
