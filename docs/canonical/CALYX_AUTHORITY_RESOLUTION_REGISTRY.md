# Calyx Authority Resolution Registry

Status: authority-boundary resolution registry
Work order: `WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1`
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Generated: 2026-04-23

This registry resolves the unknowns left by `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`. It separates evidence, inference, and recommendation for each target.

## Resolution Table

| target | implementation reality | integration reality | exercised status | operator relevance | implied authority claim | preserve risk | demotion/quarantine/removal risk | final classification | recommendation |
|---|---|---|---|---|---|---|---|---|---|
| CLI Avatar | Implemented as `cbo_hub/cli_avatar/main.py`, a Rich terminal client posting to CBO Core `/chat`. | Started by `Scripts/start_calyx_core_services.ps1`; stopped by `Scripts/sunset_calyx.ps1`; visible in topology. | Resident process evidence; no independent receipt stream found. | Useful as local fallback client; not required for normal path. | Docs/runtime imply it is part of started station surface. | Treating it as core creates another operator path and UI authority. | Removing/quarantining loses a simple local fallback to `/chat`. | `canonical support` | Preserve as optional client only; no independent authority. |
| Telemetry Gateway | Implemented as authenticated/audited remote ingress in `cbo_hub/telemetry_gateway/app.py`. | Started by sunrise on port 7781; included in service checks and topology. | Startup readiness and audit status exercised; no evidence of normal operator conversation use in this pass. | Relevant for remote support, not normal local operation. | Docs call it remote access and service substrate. | Calling it core widens attack surface and contradicts local-first reduction. | Quarantine/removal could break remote support and audit readiness assumptions. | `canonical support` | Preserve as remote-support ingress; not normal operator path. |
| `STATE.md` | Plain text operational digest with heartbeat, health, checks, topology risk, duplicate services. | Updated/read by state-check scripts, CBO Core, Discord Gateway, runtime truth scripts. | Fresh during inspection; actively injected into responses and heartbeat paths. | High; operator-readable quick state. | Often implied as current station state. | Treating it as sole authority can preserve stale or summarized truth as fact. | Removing it would break readable operator context and existing fast paths. | `canonical support` | Preserve as advisory generated digest; live probes/runtime JSON/receipts remain stronger evidence. |
| Bridge Overseer | Implemented Reflect/Plan/Act/Critique loop in `calyx/cbo/bridge_overseer.py`. | Started by sunrise; stopped by sunset; visible in topology. | Fresh `metrics/bridge_pulse.csv`, but repeated zero objectives, zero tasks, zero dispatches; duplicate/ambiguous in topology. | Current operator value unproven. | Name and docs imply central orchestration authority. | Preserving as canonical keeps false control-plane authority and multiplicity noise. | Quarantine/removal could lose historical metrics or future coordinator substrate. | `quarantined noncanonical` | Exclude from canonical claims; later decide remove from sunrise or reduce to passive metric. |
| Workspace planning surface | Implemented proposal/discussion/approval/failure/snapshot flows under Avatar Web. | Integrated into Avatar Web and CBO Core workspace endpoints. | Exercised heavily through 2026-04-14; dormant in current evidence. | Potentially useful planning UI, but not current normal operator path. | UI/docs imply planning authority and structured proposal lane. | Preserving as canonical keeps dormant extra operator surface and malformed-output burden. | Quarantine/removal could lose a previously useful planning artifact trail. | `quarantined noncanonical` | Preserve as dormant/historical tool; exclude from canonical operator path. |
| `MEMORY.md` continuity | Implemented as curated markdown file. | Loaded by session doctrine for main sessions; no evidence of running services using it as runtime state authority. | Read in operator sessions; daily companion files missing for current day/yesterday; hot/warm memory stale. | High as operator reference; insufficient as runtime continuity. | Doctrine implies curated memory continuity. | Calling it runtime authority creates false continuity and hides missing daily memory. | Demoting too far loses useful long-term operator context. | `canonical support` | Preserve as curated operator reference and partial continuity component; not runtime continuity authority or sole continuity source. |

## Resolved Canonical Language

- `canonical core`: systems that directly start, stop, govern, or expose the active runtime path.
- `canonical support`: implemented, integrated, and useful systems that support the canonical core but must not claim independent authority.
- `quarantined noncanonical`: implemented or historically useful systems that must not participate in current authority claims.
- `removable`: surfaces that can be removed from current claims in a later demotion pass.
- `historical only`: artifacts retained for evidence or traceability, not operation.

## Final Dispositions

- CLI Avatar: `canonical support`
- Telemetry Gateway: `canonical support`
- `STATE.md`: `canonical support`
- Bridge Overseer: `quarantined noncanonical`
- Workspace planning surface: `quarantined noncanonical`
- `MEMORY.md`: `canonical support`, partial continuity component, not runtime continuity authority

## Continuity Resolution

`MEMORY.md` is not canonical runtime continuity authority. It is a curated operator reference used by session doctrine. The current runtime continuity picture is partial:

- Operator doctrine/context: `AGENTS.md`, `SOUL.md`, `USER.md`
- Curated operator memory: `MEMORY.md`
- Daily memory convention: `memory/YYYY-MM-DD.md`, currently incomplete
- Operational digest: `STATE.md`
- Runtime truth: `runtime/*.json` and `runtime/receipts/*`

Recommendation:

Keep `MEMORY.md` as canonical support. Do not call runtime continuity canonical until daily memory practice, operational state, and runtime receipts have a single documented authority relationship.
