---
status: archived
owner: station
last_reviewed_utc: "2026-04-25"
doctrine_scope: governed
---

# WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1

Status note: completed planning/documentation execution pass
Date: 2026-04-23
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Follows:
- `WO_CALYX_CORE_REDUCTION_AND_CANONICALIZATION_V1`
- `WO_CALYX_CANONICAL_AUTHORITY_RESOLUTION_V1`

## Purpose

Align Station Calyx documentation and path labels with the resolved authority model without changing runtime behavior.

This pass is documentation-and-path-canonicalization only. It does not authorize service restarts, code demotion, production deletion, new features, new integrations, or runtime enforcement changes.

## Authority Decisions Reflected

| surface | resolved disposition | authority boundary |
|---|---|---|
| CLI Avatar | canonical support | Optional local client to governed `/chat`; no independent operator authority. |
| Telemetry Gateway | canonical support | Remote-support ingress to CBO Core; not core reasoning authority and not the normal operator path. |
| `STATE.md` | canonical support | Generated operational digest; not sole authoritative truth. |
| Bridge Overseer | quarantined noncanonical | Residual historical/control-plane surface; not canonical orchestration. |
| Workspace planning surface | quarantined noncanonical | Historical/dormant planning tool; not canonical operator path. |
| `MEMORY.md` | canonical support | Curated operator reference and partial continuity component; not runtime continuity authority and not sole continuity authority. |

## Non-Behavioral Edits Performed

| path | change type | correction |
|---|---|---|
| `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md` | documentation-only | Removed Telemetry Gateway and `MEMORY.md` from proposed core; added canonical support section; clarified curated memory status. |
| `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md` | documentation-only | Created reduced system map separating core, support, quarantine, deprecated, historical, and unknown surfaces. |
| `docs/canonical/CALYX_DOCUMENT_STATUS_REGISTRY.md` | documentation-only | Created registry of reviewed document statuses and remaining correction targets. |
| `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md` | documentation-only | Created registry of misleading path/entrypoint authority claims and later demotion targets. |
| `cbo_hub/docs/CALYX_CORE_SERVICES.md` | documentation-only | Relabeled service list as core/support map; Telemetry Gateway and CLI Avatar are support; `STATE.md` is not sole truth. |
| `calyx/cbo/README.md` | documentation-only | Added quarantine notice for Bridge Overseer. |
| `docs/AGENT_REPOSITORY.md` | documentation-only | Relabeled as mixed-status index; marked CP8/CP10 and OpenClaw skills noncanonical. |
| `docs/STATION_STACK_POLICY.md` | documentation-only | Distinguished core services from support services and clarified Telemetry Gateway support role. |
| `SOUL.md` | documentation-only | Clarified core/support service boundaries and memory/state authority boundaries. |
| `MEMORY.md` | documentation-only | Added authority note that `MEMORY.md` is curated support only, not runtime continuity authority. |

## Claims Demoted

| claim | demotion |
|---|---|
| Telemetry Gateway is a core service | Demoted to canonical support. |
| CLI Avatar can imply operator/control authority | Clarified as canonical support client only. |
| `STATE.md` is the build path authority | Clarified as generated digest, not sole truth. |
| `MEMORY.md` is long-term/runtime memory authority | Clarified as curated operator reference and partial continuity component only. |
| Bridge Overseer orchestrates Station Calyx | Marked quarantined noncanonical. |
| Workspace planning surface is a normal operator path | Marked quarantined noncanonical. |
| CP8/CP10 documented agent ecology is live | Marked documented but missing/noncanonical. |
| OpenClaw skills imply active Station integrations | Marked quarantined noncanonical. |

## Path and Entrypoint Review

See `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md` for explicit path-level status.

This pass identifies demotion/removal targets only. It does not rename, delete, disable, or quarantine runtime paths in code.

## Remaining Runtime Enforcement Targets

- Sunrise validation should distinguish canonical core from canonical support instead of treating all started services as core.
- Health and topology surfaces should label `core`, `canonical support`, `quarantined noncanonical`, `deprecated`, `historical`, and `unknown`.
- Bridge Overseer process/startup presence should be reconciled in a later implementation pass.
- Workspace planning path should receive explicit noncanonical runtime labeling or be removed from operator-facing launch surfaces in a later pass.
- `STATE.md` generation should retain advisory wording and cross-link to stronger runtime truth surfaces.
- Continuity tooling should prevent `MEMORY.md` from being presented as sole runtime continuity authority.

## Acceptance Notes

This pass produced the required canonical system map, document status registry, path/entrypoint demotion registry, and governance receipt. All edits are documentation-only. No runtime behavior was changed.
