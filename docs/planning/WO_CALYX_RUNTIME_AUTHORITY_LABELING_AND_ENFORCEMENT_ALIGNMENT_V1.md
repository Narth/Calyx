---
status: archived
owner: station
last_reviewed_utc: "2026-04-25"
doctrine_scope: governed
---

# WO_CALYX_RUNTIME_AUTHORITY_LABELING_AND_ENFORCEMENT_ALIGNMENT_V1

Status note: minimal implementation pass complete
Date: 2026-04-23
Baseline: `calyx-baseline-2026-04-21` / `dc57c25b3edaf361ec8f23f9219390d0c218d3d3`
Authority source:
- `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md`
- `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md`
- `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md`

## Purpose

Align existing operator-facing runtime truth surfaces with the resolved Station Calyx authority model. This pass changes labels and representation only. It does not delete code, stop processes, start processes, add integrations, or restructure runtime control.

## Implemented Labeling Behavior

Preferred status vocabulary:
- `canonical core`
- `canonical support`
- `quarantined noncanonical`
- `deprecated`
- `historical`
- `unknown`

| surface name | file/path | previous authority ambiguity | implemented authority labeling/alignment change | behavior changed or representation only | follow-on enforcement still needed |
|---|---|---|---|---|---|
| Sunrise operator output | `Scripts/start_calyx_core_services.ps1` | Output treated all launched services as an undifferentiated core set. | Startup messages now label CBO Hub services as `canonical core` or `canonical support`; Bridge Overseer is visibly `quarantined noncanonical`; sunrise receipt includes `service_authority_status`. | Representation only | Yes, later pass should decide whether quarantined services remain launched. |
| CBO Hub service probe | `Scripts/check_calyx_core_services.ps1` | Filename and comments implied all probed services are core. | Comments now clarify this probe keeps legacy checks output stable; authority labels live in sunrise/STATE/heartbeat/snapshot/topology. | Representation only | No behavior change; future rename may be considered separately. |
| STATE runtime block helper | `Scripts/runtime_truth_contract.ps1` | STATE-adjacent fields did not state that STATE is support/advisory. | Runtime block now supports `state_authority_status`, `state_authority_note`, and `runtime_topology_authority_summary`. | Representation only | Existing STATE refresh must run normally to render new fields. |
| STATE/heartbeat/snapshot writer | `Scripts/update_state_checks.ps1` | Telemetry appeared beside core services without authority class; `runtime_truth_canonical` wording implied stronger authority. | Adds service-level `authority_status`; marks STATE as `canonical support`; marks heartbeat and service snapshot as generated support evidence, not sole liveness authority. | Representation only | Normal refresh required to update runtime artifacts. |
| Station health JSON | `Scripts/station_health_loop.ps1` | Health artifact was core evidence but had no explicit authority boundary. | Adds `authority_status=canonical core` and note that health is not sole Station authority. | Representation only | Running loop must refresh normally to emit new fields. |
| Runtime topology snapshot | `calyx/governance/runtime_topology.py`, `Scripts/runtime_topology_snapshot.py` | Topology identified declared services but did not expose canonical core/support/quarantine status. | Adds authority vocabulary, service authority labels, auxiliary labels, active authority counts, operator table authority status, and topology authority summary. Failure fallback emits compatible authority fields. | Representation only | Normal topology refresh required to update snapshot. |

## Authority Labels Implemented

| system | implemented runtime label |
|---|---|
| Dev Harness | `canonical core` |
| CBO Core | `canonical core` |
| Avatar Web | `canonical core` |
| Discord Gateway | `canonical core` |
| Station health loop | `canonical core` |
| Service failure watch | `canonical core` |
| Telemetry Gateway | `canonical support` |
| CLI Avatar | `canonical support` |
| Bridge Overseer | `quarantined noncanonical` |
| Navigator/Triage loop | `unknown` |
| Energy Churn/CP9 loop | `unknown` |
| CP6/CP7 loop | `unknown` |
| Runtime truth observer auxiliaries | `canonical support` |
| Station patch/sunrise auxiliaries | `canonical support` |

## Restart Position

No restart was performed. This pass edited scripts and modules only. Existing running processes will not reflect all label changes until their next normal refresh or next authorized sunrise. A restart is not strictly required for repository alignment and was not performed under the bounded scope.

## Deferred Items

- Decide whether Bridge Overseer should remain launched by sunrise, be quarantined at runtime, or be removed in a later authorized implementation pass.
- Decide final authority status for Navigator/Triage, Energy Churn/CP9, and CP6/CP7 loops after simplification review.
- Consider a later non-breaking rename or wrapper clarification for `check_calyx_core_services.ps1` and `start_calyx_core_services.ps1`, whose names still contain historical "core" language.
- Add UI-visible noncanonical labeling for workspace planning surface if it remains reachable.

## Scope Confirmation

This pass stayed bounded to runtime authority labeling/alignment. It did not introduce new capabilities, new integrations, new control planes, or new governance layers.
