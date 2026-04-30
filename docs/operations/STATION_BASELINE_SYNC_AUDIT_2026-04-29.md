---
status: active
owner: station
last_reviewed_utc: "2026-04-29"
doctrine_scope: governed
---

# Station Baseline Sync Audit - 2026-04-29

## Purpose

This pass establishes a repeatable separation between:

- Git baseline as rebuildable Station body
- runtime telemetry as local node experience
- curated continuity as operator-approved memory
- receipts and ledgers as evidence

No files were staged, committed, deleted, or moved during this pass.

## Artifacts Added

- `docs/canonical/STATION_BASELINE_MANIFEST.md`
- `Scripts/baseline_parity_check.ps1`

Generated local runtime artifacts:

- `runtime/baseline_parity_report.json`
- `runtime/node_manifest.json`

The runtime artifacts are node-local and ignored by default.

## Ignore Hardening

`.gitignore` was extended for local test/context artifacts that should not be baseline material:

- `.pytest_*/`
- `.cbo_pytest_min_probe/`
- `skills/user_contexts.json`

Existing ignore posture already excludes `runtime/`, `logs/`, `outgoing/`, `memory/`, local OpenClaw identity/device/credential surfaces, and other generated state.

## Current Classification

`Scripts/baseline_parity_check.ps1` reported:

| class | count |
|---|---:|
| canonical_candidate | 313 |
| operator_decision | 36 |
| local_node_state | 0 |
| scratch_or_generated | 0 |

Current branch:

```text
wo-sunrise-canonical-bootpath-v1
```

Current HEAD:

```text
dc57c25b3edaf361ec8f23f9219390d0c218d3d3
```

## Interpretation

The visible worktree is no longer dominated by local runtime contamination. It is mostly canonical candidate source plus operator-decision surfaces.

The remaining operator-decision surfaces are chiefly:

- `STATE.md`
- tracked deletion of `openclaw/calyx-profile.json`
- historical OpenClaw source/config surfaces under `openclaw/`
- local/plugin/workstation capability surfaces under `skills/`

These require explicit baseline curation rather than automatic cleanup.

## Baseline Doctrine

Git restores the Station structure.

Curated memory restores continuity.

Receipts prove events.

Telemetry describes this node.

No class may silently impersonate another.

## Next Safe Step

Run the parity checker before any baseline commit or cross-node sync:

```powershell
.\Scripts\baseline_parity_check.ps1
```

Then review `runtime/baseline_parity_report.json` and decide the `operator_decision` set explicitly.
