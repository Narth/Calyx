---
status: archived
owner: station
last_reviewed_utc: "2026-04-25"
doctrine_scope: governed
---

# WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1

Status note: planning/resolution-only
Follows: `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Created: 2026-04-23

## Purpose

Resolve the remaining authority-boundary unknowns before code/path demotion or runtime enforcement work proceeds.

This pass does not authorize runtime changes, service restarts, code deletion, path demotion in code, new features, new integrations, or new control planes.

## Evidence Sources

- `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md`
- `docs/canonical/CALYX_CANONICAL_OPERATOR_PATH.md`
- `docs/canonical/CALYX_CANONICAL_CONTROL_PLANE.md`
- `docs/canonical/CALYX_CANONICAL_CONTINUITY_MODEL.md`
- `Scripts/start_calyx_core_services.ps1`
- `cbo_hub/cli_avatar/main.py`
- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/avatar_web/app.py`
- `calyx/cbo/bridge_overseer.py`
- `STATE.md`
- `MEMORY.md`
- `SOUL.md`
- `AGENTS.md`
- `runtime/runtime_topology_snapshot.json`
- `runtime/station_health.json`
- `runtime/telemetry_gateway_audit_status.json`
- `cbo_hub/logs/telemetry_gateway_audit.jsonl`
- `metrics/bridge_pulse.csv`
- `runtime/workspace_v0/`

## Final Authority Recommendations

| target | final classification | recommendation |
|---|---|---|
| CLI Avatar operator relevance | `canonical support` | Preserve as optional local `/chat` client only; no independent authority. |
| Telemetry Gateway | `canonical support` | Preserve as remote-support ingress only; not the normal operator path and not core reasoning authority. |
| `STATE.md` authority boundary | `canonical support` | Preserve as generated/advisory operational context; not durable memory and not sole runtime truth. |
| Bridge Overseer | `quarantined noncanonical` | Quarantine from authority claims; active process currently provides no task-control value. |
| Workspace planning surface | `quarantined noncanonical` | Quarantine as historical/dormant planning tool; not normal operator path. |
| `MEMORY.md` continuity authority | `canonical support` | Preserve as curated operator reference and partial continuity component; not runtime continuity authority and not sole authority. |

## Target Resolutions

### CLI Avatar

Evidence:

- `Scripts/start_calyx_core_services.ps1` starts `cbo_hub.cli_avatar.main` in a normal window.
- `cbo_hub/cli_avatar/main.py` is a thin interactive client that posts to `http://127.0.0.1:7778/chat`.
- Runtime topology names `CLI Avatar` as a resident process.

Inference:

- CLI Avatar is implemented, integrated, and visibly launched.
- It does not emit independent runtime truth or govern anything; it depends on CBO Core.
- Its operator value is fallback/local interaction, not canonical authority.

Recommendation:

- Classify as `canonical support`.
- Preserve only as optional local client to `/chat`.
- Do not describe it as a separate operator path, control plane, or authority surface.

### Telemetry Gateway

Evidence:

- `Scripts/start_calyx_core_services.ps1` starts `cbo_hub.telemetry_gateway.app:app` on `0.0.0.0:7781`.
- `cbo_hub/telemetry_gateway/app.py` documents remote command ingress, `TELEMETRY_SECRET`, client identity namespacing, and append-only audit logging.
- `cbo_hub/logs/telemetry_gateway_audit.jsonl` contains repeated `startup_readiness` entries.
- `runtime/telemetry_gateway_audit_status.json` reports `trust_state: trusted` from 2026-04-18 startup readiness.

Inference:

- Telemetry Gateway is implemented, integrated, and exercised at startup/audit level.
- Evidence supports remote-support capability, not normal operator conversation use.
- Treating it as core operator path would widen authority and exposure beyond current single-operator workstation reality.

Recommendation:

- Classify as `canonical support`.
- Preserve as optional remote-support ingress with audit and auth boundaries.
- Do not treat as the single canonical operator path.

### STATE.md

Evidence:

- `STATE.md` currently contains fresh `heartbeat_ts`, service checks, health status, runtime topology risk, duplicate services, and stale-runtime labels.
- `Scripts/update_state_checks.ps1`, `Scripts/runtime_truth_contract.ps1`, `calyx/cbo/discord_gateway.py`, and `cbo_hub/cbo_core/app.py` read or refresh `STATE.md`.
- CBO Core uses `STATE.md` for heartbeat fast paths and context injection.

Inference:

- `STATE.md` is implemented, integrated, exercised, and operator-relevant.
- Its own content says runtime truth may be stale and points to live probes/TTL.
- It is an operational context digest, not durable memory and not sole runtime authority.

Recommendation:

- Classify as `canonical support`.
- Preserve as generated/advisory operational context.
- Runtime authority remains with live probes, fresh runtime JSON, and receipts; `STATE.md` summarizes those surfaces.

### Bridge Overseer

Evidence:

- `Scripts/start_calyx_core_services.ps1` starts `calyx.cbo.bridge_overseer`.
- `calyx/cbo/bridge_overseer.py` implements Reflect, Plan, Act, Critique over objectives.
- `metrics/bridge_pulse.csv` is fresh but repeatedly reports `objectives=0 tasks=0 dispatched=0`.
- Runtime topology reports `bridge_overseer` as duplicate/ambiguous.

Inference:

- Bridge Overseer is implemented, integrated, and running.
- Current exercise does not demonstrate operator-relevant control value.
- Its naming and docs imply more authority than current runtime evidence supports.

Recommendation:

- Classify as `quarantined noncanonical`.
- Preserve only as historical/current experimental process until follow-on work decides whether to remove from sunrise or reduce to passive metrics.
- Do not include in canonical control-plane authority.

### Workspace Planning Surface

Evidence:

- `cbo_hub/avatar_web/workspace_v0.py` and `cbo_hub/avatar_web/app.py` implement workspace proposal, discussion, approval, failure, and snapshot flows.
- `runtime/workspace_v0/` contains submissions, snapshots, proposals, approvals, and failures, last active on 2026-04-14.
- Current canonical operator path uses `/chat`; the prior reduction pass classified workspace as dormant.

Inference:

- Workspace planning is implemented and historically exercised.
- It is not current daily operator flow, not part of startup authority, and not required for minimal Calyx.
- It has future value, but preserving it as canonical would keep an extra operator surface alive without current necessity.

Recommendation:

- Classify as `quarantined noncanonical`.
- Preserve as historical/dormant planning tool for now.
- Exclude from normal operator-path and core-control-plane claims.

### MEMORY.md And Continuity

Evidence:

- `AGENTS.md` requires `SOUL.md`, `USER.md`, today/yesterday daily memory, and `MEMORY.md` only in main session.
- `MEMORY.md` exists and is human-readable curated memory.
- `memory/2026-04-23.md` and `memory/2026-04-22.md` were missing during the previous pass.
- `memory/hot/*` and `memory/warm/*` exist but are stale January scaffolding.
- CBO runtime services use `STATE.md` and runtime JSON for operational context; no evidence shows `MEMORY.md` is consumed as runtime state authority by the running services.

Inference:

- `MEMORY.md` is operator/session continuity support.
- It is not canonical runtime continuity authority because it is not live-integrated into runtime supervision, liveness, or service authority.
- No single robust runtime continuity model currently exists; current continuity is partial and split between doctrine files, curated memory, daily memory convention, `STATE.md`, and runtime receipts.

Recommendation:

- Classify `MEMORY.md` as `canonical support`, not runtime authority.
- Describe it as curated operator reference and partial continuity component.
- Treat daily memory as completion-required if it remains doctrine.
- Keep `STATE.md` and runtime JSON as operational truth, not memory.

## Operator Impact

- Normal operation remains centered on `/chat` through Avatar Web or Discord Gateway.
- CLI Avatar is available as optional support but not a separate authority path.
- Telemetry Gateway remains remote-support infrastructure, not the default operator path.
- `STATE.md` remains useful but must not be read as sole truth.
- Bridge Overseer and workspace planning should not appear in current canonical claims.
- Continuity is not fully solved; `MEMORY.md` is useful but insufficient as runtime continuity authority.

## Follow-On Implementation Prerequisites

Future implementation work, if authorized separately, should:

- Update startup docs to label CLI Avatar and Telemetry Gateway as support surfaces.
- Remove Bridge Overseer from canonical authority claims before any runtime demotion.
- Quarantine workspace planning docs and UI claims before deciding whether to preserve or retire it.
- Add explicit wording that `STATE.md` is a digest of operational truth, not authority by itself.
- Resolve the daily memory doctrine mismatch before calling continuity canonical.

## Residual Unknowns

No unresolved authority-boundary unknowns remain for the six required targets. Implementation details for future demotion are intentionally out of scope.
