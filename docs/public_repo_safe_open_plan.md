# SAFE-TO-OPEN Public Repo Plan (Architecture-Only)

## Design decisions captured
1. Public repository is **architecture-only** (code, docs, schemas, examples).
2. Runtime telemetry/research/human artifacts must be stored externally and must not exist in git (including history).
3. Public users must never call Station Calyx directly; all public traffic must go through a Gateway path.

## A) Repo split / hygiene implementation plan

### 1) Identify tracked runtime artifacts (current snapshot)
- Generated inventory file: `docs/runtime_artifacts_inventory_2026-02-11.md`.
- Primary tracked runtime classes:
  - `telemetry/**`
  - `exports/**`
  - `station_calyx/data/**`
  - `*.jsonl` evidence/log streams
  - media captures (`*.wav`, screenshots)

### 2) Remove runtime artifacts from git tracking (working tree)
Run from repo root:

```bash
# remove tracked runtime dirs/files from index only (keep local copies)
git rm -r --cached telemetry exports station_calyx/data reports outgoing incoming responses logs || true

# remove tracked runtime extensions from index
git ls-files '*.jsonl' '*.wav' '*.mp3' '*.png' '*.jpg' '*.jpeg' \
  | xargs -r git rm --cached

# commit cleanup after verifying
# git commit -m "chore: untrack runtime artifacts for architecture-only public repo"
```

### 3) Purge sensitive/runtime artifacts from git history (required before open)
> Coordinate with maintainers first; this rewrites history and requires force-push + clone reset.

```bash
# install filter-repo if needed
# pip install git-filter-repo

# mirror clone recommended
# git clone --mirror <origin-url> calyx-mirror.git
# cd calyx-mirror.git

git filter-repo --force \
  --path telemetry --path exports --path station_calyx/data --path reports --path outgoing --path incoming --path responses --path logs \
  --path-glob '*.jsonl' --path-glob '*.wav' --path-glob '*.mp3' --path-glob '*.png' --path-glob '*.jpg' --path-glob '*.jpeg' \
  --invert-paths

# verify rewrite
git log --name-only --pretty=format: | rg 'telemetry/|exports/|station_calyx/data|\.jsonl|\.wav|\.mp3|\.png|\.jpg' || true

# force-push rewritten history
# git push --force --all
# git push --force --tags
```

### 4) Recommended architecture-only folder layout

```text
/code/         # runtime code only
/schemas/      # JSON schema / contracts
/examples/     # synthetic safe examples only
/docs/         # architecture + governance docs
/deploy/       # deploy manifests and gateway scaffolding
/runtime/      # local-only generated artifacts (ignored)
```

### 5) CI guardrail for forbidden tracked paths
- Added denylist script: `tools/check_forbidden_tracked_paths.sh`.
- Added CI workflow: `.github/workflows/public-repo-hygiene.yml`.
- CI fails if any forbidden runtime path/filetype is tracked.

## B) Service exposure hardening
- Keep Station and dashboard loopback/private by default.
- Block non-loopback binds unless explicit `CALYX_ALLOW_NON_LOOPBACK=true` override.
- Dashboard debug defaults to off.
- Dashboard auth placeholders fail-closed outside explicit `CALYX_DEV_MODE=true`.
- FastAPI exception response now generic with correlation ID.

## C) Gateway MVP (public edge)
- Added minimal gateway skeleton under `deploy/gateway/`.
- Public statement and contract in `docs/gateway.md`.
- Recommended controls:
  - HMAC request signature
  - request schema validation
  - per-client rate limiting
  - bounded forwarding contract to loopback Station endpoint

## D) Build breaker
- Fixed `dashboard/backend/api/chat.py` indentation issue and tightened one bare-except.
