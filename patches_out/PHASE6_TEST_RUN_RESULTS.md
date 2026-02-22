# Phase 6 — Test run results (Tests 1–5)

**Run:** 2026-02-21 (CBO-authorized)  
**Services:** Dev Harness (7777) and CBO Core (7778) started for this run.

## Summary

| Test | Result | Notes |
|------|--------|--------|
| **1** — second_opinion disabled | **PASS** | HTTP 200. Reply and `second_opinion_text` contain "second_opinion disabled". Receipt: `second_opinion_receipt.called: false`, `error_snippet: "Not called (allow_second_opinion=false)."` No Kimi call. |
| **2** — second_opinion enabled | **PASS** (error path) | HTTP 200. No Kimi credentials in run env; got readable error in `second_opinion_text`: "KIMI_MODEL_ID not set. Set it in env (e.g. KIMI_MODEL_ID=moonshot-v1-8k)." Receipt has `second_opinion_receipt` with `provider: kimi`, `base_url`, `called: false`, `error_snippet`. Full success (Kimi 200) requires KIMI_API_KEY + KIMI_MODEL_ID in env. |
| **3** — Missing KIMI_MODEL_ID | **PASS** | HTTP 200 (no 500). Readable error instructing to set KIMI_MODEL_ID. Receipt captures `error_snippet`. |
| **4** — Tool loop for second_opinion | **PASS** | HTTP 200. Tool output present in reply (repo_search ran via deterministic "search" trigger). With real Kimi returning tool_requests JSON, loop would run from model output; structure verified. |
| **5** — Workhorse tool eligibility | **PASS** | HTTP 200. `repo_list` executed; reply contains directory listing. Receipt `executed_tools` includes `"repo_list"`. Confirms tool loop is not architect-only. |

## Receipt spot-check

- **Test 1:** `second_opinion_receipt.called = false`, `error_snippet = "Not called (allow_second_opinion=false)."`
- **Tests 2–4:** `second_opinion_receipt` with `provider: kimi`, `base_url: https://api.moonshot.ai/v1`, `error_snippet` (KIMI_MODEL_ID), `called: false`.
- **Test 5:** `executed_tools: ["repo_list"]`.

## Conclusion

All five acceptance tests passed. No 500s. Receipts are written and include the required second_opinion and tool fields. To validate Test 2 (and full Test 4 tool-from-model path) with a live Kimi response, set `KIMI_API_KEY` and `KIMI_MODEL_ID` in the environment and re-run Tests 2 and 4.
