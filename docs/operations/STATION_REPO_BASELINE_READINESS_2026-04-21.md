---
status: active
owner: station
last_reviewed_utc: "2026-04-21"
doctrine_scope: governed
---

# STATION_REPO_BASELINE_READINESS_2026-04-21

## Purpose

This report records the controlled repo mutation pass performed after runtime reconciliation in order to reduce mixed provenance and improve baseline readiness.

This was not a commit pass. It was a cleanup and classification pass.

## Mutations Performed

### Kept

Canonical source-bearing surfaces were kept in repo scope, including:

- `Scripts/`
- `calyx/`
- `cbo_hub/avatar_web/`
- `cbo_hub/cbo_core/stamping.py`
- `cbo_hub/telemetry_gateway/`
- `docs/operations/`
- `docs/planning/`
- `tests/`
- `tools/`
- `governance/`
- `policy/`
- `COMPENDIUM.md` at repo root as the canonical authority file
- OpenClaw integration and bridge source-bearing surfaces, including:
  - `openclaw/extensions/calyx-governance/*`
  - `openclaw/gateway.cmd`
  - `skills/calyx-cbo-bridge/*`

### Ignored

`.gitignore` and `docs/public_repo_denylist.md` were extended to exclude clearly non-canonical buckets:

- `.openclaw/`
- `.worktrees/`
- `analysis/`
- `tmp_lifecycle_case*/`
- `cbo_hub/data/`
- `HEALTH.md`
- `MEMORY.md`
- `pytest_*/`
- `openclaw/credentials/`
- `openclaw/devices/`
- `openclaw/identity/`
- `openclaw/exec-approvals.json`
- `openclaw/workspace-state.json`
- `openclaw/agents/main/sessions/`
- `openclaw/media/inbound/`

### Removed from repo scope

The following clearly temp/scratch artifacts were physically removed:

- `analysis/`
- `tmp_lifecycle_case2/`
- `tmp_lifecycle_case2b/`
- `tmp_lifecycle_case3/`
- `tmp_lifecycle_case3b/`

### Retained local-only, but no longer in active repo scope

These remain on disk but are now ignored and treated as non-canonical active surfaces:

- `HEALTH.md`
- `MEMORY.md`
- `cbo_hub/data/*`
- OpenClaw local credential/device/identity/approval/workspace state

## Post-Mutation State

| measure | before | after |
|---|---:|---:|
| tracked modified files | `82` | `82` |
| tracked deletions | `2` | `2` |
| untracked paths | `259` | `245` |
| visible porcelain entries | `343` | `329` |

## Validation

### Denylist / ignore reduction

The following non-canonical buckets no longer appear in `git ls-files --others --exclude-standard`:

- `.openclaw/`
- `.worktrees/`
- `analysis/`
- `tmp_lifecycle_case*/`
- `cbo_hub/data/`
- `openclaw/credentials/`
- `openclaw/devices/`
- `openclaw/identity/`
- `openclaw/exec-approvals.json`
- `openclaw/workspace-state.json`
- `openclaw/agents/main/sessions/`
- `openclaw/media/inbound/`
- `HEALTH.md`
- `MEMORY.md`

### Secret-pattern scan

Tracked-file secret-pattern scan returned:

- `secret_scan_clean`

### `COMPENDIUM.md` move

Current state:

- root `COMPENDIUM.md` exists and is treated as canonical
- `docs/COMPENDIUM.md` remains a tracked deletion

Operationally, the move is resolved. Git normalization still requires the eventual baseline commit to add root `COMPENDIUM.md` and finalize deletion of `docs/COMPENDIUM.md`.

## Remaining Baseline Blockers

### 1. Canonical source is still uncommitted

The reduced worktree still contains a large amount of legitimate untracked Station source:

- `Scripts/` (`53`)
- `calyx/` (`36`)
- `cbo_hub/` (`8`)
- `docs/` (`85`)
- `tests/` (`36`)
- `openclaw/` (`24`)
- `skills/` (`16`)
- `tools/` (`13`)
- `governance/` (`3`)
- `policy/` (`8`)
- `COMPENDIUM.md` (`1`)

This is no longer mainly local-state noise. It is mostly real source awaiting deliberate versioning decisions.

### 2. Historical OpenClaw and bridge surfaces remain in scope by decision

These are intentionally preserved for dependency/integration posture, but they still require deliberate baseline representation:

- `openclaw/gateway.cmd`
- `openclaw/extensions/calyx-governance/*`
- `openclaw/openclaw.json*`
- `openclaw/cron/jobs*.json*`
- `openclaw/completions/*`
- `openclaw/canvas/*`
- `skills/calyx-cbo-bridge/*`

### 3. ACL-blocked pytest temp directories remain on disk

The following local temp directories still exist and still generate `git status` warnings:

- `.pytest_tmp`
- `pytest_single_run`
- `pytest_tmp_incident_20260418_2`

Removal was attempted, including an elevated attempt, but failed with access denied. These are no longer conceptual blockers, but they remain operational cleanup debt.

## Baseline Readiness Verdict

The repository is **not yet baseline-clean**.

However, it is now substantially more explainable:

- canonical source and local state are more sharply separated
- stale `HEALTH.md` and `MEMORY.md` are no longer treated as active baseline surfaces
- local OpenClaw runtime/operator state is excluded from active baseline scope
- temp lifecycle and scratch analysis artifacts are removed

## Readiness Assessment

| question | answer |
|---|---|
| is canonical source clearer than before? | yes |
| is local-only state excluded from active repo scope? | yes, for the classified buckets |
| is runtime/generated noise materially reduced? | yes |
| is the repo baseline-clean right now? | no |
| is the repo ready for commit planning? | yes, but only as a deliberate source-review and baseline-curation pass |

## Next Safe Step

The next safe step is **commit planning and source curation**, not blind cleanup.

That pass should:

1. review the remaining untracked source additions by subsystem
2. decide which preserved OpenClaw and bridge surfaces belong in the baseline representation
3. normalize the root `COMPENDIUM.md` into version control
4. resolve the remaining tracked modifications into an intentional baseline set
5. only then create the baseline commit
