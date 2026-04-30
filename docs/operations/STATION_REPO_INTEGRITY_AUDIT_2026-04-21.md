---
status: active
owner: station
last_reviewed_utc: "2026-04-21"
doctrine_scope: governed
---

# STATION_REPO_INTEGRITY_AUDIT_2026-04-21

## Purpose

This audit measures whether the repository reflects the actual governed Station state closely enough to support reconciliation, version control, and baseline backup.

This pass is read-only. No cleanup, staging, commit, or process termination was performed.

## Executive State

The repository is not at a clean baseline.

It currently contains three materially different categories of drift:

1. intended but uncommitted Station changes
2. local-only operator or runtime-adjacent state that should not be versioned
3. temporary test or investigation artifacts that should not survive into a baseline commit

Because those categories are mixed together in one worktree, Phase D baseline consolidation is not yet safe.

## Git State Summary

| measure | value | evidence type |
|---|---:|---|
| branch | `wo-sunrise-canonical-bootpath-v1` | direct |
| tracked modified files | `82` | direct |
| tracked deletions | `2` | direct |
| untracked files/directories | `259` | direct |
| total visible porcelain entries | `343` | direct |
| tracked files under `runtime/` | `0` | direct |
| tracked files under `memory/` | `0` | direct |

## High-Risk Repo Integrity Findings

### 1. Large untracked governance and code surface

The worktree contains a substantial amount of untracked Station code and governance material under:

- `Scripts/`
- `calyx/`
- `cbo_hub/`
- `docs/operations/`
- `docs/planning/`
- `tests/`

This is not runtime noise. It appears to be real implementation and planning work that has not yet been normalized into version control.

### 2. Local-only state is mixed into the same untracked set

The following untracked paths are local or environment-specific and should not be part of a canonical baseline commit:

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

These files increase ambiguity because they live under repo paths but represent local state rather than source-of-truth code.

### 3. Temporary artifacts are currently baseline blockers

Untracked temp and investigation artifacts are present:

- `tmp_lifecycle_case2/`
- `tmp_lifecycle_case2b/`
- `tmp_lifecycle_case3/`
- `tmp_lifecycle_case3b/`
- `.worktrees/audit/`
- `.openclaw/workspace-state.json`
- `analysis/anthropic_skill_pass__*`

They are not necessarily dangerous, but they are baseline blockers until explicitly classified, ignored, or removed.

### 4. Legacy path transition is not committed cleanly

There is still a tracked deletion for `docs/COMPENDIUM.md` and an untracked `COMPENDIUM.md` at repo root.

That is operationally consistent with the authority move to repo root, but it is not yet a clean versioned transition.

### 5. Git visibility is partially degraded by permission-denied directories

`git status` and related commands report:

- `.pytest_tmp/`: permission denied
- `pytest_single_run/`: permission denied
- `pytest_tmp_incident_20260418_2/`: permission denied

That means the current worktree cannot be considered fully inspectable from Git alone. Baseline consolidation should not proceed until those directories are either classified or removed from the audit path.

## Hygiene and Policy Findings

### Already acceptable

- `.gitignore` excludes `runtime/`, `memory/`, logs, venvs, and other generated surfaces.
- No tracked files currently exist under `runtime/`.
- No tracked files currently exist under `memory/`.
- `docs/public_repo_denylist.md` already encodes the intended public-boundary policy for runtime and secret-bearing material.

### Ambiguous or incomplete

- `.gitignore` does not currently cover:
  - `tmp_lifecycle_case*/`
  - `.worktrees/`
  - `.openclaw/`
  - `cbo_hub/data/`
- The repo contains many legitimate untracked source files mixed with local-only state, so a blanket `git add .` would be governance failure.

### Must be reclassified before baseline

- `openclaw/` local identity, device, credential, workspace, and approval artifacts
- `cbo_hub/data/` workspace board state
- temp lifecycle directories
- analysis scratch artifacts

## Untracked Category Counts

| pattern | count | interpretation |
|---|---:|---|
| `^openclaw/` | `35` | historical/external capability surface mixed with local state |
| `^\\.openclaw/` | `1` | local workspace state |
| `^tmp_` | `4` | temporary lifecycle investigation artifacts |
| `^\\.worktrees/` | `1` | local git workspace artifact |
| `^cbo_hub/data/` | `5` | application state, not source |
| `^analysis/` | `5` | working analysis artifacts |
| `^policy/` | `8` | likely legitimate source, currently untracked |

## Baseline Commit Plan

Phase D should proceed only after the following controlled sequence:

1. classify all untracked paths into:
   - commit as source
   - ignore as local/generated
   - remove as temporary
2. normalize the COMPENDIUM authority move:
   - commit root `COMPENDIUM.md`
   - finalize deletion of `docs/COMPENDIUM.md`
   - verify no stale active references remain
3. isolate local OpenClaw and workspace-state files from source-bearing paths
4. remove or ignore temp lifecycle and scratch analysis artifacts
5. resolve tracked modifications intentionally, not mechanically
6. re-run:
   - `git status --short --branch`
   - secret-pattern scan
   - denylist compliance scan
   - runtime artifact tracking scan
7. create one clean baseline commit only after the worktree is fully classified
8. tag the resulting commit, for example:
   - `calyx-baseline-20260421`

## Current Conclusion

The repository is not yet suitable for baseline commit or GitHub consolidation.

The blocker is not just volume. The blocker is mixed provenance:

- governed code
- local identity and workspace state
- temp investigation artifacts

Those must be separated before any canonical baseline can be trusted.

## Evidence

- `git status --short --branch`
- `git diff --name-only`
- `git ls-files --others --exclude-standard`
- `.gitignore`
- `docs/public_repo_denylist.md`
