---
status: active
owner: station
last_reviewed_utc: "2026-04-21"
doctrine_scope: governed
---

# STATION_REPO_BASELINE_CLASSIFICATION_2026-04-21

## Purpose

This pass classifies the current worktree so baseline preparation can proceed without mixing canonical source, local-only state, generated artifacts, and historical surfaces.

This is a read-only classification pass. No files were deleted, ignored, staged, committed, or moved.

## Worktree Summary

| measure | value |
|---|---:|
| tracked modified files | `82` |
| tracked deletions | `2` |
| untracked paths | `259` |
| visible porcelain entries | `343` |

## Classification Buckets

### 1. Canonical source/work to retain

These paths appear to be legitimate Station source, governance, planning, or validation work that should remain in repo scope and be normalized into version control after review.

Representative areas:

- tracked modifications:
  - `Scripts/` (`7`)
  - `calyx/` (`18`)
  - `cbo_hub/` (`5`)
  - `docs/` (`35`)
  - `benchmarks/` (`3`)
- untracked source additions:
  - `Scripts/` (`53`)
  - `calyx/` (`36`)
  - `cbo_hub/` (`13`)
  - `docs/` (`84`)
  - `tests/` (`36`)
  - `tools/` (`13`)
  - `governance/` (`3`)
  - `policy/` (`8`)

Representative canonical-source examples:

- `Scripts/runtime_truth_contract.ps1`
- `Scripts/runtime_topology_snapshot.py`
- `Scripts/restart_service.ps1`
- `calyx/governance/runtime_topology.py`
- `calyx/kernel/swarm_work_envelope.py`
- `calyx/kernel/swarm_trace.py`
- `calyx/kernel/swarm_sandbox.py`
- `cbo_hub/avatar_web/app.py`
- `docs/operations/STATION_INTERRUPTION_AND_RECOVERY_MODEL.md`
- `docs/operations/STATION_EXTERNAL_CAPABILITY_DECLARATION_2026-04-17.md`
- `docs/planning/WO_SWARM_EXECUTION_ENVELOPE_AND_WORKER_LEASES_V1.md`
- `tests/test_station_interruption_governance.py`

Working classification:

- **keep in repo scope**
- **review and commit intentionally**

### 2. Local-only operator state

These paths should not be part of a canonical baseline commit. They represent local identity, approvals, workspace state, or operator continuity.

Confirmed local-only paths:

- `.openclaw/workspace-state.json`
- `openclaw/credentials/discord-allowFrom.json`
- `openclaw/credentials/discord-pairing.json`
- `openclaw/devices/paired.json`
- `openclaw/devices/pending.json`
- `openclaw/identity/device-auth.json`
- `openclaw/identity/device.json`
- `openclaw/exec-approvals.json`
- `openclaw/workspace-state.json`
- `skills/user_contexts.json`
- `cbo_hub/data/whiteboard_tasks.json`
- `cbo_hub/data/workspace_discussion.json`
- `cbo_hub/data/workspace_live_board.json`
- `cbo_hub/data/workspace_meta.json`
- `cbo_hub/data/workspace_undo_state.json`

Working classification:

- **remove from repo scope**
- **ignore locally**

### 3. Generated runtime artifacts

The current `.gitignore` correctly excludes `runtime/`, `memory/`, and other generated surfaces from tracking. There are no tracked files under `runtime/` or `memory/`.

However, generated-state-like files still exist under source-looking paths:

- `cbo_hub/data/*`
- `.openclaw/workspace-state.json`
- `openclaw/workspace-state.json`
- `skills/user_contexts.json`

Working classification:

- **treat as generated/local state**
- **exclude from baseline**

### 4. Temp / scratch / analysis output

These paths are not baseline material:

- `tmp_lifecycle_case2/STATE.md`
- `tmp_lifecycle_case2b/STATE.md`
- `tmp_lifecycle_case3/STATE.md`
- `tmp_lifecycle_case3b/STATE.md`
- `.worktrees/audit/`
- `analysis/anthropic_skill_pass__alignment_map.md`
- `analysis/anthropic_skill_pass__simulation_report.md`
- `analysis/anthropic_skill_pass__source.pdf`
- `analysis/anthropic_skill_pass__source.txt`
- `analysis/anthropic_skill_pass__structured_notes.md`

Additionally, Git visibility is degraded by permission-denied temp directories:

- `.pytest_tmp/`
- `pytest_single_run/`
- `pytest_tmp_incident_20260418_2/`

Working classification:

- **remove or ignore**
- **not baselineable**

### 5. Deprecated or historical surfaces

These paths are capability-bearing historical surfaces. They are not runtime-authoritative and should not be mixed into the canonical Station baseline without explicit intent.

Examples:

- tracked deletion:
  - `openclaw/calyx-profile.json`
- untracked historical OpenClaw/config/plugin surfaces:
  - `openclaw/gateway.cmd`
  - `openclaw/extensions/calyx-governance/index.ts`
  - `openclaw/extensions/calyx-governance/openclaw.plugin.json`
  - `openclaw/openclaw.json`
  - `openclaw/openclaw.json.bak*`
  - `openclaw/cron/jobs*.json*`
  - `openclaw/completions/*`
  - `openclaw/canvas/*`
  - `skills/calyx-cbo-bridge/index.js`
  - `skills/calyx-cbo-bridge/manifest.json`
  - `skills/calyx-cbo-bridge/package.json`

Working classification:

- **historical surface**
- **requires explicit decision whether to preserve as source, archive externally, or remove from repo scope**

### 6. Files requiring explicit operator decision

These paths cannot be mutated safely without an operator decision because they affect authority, continuity, or historical capability boundaries.

#### `COMPENDIUM.md` move

Current state:

- untracked: `COMPENDIUM.md`
- tracked deletion: `docs/COMPENDIUM.md`

Required decision:

- finalize repo-root `COMPENDIUM.md` as canonical
- commit deletion of `docs/COMPENDIUM.md`

This should be treated as **keep + finalize**, not as local-only state.

#### Root continuity surfaces

- `HEALTH.md`
- `MEMORY.md`

These are untracked and not clearly classified as either canonical repo docs or local operator continuity surfaces.

Required decision:

- commit as canonical docs, or
- classify as local-only and ignore

#### Historical OpenClaw source-bearing surfaces

Examples:

- `openclaw/gateway.cmd`
- `openclaw/extensions/calyx-governance/*`
- `openclaw/calyx/openclaw/calyx-profile.json`
- `skills/calyx-cbo-bridge/*`

Required decision:

- retain as historical source
- archive outside baseline
- or remove from active repo scope

## Tracked Modifications vs Untracked Source Additions

### Tracked modifications

These are already in versioned scope and should be reviewed as candidate baseline content, not treated as junk.

High-signal tracked modified areas:

- governance/runtime core:
  - `Scripts/sunrise_calyx.ps1`
  - `Scripts/sunset_calyx.ps1`
  - `Scripts/update_state_checks.ps1`
  - `calyx/cbo/discord_gateway.py`
  - `calyx/cbo/intent_pipeline/plan.py`
  - `calyx/execution/hub_runner.py`
  - `calyx/kernel/contract.py`
  - `calyx/kernel/envelope.py`
  - `cbo_hub/cbo_core/app.py`
  - `cbo_hub/dev_harness/app.py`
  - `cbo_hub/telemetry_gateway/app.py`
- doctrine/docs:
  - `AGENTS.md`
  - `SOUL.md`
  - `USER.md`
  - `STATE.md`
  - `docs/public_repo_denylist.md`
  - `docs/OPENCLAW_CALYX_INTEGRATION.md`

Working classification:

- **retain**
- **review diff intentionally**

### Untracked source additions

These appear to be the bulk of the real implementation work that has not been normalized into version control yet.

High-signal areas:

- runtime topology / governance:
  - `calyx/governance/*`
  - `Scripts/runtime_truth_contract.ps1`
  - `Scripts/runtime_topology_snapshot.py`
  - `Scripts/restart_service.ps1`
- swarm substrate:
  - `calyx/kernel/swarm_*`
  - `docs/planning/WO_SWARM_*`
  - `tests/test_swarm_*`
- interruption governance:
  - `docs/operations/STATION_INTERRUPTION_AND_RECOVERY_MODEL.md`
  - `tests/test_station_interruption_governance.py`
- repo/audit docs:
  - `docs/operations/STATION_REPO_INTEGRITY_AUDIT_2026-04-21.md`

Working classification:

- **retain**
- **promote into tracked canonical source after review**

## Baseline Preparation Plan

### Keep

- canonical source in `Scripts/`, `calyx/`, `cbo_hub/`, `docs/`, `tests/`, `tools/`, `governance/`, `policy/`
- root `COMPENDIUM.md` as the active authority compendium
- tracked governance and doctrine modifications, after review

### Ignore

- `.openclaw/`
- `.worktrees/`
- `cbo_hub/data/`
- `tmp_lifecycle_case*/`
- analysis scratch outputs
- local continuity surfaces if not promoted:
  - `HEALTH.md`
  - `MEMORY.md`

### Remove from repo scope

- OpenClaw credential, identity, device, approval, and workspace-state files
- any remaining local workspace-state files under `cbo_hub/data/`
- temporary lifecycle case directories

### Explicit operator approval required before mutation

1. finalize the `COMPENDIUM.md` move
2. decide whether `HEALTH.md` and `MEMORY.md` are canonical or local-only
3. decide which historical OpenClaw source-bearing surfaces remain in active repo scope
4. decide whether `skills/calyx-cbo-bridge/*` remains as historical source or is removed from active baseline scope
5. decide whether analysis artifacts should be archived externally or deleted locally

## Recommended Mutation Sequence

1. finalize `COMPENDIUM.md` authority path
2. extend `.gitignore` for local-only and temp paths that are clearly non-canonical
3. remove local-only state from repo scope
4. remove temp/scratch artifacts from repo scope
5. re-run `git status`, denylist scan, and secret scan
6. review tracked modifications and untracked source additions as baseline candidate content
7. only then create the baseline commit

## Current Conclusion

The worktree is now explainable enough to prepare a baseline path, but it is not yet baseline-clean.

The next safe step is not `git commit`.

The next safe step is **operator-approved repo mutation for the clearly non-canonical buckets**, followed by a second audit pass on the reduced worktree.
