# Tool loop – runtime verification

## Summary

Read-only structured tool-call loop in CBO Core:

- **When:** `model_role == "architect"`, `allow_tools == True`, model returns valid JSON with `"tool_requests"`.
- **Then:** Parse JSON safely; allow only `repo_list`, `repo_search`; execute up to 3 tool calls; append results to reply; record `executed_tools` in receipt.
- **Not used:** docker, file writes, new endpoints, recursion; CLI protocol unchanged.

## Verification steps

1. **Start Dev Harness (port 7777)**  
   From repo root:
   ```bash
   uvicorn cbo_hub.dev_harness.app:app --host 127.0.0.1 --port 7777
   ```

2. **Start CBO Core (port 7778)**  
   In another terminal:
   ```bash
   uvicorn cbo_hub.cbo_core.app:app --host 127.0.0.1 --port 7778
   ```

3. **Confirm no 500s**
   - `POST http://127.0.0.1:7778/chat` with body:
     ```json
     {"user_text": "List root directory", "session_id": "home", "mode": "dev", "allow_tools": true, "model_role": "architect"}
     ```
   - Expect `200` and `reply_text` containing `[CBO online]` and optionally `[tool] repo_list(...)` / `[tool] repo_search(...)` if the model returned `tool_requests`.

4. **Confirm receipts**
   - Check `cbo_hub/receipts/cbo_core.jsonl`: each line is a receipt; each receipt has `executed_tools` (array of tool names) and `tool_calls` (with `result_sha256`).

5. **Optional: CLI**
   - Run `python -m cbo_hub.cli_avatar.main`, then `/architect`, then e.g. "List root and search for AGENTS" to trigger tool_requests path (if the model responds with JSON).

## Success criteria

- No 500 errors on `/chat` for the above cases.
- Receipts written to `cbo_hub/receipts/cbo_core.jsonl` with `executed_tools` and `tool_calls` populated when tools run.
- Only `repo_list` and `repo_search` are executed from the loop; no docker, no file modification.

---

# Phase 6: Kimi (second_opinion) — acceptance tests

Config: `KIMI_BASE_URL` (default `https://api.moonshot.ai/v1`), `KIMI_MODEL_ID` (required), `KIMI_API_KEY` or `MOONSHOT_API_KEY`.

## Test 1: second_opinion disabled (no silent spend)

- **Request:** `POST /chat` with `model_role="second_opinion"`, `allow_second_opinion=false` (or omit; default false).
- **Expect:** HTTP 200.
- **Response:** `reply_text` includes a readable message like "second_opinion disabled" or "Set allow_second_opinion=true to enable"; `second_opinion_text` may contain the same.
- **Receipt:** `second_opinion_receipt` present with `provider: "kimi"`, `called: false` (or equivalent). Provider not actually called.

## Test 2: second_opinion enabled, valid config

- **Request:** `POST /chat` with `model_role="second_opinion"`, `allow_second_opinion=true`, valid `KIMI_API_KEY`, `KIMI_BASE_URL`, `KIMI_MODEL_ID` in env.
- **Expect:** HTTP 200.
- **Receipt:** `second_opinion_receipt` has `provider: "kimi"`, `base_url`, `model_id`, `http_status: 200`.
- **Response:** `second_opinion_text` present (Kimi reply or error string).

## Test 3: second_opinion enabled, missing KIMI_MODEL_ID

- **Request:** `POST /chat` with `allow_second_opinion=true`, `model_role="second_opinion"`; env has key/url but **no** `KIMI_MODEL_ID`.
- **Expect:** HTTP 200 (no 500).
- **Response:** Readable error instructing to set `KIMI_MODEL_ID`.
- **Receipt:** `second_opinion_receipt` has `error_snippet` indicating model id not set and/or `called: false` or call completed with error.

## Test 4: Tool loop for second_opinion

- **Request:** `POST /chat` with `model_role="second_opinion"`, `allow_second_opinion=true`, `allow_tools=true`; user prompt such that Kimi returns valid `tool_requests` JSON with e.g. `repo_search` for "STATE.md".
- **Expect:** HTTP 200; `executed_tools` includes `"repo_search"`; tool results appended in `reply_text`; receipt has `tool_calls` and `executed_tools`; `second_opinion_text` contains Kimi output.
