# Public Repo History Rewrite Runbook

**Purpose:** Step-by-step plan to purge runtime and sensitive artifacts from **entire git history** using `git filter-repo`, so the repo can be published or shared without historical exposure of telemetry, exports, station data, or media.

**Scope:** Planning and runbook only. **Do not execute** until Architect approval and backups are confirmed.

---

## 1. Forbidden Paths / Patterns (Denylist)

These match the **exact** patterns used in the local repo hygiene inventory (`reports/security/local_hygiene_inventory_*.md`) and the runtime exclusions in `.gitignore` / `GITHUB_PREP_CHECKLIST.md`.

### 1.1 Directory prefixes (strip from history)

| Pattern | Source |
|---------|--------|
| `telemetry/` | Hygiene inventory |
| `exports/` | Hygiene inventory |
| `station_calyx/data/` | Hygiene inventory |
| `outgoing/` | Hygiene inventory, .gitignore |
| `incoming/` | Hygiene inventory, .gitignore |
| `responses/` | Hygiene inventory, .gitignore |
| `runtime/` | Hygiene inventory |
| `state/` | .gitignore, GITHUB_PREP_CHECKLIST |
| `memory/` | .gitignore, GITHUB_PREP_CHECKLIST |
| `staging/` | .gitignore, GITHUB_PREP_CHECKLIST |
| `logs/` | .gitignore, GITHUB_PREP_CHECKLIST |
| `keys/` | .gitignore, GITHUB_PREP_CHECKLIST |

### 1.2 File extensions (strip from history)

| Pattern | Source |
|---------|--------|
| `*.jsonl` | Hygiene inventory |
| `*.wav` | Hygiene inventory, .gitignore (samples/wake_word/*.wav) |
| `*.mp3` | Hygiene inventory |
| `*.m4a` | Hygiene inventory |
| `*.png` | Hygiene inventory |
| `*.jpg` | Hygiene inventory |
| `*.jpeg` | Hygiene inventory |

**Canonical denylist script reference:** The same patterns are used by the hygiene inventory commands in `reports/security/local_hygiene_inventory_<date>.md`. Keep this runbook in sync with that report’s patterns.

---

## 2. Prerequisites

### 2.1 Install git-filter-repo

- **Windows (PowerShell):**
  ```powershell
  pip install git-filter-repo
  ```
  Or install from: https://github.com/newren/git-filter-repo

- **Verify:**
  ```powershell
  git filter-repo --version
  ```

### 2.2 Ensure repo is clean

```powershell
Set-Location c:\Calyx   # or your repo root
git status
```

- **Required:** No uncommitted changes. Commit or stash everything before any history rewrite.

### 2.3 Full backup (mandatory)

```powershell
# Clone a full backup (including all refs and history)
$BACKUP = "C:\Calyx_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
git clone --mirror "c:\Calyx" "$BACKUP"
# Optional: also copy working tree
Copy-Item -Recurse "c:\Calyx" "C:\Calyx_working_tree_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

- Confirm backup exists and is a full mirror before proceeding.

---

## 3. Pre-flight: Count and list affected paths

Run these **before** any rewrite to record how many paths will be removed.

### 3.1 Unique paths in history matching denylist

```powershell
Set-Location c:\Calyx
git log --name-only --pretty=format: | Sort-Object -Unique | Where-Object {
  $_ -and (
    $_ -match '^telemetry/|^exports/|^station_calyx/data/|^outgoing/|^incoming/|^responses/|^runtime/|^state/|^memory/|^staging/|^logs/|^keys/|\.(jsonl|wav|mp3|m4a|png|jpg|jpeg)$'
  )
} | Measure-Object -Line
```

- Record the count (e.g. in the runbook or a local note).

### 3.2 Export list of affected paths (optional)

```powershell
git log --name-only --pretty=format: | Sort-Object -Unique | Where-Object {
  $_ -and (
    $_ -match '^telemetry/|^exports/|^station_calyx/data/|^outgoing/|^incoming/|^responses/|^runtime/|^state/|^memory/|^staging/|^logs/|^keys/|\.(jsonl|wav|mp3|m4a|png|jpg|jpeg)$'
  )
} | Out-File -FilePath "reports\security\paths_to_purge_from_history.txt" -Encoding utf8
```

---

## 4. Build path list for git-filter-repo

`git filter-repo` can take multiple `--path <path> --invert-paths` to remove paths. For directory trees, a trailing slash denotes a directory (and everything under it). For globs, use `--path-glob`.

### 4.1 Option A: Inline path list (directory prefixes only)

Remove **only** the directory prefixes (no extension globs). Run from repo root:

```powershell
git filter-repo --path telemetry/ --path exports/ --path station_calyx/data/ --path outgoing/ --path incoming/ --path responses/ --path runtime/ --path state/ --path memory/ --path staging/ --path logs/ --path keys/ --invert-paths --force
```

- This removes every file whose path **starts with** each of these directories (e.g. `telemetry/energy/foo.json`).

### 4.2 Option B: Add extension globs (recommended for full denylist)

To also remove any file matching the extensions **anywhere** in the repo:

```powershell
git filter-repo `
  --path telemetry/ --path exports/ --path station_calyx/data/ --path outgoing/ --path incoming/ --path responses/ --path runtime/ --path state/ --path memory/ --path staging/ --path logs/ --path keys/ `
  --path-glob '*.jsonl' --path-glob '*.wav' --path-glob '*.mp3' --path-glob '*.m4a' --path-glob '*.png' --path-glob '*.jpg' --path-glob '*.jpeg' `
  --invert-paths --force
```

- **Caution:** `--path-glob '*.jsonl'` removes **every** `.jsonl` file in history (e.g. under `benchmarks/`, `calyx/`, `docs/`, `tests/`), not only under the listed directories. If you want to purge only runtime directories and leave other `.jsonl` (e.g. benchmarks) in history, **omit** the `--path-glob` lines and use Option A.

### 4.3 Option C: Paths-from-file (for audit trail)

Create a file listing one path/glob per line, then:

```powershell
# Create denylist file (one path per line; no trailing slash for files)
@"
telemetry/
exports/
station_calyx/data/
outgoing/
incoming/
responses/
runtime/
state/
memory/
staging/
logs/
keys/
"@ | Out-File -FilePath "docs\filter_repo_denylist.txt" -Encoding utf8 -NoNewline
# Then run (syntax depends on git-filter-repo version; see docs for --paths-from-file or equivalent)
```

- Check `git filter-repo` documentation for your version for exact `--paths-from-file` or `--path-list-file` syntax; not all versions support reading paths from a file.

---

## 5. Safety checks before running filter-repo

1. **Backup confirmed:** Full mirror clone exists and is accessible.
2. **Clean working tree:** `git status` is clean.
3. **No active remotes required:** `git filter-repo` will remove remote-tracking refs by default; re-add `origin` after the rewrite if needed.
4. **Approval:** Architect or delegated authority has approved the history rewrite.
5. **Denylist locked:** No ad-hoc path added; only the patterns in §1 are used.

---

## 6. Execute rewrite (after approval)

**Single command (Option A — directories only):**

```powershell
Set-Location c:\Calyx
git filter-repo --path telemetry/ --path exports/ --path station_calyx/data/ --path outgoing/ --path incoming/ --path responses/ --path runtime/ --path state/ --path memory/ --path staging/ --path logs/ --path keys/ --invert-paths --force
```

- `--force` is required because filter-repo refuses to run on a repo that has remotes, unless forced. Remotes are removed; re-add after verification.

---

## 7. Post-rewrite verification

### 7.1 Re-add remote (if you use origin)

```powershell
git remote add origin <YOUR_ORIGIN_URL>
```

### 7.2 Confirm purged paths are gone from history

```powershell
git log --name-only --pretty=format: | Sort-Object -Unique | Where-Object {
  $_ -and (
    $_ -match '^telemetry/|^exports/|^station_calyx/data/|^outgoing/|^incoming/|^responses/|^runtime/|^state/|^memory/|^staging/|^logs/|^keys/|\.(jsonl|wav|mp3|m4a|png|jpg|jpeg)$'
  )
}
```

- **Expected:** No output (or only paths you intentionally kept).

### 7.3 Spot-check commits and tree

```powershell
git log --oneline -20
git ls-files | Select-Object -First 50
```

- Confirm recent commits and current index look correct.

### 7.4 Compare object count (optional)

```powershell
git count-objects -v
```

- Compare with pre-rewrite run; object count should drop after purge.

---

## 8. Push rewritten history (destructive)

**Warning:** This rewrites the remote. All clones must re-clone or rebase.

```powershell
git push origin --force --all
git push origin --force --tags
```

- Notify anyone with clones to re-clone or follow a documented recovery flow.

---

## 9. Exact commands summary (copy-paste reference)

| Step | Command |
|------|--------|
| Backup | `git clone --mirror "c:\Calyx" "C:\Calyx_backup_<date>"` |
| Pre-flight count | `git log --name-only --pretty=format: \| Sort-Object -Unique \| Where-Object { $_ -and ($_ -match '^telemetry/\|^exports/\|^station_calyx/data/\|^outgoing/\|^incoming/\|^responses/\|^runtime/\|^state/\|^memory/\|^staging/\|^logs/\|^keys/\|\.(jsonl\|wav\|mp3\|m4a\|png\|jpg\|jpeg)$') } \| Measure-Object -Line` |
| Rewrite (dirs only) | `git filter-repo --path telemetry/ --path exports/ --path station_calyx/data/ --path outgoing/ --path incoming/ --path responses/ --path runtime/ --path state/ --path memory/ --path staging/ --path logs/ --path keys/ --invert-paths --force` |
| Verify no matches | `git log --name-only --pretty=format: \| Sort-Object -Unique \| Where-Object { $_ -and ($_ -match '^telemetry/\|^exports/\|...') }` (expect empty) |
| Re-add remote | `git remote add origin <URL>` |
| Force push | `git push origin --force --all` ; `git push origin --force --tags` |

---

## 10. Rollback

If something goes wrong:

1. **Do not** push the rewritten repo.
2. Remove the rewritten clone: `Remove-Item -Recurse -Force c:\Calyx` (or the path you ran filter-repo in).
3. Restore from backup: `git clone "C:\Calyx_backup_<date>" c:\Calyx` (or restore from mirror clone per git documentation).
4. Re-add remotes and continue from the pre-rewrite state.

---

*Runbook only. No execution performed. Align denylist with `reports/security/local_hygiene_inventory_*.md` and `.gitignore`.*
