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
| `sitecustomize.py`, `test_secret.py` | .gitignore |
| `Codex/Archives/*.zip`, `Codex/CGPT History/*.zip` | .gitignore |

---

## 4. Regex for hygiene / history scan

Single regex for matching paths (PowerShell `-match`):

```
^telemetry/|^exports/|^station_calyx/data/|^outgoing/|^incoming/|^responses/|^runtime/|^state/|^memory/|^staging/|^logs/|^keys/|\.(jsonl|wav|mp3|m4a|png|jpg|jpeg)$
```

---

## 5. Source documents

- **.gitignore** — Runtime state, secrets, logs, IDE, caches, models
- **GITHUB_PREP_CHECKLIST.md** — Runtime dirs, keys, config
- **reports/security/local_hygiene_inventory_2026-02-10.md** — Telemetry, exports, station_calyx/data, extensions
- **docs/public_repo_history_rewrite_runbook.md** — Combined list for git filter-repo

---

*Consolidated 2026-02-11. No code changes.*
