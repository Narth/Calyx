# Deployment & Integration Harness v0.1 — Receipt

**Date:** 2026-02-24  
**Objective:** Build Deployment & Integration Harness v0.1  
**Status:** Complete

## Deliverables

| # | Deliverable | Commit | Status |
|---|-------------|--------|--------|
| 1 | Parameterize REPO_ROOT in cbo_hub services | c6c24b95 | Done |
| 2 | Complete dependency declaration (httpx, python-dotenv, rich) | 4dd11854 | Done |
| 3 | Create .env.example | 224e1f4f | Done |
| 4 | Deployment smoke test (tools/smoke_test.py) | 1bf41f5b | Done |

## Summary

1. **REPO_ROOT:** `dev_harness/app.py` and `cbo_core/app.py` now use `Path(__file__).resolve().parents[2]` with `CALYX_REPO_ROOT` env override. `.env.cbo` loader path uses resolved root.

2. **requirements.txt:** Added `httpx>=0.27`, `python-dotenv>=1.0`, `rich>=13.0`. No existing entries removed or re-pinned.

3. **.env.example:** Documented API keys, model IDs, base URLs, cost-rate env vars from cbo_core/app.py and calyx/kernel/paths.py. Comments for required vs optional. Ref docs/USAGE_AND_HEALTH.md.

4. **tools/smoke_test.py:** Lane 0 boot-to-verified smoke test. Accepts `--cbo-api-url`, `--dev-harness-url`, `--cbo-core-url`. Tests: GET /heartbeat (CBO API), GET /docs (Dev Harness, CBO Core), POST /objective → /report (objectives_pending), POST /chat (receipt_sha256). Uses stdlib + httpx. Writes receipt to runtime/deployment/smoke_receipt.jsonl.

## Verification

- `pytest tests/ -q` — 66 passed
- No new network endpoints; no side effects beyond smoke receipt
- Deny-by-default governance preserved
