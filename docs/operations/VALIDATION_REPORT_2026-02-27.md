---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Three-Channel Smoke Test — Validation Report

**Date:** 2026-02-27
**Context:** Post WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1; new Discord token applied. Three entry points tested with identical prompts.

---

## Test Matrix

| Entry Point | Session ID | Test 1: event_ledger emit | Test 2: Station heartbeat |
|-------------|------------|---------------------------|---------------------------|
| **CBO Browser (Avatar Web 7780)** | home | FAIL — hallucinated `Station/src/event_handler.c` | FAIL — searched repo instead of producing |
| **Discord DM** | discord_1465434173224259615 | FAIL — hallucinated `/path/to/station_repo/src/event_ledger/emitter.py` | PASS — returned `{"heartbeat_ts": "2026-02-26T14:14:47Z"}` |
| **Authorized public channel** | discord_1465903939659632807 | FAIL — hallucinated `src/modules/event_log/ledger.cpp` | FAIL — searched repo instead of producing |

**Ground truth:**
- **event_ledger emit:** `calyx/kernel/event_ledger.py` (line 78)
- **Heartbeat:** STATE.md `heartbeat_ts`, `health`, `checks` — already injected in context

---

## Failure Analysis

### Test 1: event_ledger Smoke Test

**Expected:** `repo_search` with query `event_ledger` (or `event_ledger emit`), result `calyx/kernel/event_ledger.py`, one-sentence synthesis.

**Observed:**
- Browser: First run used `query='Calyx'` (wrong); second run `query='event_ledger emit'` → synthesis cited `Station/src/event_handler.c` (hallucination)
- Discord DM: `query='event_ledger emit'` → synthesis cited `/path/to/station_repo/src/event_ledger/emitter.py` (hallucination)
- Public channel: `query='event_ledger emit function'` → synthesis cited `src/modules/event_log/ledger.cpp` (hallucination)

**Root cause:** Synthesis pass (qwen2.5-coder:7b) continues to invent file paths instead of citing tool results. FE-9 pattern persists. All three sessions produced different wrong answers — non-determinism + lack of grounding.

### Test 2: Station Heartbeat

**Expected:** Return heartbeat JSON from STATE (heartbeat_ts, health, checks). STATE is injected; no tools required.

**Observed:**
- Browser: `repo_list` + `repo_search(query='heartbeat')` → found HEARTBEAT.md; no heartbeat JSON produced
- Discord DM: `repo_list` (local availability) → correctly synthesized `{"heartbeat_ts": "2026-02-26T14:14:47Z"}` from STATE
- Public channel: `repo_list` + `repo_search(query='station_health_loop.ps1')` → found HEARTBEAT.md; no heartbeat JSON produced

**Root cause:** When user says "produce the latest Station heartbeat," model sometimes interprets as "search for heartbeat-related files" and runs repo_search. DM succeeded because model used STATE in context without searching. Intent ambiguity + stochastic tool choice.

---

## Refinement Recommendations

### 1. Heartbeat Fast Path (High Impact)

Add `_is_heartbeat_request(user_text)` — when user asks for "latest Station heartbeat," "produce heartbeat," "station heartbeat," etc., bypass LLM and return JSON from STATE:

```python
# In chat handler, after simple confirmation fast path:
if _is_heartbeat_request(req.user_text):
    state_md = _load_state_md()
    # Extract heartbeat_ts, health, checks from STATE
    return ChatResp(reply_text=heartbeat_json, ...)
```

**Benefit:** Deterministic, no tool misuse, consistent across all entry points.

### 2. Synthesis Grounding (High Impact)

- **Explicit top hit:** When synthesis runs after repo_search, pass the first hit path explicitly: `"Top hit from search: {path}. Your answer MUST cite this path exactly. Do not invent other paths."`
- **Stricter prompt:** "Use ONLY file paths that appear verbatim in the tool results. If no path matches, say 'No matching file found.'"

### 3. Event Ledger Search Tuning

- Increase `max_hits` for event_ledger-style queries (e.g. when query contains "event_ledger" or "emit") so synthesis has more context
- Consider deterministic fallback: if repo_search returns a hit containing `event_ledger` and `emit`, use that path directly in reply without synthesis

### 4. Intent Disambiguation in Prompt

Add to system prompt for local model: "When the user asks for 'Station heartbeat' or 'latest heartbeat,' answer from the <STATE> block. Do not search the repo. The heartbeat_ts, health, and checks are in STATE."

---

## Related Failure Events

- **FE-2026-02-26-9:** Synthesis hallucination (EventLedger.js, EventLedger.vue) — same pattern
- **FE-2026-02-26-2:** Simple confirmation fast path — analogous fix for heartbeat
- **FE-2026-02-26-6:** No synthesis after tools — synthesis added; grounding still weak

---

## Detection Signals

| Signal | Description |
|--------|-------------|
| `synthesis_hallucination_wrong_file` | Synthesis cites file path not in tool results |
| `heartbeat_intent_misinterpreted` | User asked for heartbeat; model ran repo_search instead |
| `cross_channel_response_variance` | Same prompt, different outcomes across entry points |
