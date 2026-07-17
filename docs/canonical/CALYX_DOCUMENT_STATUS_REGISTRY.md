# Calyx Document Status Registry

Status: canonical registry
Date: 2026-04-23
Work order: `WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1`

Status vocabulary: `canonical core`, `canonical support`, `quarantined noncanonical`, `deprecated`, `historical`, `unknown`.

## Reviewed Documents

| path | previous implied status | corrected status | reason for correction | change type | further runtime enforcement needed |
|---|---|---|---|---|---|
| `docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md` | Canonical reduction registry with some stale core labels | canonical core | Registry remains authority surface, but Telemetry Gateway and `MEMORY.md` were corrected to support. | documentation-only | yes, sunrise/topology should eventually label support separately |
| `docs/canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md` | Canonical authority resolution | canonical core | Starting authority for this pass; no conflict found. | reviewed-only | no |
| `docs/canonical/CALYX_CANONICAL_OPERATOR_PATH.md` | Canonical operator path | canonical core | Already reflects `/chat` and support boundaries. | reviewed-only | no |
| `docs/canonical/CALYX_CANONICAL_CONTROL_PLANE.md` | Canonical control plane | canonical core | Already distinguishes support and quarantine surfaces. | reviewed-only | yes, runtime health/topology still needs labels |
| `docs/canonical/CALYX_CANONICAL_CONTINUITY_MODEL.md` | Canonical continuity model | canonical core | Already states `MEMORY.md` is not runtime continuity authority. | reviewed-only | yes, continuity tooling remains fragmented |
| `docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md` | missing | canonical core | Created to expose reduced core/support/quarantine map. | documentation-only | yes |
| `docs/canonical/CALYX_LOCAL_MCP_SERVER.md` | missing | canonical support | Created to document the approved local read-only MCP support server and distinguish it from quarantined cloud/MCP workflow docs. | documentation-only | no |
| `docs/canonical/CALYX_DOCUMENT_STATUS_REGISTRY.md` | missing | canonical core | Created to record document statuses and corrections. | documentation-only | no |
| `docs/canonical/CALYX_PATH_AND_ENTRYPOINT_DEMOTION_REGISTRY.md` | missing | canonical core | Created to record misleading path and launcher authority claims. | documentation-only | yes |
| `docs/planning/WO_CALYX_DOC_AND_PATH_CANONICALIZATION_EXECUTION_V1.md` | missing | canonical support | Created as execution record for this pass. | documentation-only | no |
| `cbo_hub/docs/CALYX_CORE_SERVICES.md` | Canonical core services list | canonical support | Corrected to core/support service map; Telemetry Gateway is support, not core. | documentation-only | yes, service probes should expose status classes |
| `docs/STATION_STACK_POLICY.md` | Stack policy treating all four services as core | canonical support | Corrected core/support distinction and `STATE.md` advisory boundary. | documentation-only | yes |
| `SOUL.md` | Doctrine implying Telemetry as core and `MEMORY.md`/`STATE.md` stronger authority | canonical support | Clarified support boundaries without changing doctrine role. | documentation-only | no |
| `MEMORY.md` | Curated memory implying refinement mechanisms and long-term memory authority | canonical support | Added authority note: operator reference only, not runtime continuity authority. | documentation-only | no |
| `docs/AGENT_REPOSITORY.md` | Canonical agent/service index | historical | Relabeled as mixed-status index; missing and quarantined surfaces marked. | documentation-only | yes, later doc demotion/removal likely |
| `calyx/cbo/README.md` | Bridge Overseer runtime authority | quarantined noncanonical | Added visible quarantine notice. | documentation-only | yes, later runtime demotion if approved |
| `docs/CBO_CONTRACT.md` | Legacy CBO/outgoing canonical contract | historical | Not edited in this pass; should be demoted or labelled in follow-on doc cleanup. | reviewed-only | yes |
| `docs/CALYX_CLI_GUIDE.md` | CLI can steer station operations | canonical support | Should be corrected to support-only if still operator-facing. | reviewed-only | yes |
| `docs/OPENCLAW_CALYX_INTEGRATION.md` | Integration documentation | quarantined noncanonical | Already marked deprecated/forbidden in existing documentation. | reviewed-only | no |
| `docs/CLOUD_SYNC_WORKFLOW.md` | Cloud/MCP workflow authority | quarantined noncanonical | Future-value workflow surface outside reduced core. | reviewed-only | yes |
| `docs/skills_integration.md` | Skills/MCP integration authority | quarantined noncanonical | Missing referenced active local tooling; not current core. | reviewed-only | yes |
| `docs/MEMORY_ARCHITECTURE_v1.0.md` | Memory architecture authority | historical | Hot/warm memory scaffold is not current runtime continuity. | reviewed-only | yes |

## Correction Rules Applied

- Support systems must not be described as core.
- Quarantined systems must carry visible noncanonical status when edited.
- `MEMORY.md` must not be described as runtime continuity authority.
- `STATE.md` must not be described as sole authoritative truth.
- Historical docs may remain as history only if they stop implying current authority.
