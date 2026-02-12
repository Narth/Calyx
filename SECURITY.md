# Security Model

**Station Calyx** is a local-first governance and coordination stack for AI agents.

---

## Governance Invariants

This repository maintains strict governance invariants (verified for Calyx Mail v0.1):

### No Network Imports

- âœ… No `socket`, `requests`, `urllib`, `http`, `asyncio`, `aiohttp`, `websocket` imports
- âœ… All operations are local filesystem-based
- âœ… Benchmark harness operates offline (no network dependencies)

### No Dynamic Execution

- âœ… No `eval()`, `exec()`, `subprocess`, `__import__()`, `compile()` for untrusted content
- âœ… SQLite `execute()` only for database queries (trusted)
- âœ… Regex `re.match()` only for validation (trusted patterns)

### No Secrets in Tracked Files

- âœ… No API keys, tokens, or passwords in tracked files
- âœ… All secrets stored under `runtime/keys/` (git-ignored)
- âœ… Template files use placeholders (`__SET_ME__`)

### No Runtime Artifacts Tracked

- âœ… Runtime state (telemetry, exports, logs) git-ignored
- âœ… CI enforces: `tools/check_forbidden_tracked_paths.sh`
- âœ… Architecture-only repository

### Mail Content Non-Executable

- âœ… Calyx Mail content remains read-only
- âœ… No execution pathways from mail content
- âœ… No command/action payload types

### No Control-Plane Semantics

- âœ… No command/action payload types in v0.1
- âœ… No agent execution from mail content
- âœ… Deny-by-default governance

---

## Repo Hygiene

**CI Enforcement:**
- `.github/workflows/public-repo-hygiene.yml` runs on every push
- Checks for forbidden paths (telemetry/, exports/, runtime/, etc.)
- Checks for forbidden file types (evidence.jsonl, .wav, .mp3, .png, etc.)
- Runs `py_compile` sanity checks

**Manual Verification:**
```powershell
# Check for forbidden paths
git ls-files | grep -E "(telemetry/|exports/|runtime/)"

# Check for network imports
grep -r "import (socket|requests|urllib)" calyx/

# Check for dynamic execution
grep -r "(eval|exec|subprocess)" calyx/
```

---

## Security Reports

Public-ready verification receipts:
- `reports/security/public_release_readiness_verification_2026-02-11.md`
- `reports/security/calyx_mail_v0_1_final_release_summary_2026-02-12.md`

---

## Reporting Security Issues

See `README.md` for security contact information.