# Public Repo Denylist — Consolidated

**Purpose:** Single canonical reference for paths and patterns that must not appear in public repo history or index.  
**Sources:** `.gitignore`, `GITHUB_PREP_CHECKLIST.md`, `reports/security/local_hygiene_inventory_*.md`, `docs/public_repo_history_rewrite_runbook.md`  
**Date:** 2026-02-11 (ground-truth check)

---

## 1. Directory prefixes (forbidden)

| Pattern | Sources |
|---------|---------|
| `telemetry/` | Hygiene inventory, history runbook |
| `exports/` | Hygiene inventory, history runbook |
| `station_calyx/data/` | Hygiene inventory, history runbook |
| `outgoing/` | .gitignore, GITHUB_PREP_CHECKLIST, hygiene inventory, history runbook |
| `incoming/` | .gitignore, GITHUB_PREP_CHECKLIST, hygiene inventory, history runbook |
| `responses/` | .gitignore, hygiene inventory, history runbook |
| `runtime/` | Hygiene inventory, history runbook |
| `state/` | .gitignore, GITHUB_PREP_CHECKLIST, history runbook |
| `memory/` | .gitignore, GITHUB_PREP_CHECKLIST, history runbook |
| `staging/` | .gitignore, GITHUB_PREP_CHECKLIST, history runbook |
| `logs/` | .gitignore, GITHUB_PREP_CHECKLIST, history runbook |
| `keys/` | .gitignore, GITHUB_PREP_CHECKLIST, history runbook |
| `.venv/`, `venvs/`, `env/`, `venv/` | .gitignore, GITHUB_PREP_CHECKLIST |
| `.vscode/`, `.cursor/`, `.idea/` | .gitignore |
| `.codex_cache/`, `.claude_cache/`, `.firecrawl_cache/` | .gitignore |
| `local_backups/` | .gitignore |
| `models/` | .gitignore |
| `reports/` | .gitignore (current; may be reviewed for public) |

---

## 2. File extensions (forbidden)

| Pattern | Sources |
|---------|---------|
| `*.jsonl` | Hygiene inventory, history runbook |
| `*.wav` | Hygiene inventory, .gitignore (samples/wake_word/*.wav), history runbook |
| `*.mp3` | Hygiene inventory, history runbook |
| `*.m4a` | Hygiene inventory, history runbook |
| `*.png` | Hygiene inventory, history runbook |
| `*.jpg` | Hygiene inventory, history runbook |
| `*.jpeg` | Hygiene inventory, history runbook |
| `*.key`, `*.pem`, `*.pk.b64`, `*.sk.b64` | .gitignore |
| `*.bin`, `*.pt`, `*.onnx`, `*.safetensors` | .gitignore |
| `*.log`, `*.csv` (specific) | .gitignore |

---

## 3. Specific files (forbidden)

| Path | Sources |
|------|---------|
| `config.yaml` | .gitignore (use config.template.yaml) |
| `.env`, `.env.*` | .gitignore |
| `DISCORD_IDS.md` | .gitignore |
| `sitecustomize.py`, `test_secret.py` | .gitignore |
| `Codex/Archives/*.zip`, `Codex/CGPT History/*.zip` | .gitignore |
| `HEALTH.md`, `MEMORY.md` | Repo baseline classification 2026-04-21 |
| `.openclaw/`, `.worktrees/` | Repo baseline classification 2026-04-21 |
| `cbo_hub/data/` | Repo baseline classification 2026-04-21 |
| `tmp_lifecycle_case*/` | Repo baseline classification 2026-04-21 |
| `analysis/` | Repo baseline classification 2026-04-21 |
| `openclaw/credentials/`, `openclaw/devices/`, `openclaw/identity/` | Repo baseline classification 2026-04-21 |
| `openclaw/exec-approvals.json`, `openclaw/workspace-state.json` | Repo baseline classification 2026-04-21 |
| `openclaw/agents/main/sessions/`, `openclaw/media/inbound/` | Repo baseline classification 2026-04-21 |

---

## 4. Regex for hygiene / history scan

Single regex for matching paths (PowerShell `-match`):

```
^telemetry/|^exports/|^station_calyx/data/|^outgoing/|^incoming/|^responses/|^runtime/|^state/|^memory/|^staging/|^logs/|^keys/|\.(jsonl|wav|mp3|m4a|png|jpg|jpeg)$
```

---

## 5. Intentional exceptions (reconciled 2026-02-22)

After Codex public-facing audit, the following are **documented exceptions** so denylist policy matches repo state.

| Area | Current repo state | Policy |
|------|--------------------|--------|
| **reports/** | `reports/security/*.md` are **tracked** (audit/runbook trail) | All other `reports/` content remains forbidden/ignored. No new non-security reports without explicit decision. |
| **\*.jsonl** | **Tracked:** `benchmarks/suites/**/cases.jsonl` (allowed in .gitignore); `calyx/core/registry.jsonl`, `docs/ADVISORY_PROVENANCE_LOG.jsonl`, `docs/HASH_CHAIN_LEDGER.jsonl`, `docs/TEMPLATE_ARCHIVE_LEDGER_ENTRY.jsonl` (legacy) | .gitignore allowlist: `!tests/fixtures/*.jsonl`, `!docs/examples/**/*.jsonl`, `!benchmarks/suites/**/cases.jsonl`. Legacy tracked jsonl in `calyx/core/` and `docs/` to be reviewed before public push (migrate or add explicit allowlist). |

See `docs/CODEX_AUDIT_RESPONSE_2026-02-22.md` for full audit and optional remediations.

---

## 6. Source documents

- **.gitignore** — Runtime state, secrets, logs, IDE, caches, models
- **GITHUB_PREP_CHECKLIST.md** — Runtime dirs, keys, config
- **reports/security/local_hygiene_inventory_2026-02-10.md** — Telemetry, exports, station_calyx/data, extensions
- **docs/public_repo_history_rewrite_runbook.md** — Combined list for git filter-repo

---

*Consolidated 2026-02-11. Exceptions reconciled 2026-02-22 (Codex audit).*
