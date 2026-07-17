# Phase 6: Kimi second_opinion — summary

## Files changed

| File | Why |
|------|-----|
| `cbo_hub/cbo_core/app.py` | Only file modified. Kimi wiring, allow_second_opinion gate, tool loop expansion, STATE.md injection, receipt fields, ChatReq/ChatResp updates. |
| `patches_out/TOOL_LOOP_VERIFICATION.md` | Appended Phase 6 acceptance tests (Tests 1–4). |
| `patches_out/cbo_core_kimi_second_opinion.patch` | Unified diff of Phase 6 changes (reference). |
| `patches_out/PHASE6_SUMMARY.md` | This summary. |

No other files changed. CLI Avatar not modified (no protocol change).

## Confirmation

- **No docker exec:** No code paths call docker or `/exec/docker`.
- **No file writes beyond receipts:** Only `_write_receipt()` and `STATE.md` read (read-only). No other file writes.
- **No new endpoints:** All behavior is via existing `POST /chat`. No new routes added.

## Config (env)

- `KIMI_API_KEY` or `MOONSHOT_API_KEY` — required for Kimi calls.
- `KIMI_BASE_URL` — optional; default `https://api.moonshot.ai/v1`.
- `KIMI_MODEL_ID` — required; no silent fallback; clear error if missing.

## Request/response

- **ChatReq:** Added `allow_second_opinion: bool = False`. `model_role` accepts `second` (alias) and `second_opinion`.
- **ChatResp:** Added `second_opinion_text: Optional[str] = None`.
- **Receipt:** When `model_role == "second_opinion"`, receipt includes `second_opinion_receipt` with `provider`, `base_url`, `model_id`, `http_status`, `error_snippet` (≤500 chars), `request_id`, `called`.
