# Security Scanning

This repository runs `gitleaks` in CI via `.github/workflows/public-repo-hygiene.yml` on:

- Pushes to `main`
- Pull requests targeting `main`

The workflow is configured to fail if any secret findings are detected.

## History Rewrite Notice (2026-02-12)

**⚠️ IMPORTANT:** This repository underwent a Git history rewrite on 2026-02-12 to remove exposed secrets (`openclaw.config.json` containing Discord bot token and OpenAI API key). All commit SHAs have changed.

**If you cloned before 2026-02-12, update your local repository:**

```powershell
# Option 1: Re-clone (recommended)
cd ..
mv Calyx Calyx_backup_$(Get-Date -Format 'yyyyMMdd')
git clone https://github.com/Narth/Calyx.git

# Option 2: Reset local branches
git fetch origin --prune
git checkout main
git reset --hard origin/main
```

**Affected branches:** `main`, `public-safety-clean`, `copilot/upload-governance-framework`, `codex/perform-public-readiness-audit-on-github-repo`

See `reports/security/secret_history_purge_force_push_completion_2026-02-12.md` for details.

## Local usage

### Option 1: Docker

```bash
docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest \
  detect --source /repo --config /repo/.gitleaks.toml --redact --verbose
```

### Option 2: Local binary

```bash
gitleaks detect --source . --config .gitleaks.toml --redact --verbose
```

Exit codes:

- `0`: no leaks found
- non-zero: leak(s) detected or scan error
