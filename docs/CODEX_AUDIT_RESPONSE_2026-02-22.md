# Codex Public-Facing Secrecy & Privacy Audit — CBO Response (2026-02-22)

**Audit date:** 2026-02-22
**Auditor:** Codex (two passes)
**Respondent:** CBO (Station Calyx)
**Tag:** `preaudit` (2026-02-21) marks repo state at time of audit request.

---

## Consolidated findings (from both Codex outputs)

| # | Type | Paths / scope | Risk |
|---|------|----------------|------|
| 1 | PII (email in patches) | `patches_out/*.patch` (author/co-author metadata) | Exposes maintainer/co-author emails in public history |
| 2 | PII / operator profile | `USER.md`, `SOUL.md` | Human name, aliases, timezone, role, operational context |
| 3 | PII / operator identifier | `docs/DISCORD_SETUP.md`, `docs/OPENCLAW_CALYX_INTEGRATION.md` | Discord user IDs (authorized user, approver/allowFrom) |
| 4 | Sensitive operational metadata | Same docs | Channel ID, server/channel restriction, config paths |
| 5 | Denylist mismatch — extension | `*.jsonl` | Denylist says forbidden; tracked: `calyx/core/registry.jsonl`, `docs/ADVISORY_PROVENANCE_LOG.jsonl`, `docs/HASH_CHAIN_LEDGER.jsonl`, `docs/TEMPLATE_ARCHIVE_LEDGER_ENTRY.jsonl`, `benchmarks/suites/**/cases.jsonl` (last explicitly allowed in .gitignore) |
| 6 | Denylist mismatch — directory | `reports/` | Denylist says forbidden; `reports/security/*.md` currently tracked (audit/runbook trail) |
| 7 | Secret-handling path (no value in repo) | `Scripts/setup_openclaw_calyx.ps1`, `Scripts/start_station_calyx.ps1`, `docs/OPENCLAW_CALYX_INTEGRATION.md` | Token read from env and written to `~/.openclaw/openclaw.json` outside repo |
| 8 | Token-adjacent doc pattern | `docs/workflows/network_evidence_push_v0.md` | Bearer token handling example (redacted); high-risk for accidental paste |

**No direct secret-value exposure** was reported; gitleaks in CI remains the primary automated check.

---

## CBO actions taken (2026-02-22)

- **Audit record:** This file and reference from `docs/security.md`.
- **Denylist reconciliation:** `docs/public_repo_denylist.md` updated with an **Intentional exceptions** section so policy matches repo state (reports/, *.jsonl).

---

## Remediations completed (2026-02-22)

- **Patches:** `patches_out/*.patch` added to `.gitignore`. Future `.patch` files will not be tracked; existing tracked patches remain in history.
- **Private path:** `private/` added to `.gitignore`. Real identity and Discord IDs live in `private/` only.
- **Identity docs:** Real copies moved to `private/USER.md`, `private/SOUL.md`, `private/IDENTITY.md`. Root `USER.md`, `SOUL.md`, `IDENTITY.md` replaced with placeholder examples (no PII).
- **Discord credentials:** Raw user/channel IDs removed from `docs/DISCORD_SETUP.md` and `docs/OPENCLAW_CALYX_INTEGRATION.md`; replaced with placeholders (`<STATION_HEALTH_CHANNEL_ID>`, `<AUTHORIZED_DISCORD_USER_ID>`, `<YOUR_DISCORD_USER_ID>`). Real IDs documented in `private/DISCORD_IDS.md` (gitignored).
- **Token examples:** `docs/workflows/network_evidence_push_v0.md` updated to env-var-only: no literal token placeholders; all examples use `CALYX_INGEST_TOKEN` from environment. Quick reference and troubleshooting updated accordingly.

---

## Optional (not yet done)

- **CI:** Pre-commit or CI check: warn on Discord ID patterns and on email addresses in `docs/` and `patches_out/`; block obvious live-token formats in docs.

---

*CBO consolidation of Codex audit outputs; no live secrets reproduced.*
