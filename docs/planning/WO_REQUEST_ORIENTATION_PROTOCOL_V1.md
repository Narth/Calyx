---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_REQUEST_ORIENTATION_PROTOCOL_V1

**Status:** Implemented 2026-02-27
**Trigger:** FE-2026-02-27-2 (three-channel smoke test variance; synthesis hallucination; heartbeat intent misinterpretation)

---

## Objective

Establish Human-Sovereign Entry Gate + Deterministic Intent Orientation. Before any tool call, LLM reasoning, synthesis, or repo search, the system MUST classify intent deterministically, bind to canonical sources of truth, and decide whether a fast path applies.

**Non-negotiable:** LLMs do not classify authority. LLMs do not decide whether to use STATE. LLMs do not invent file paths.

---

## Architecture: Human Entry Gate

```
Human Request (Discord / Browser / API)
         │
         ▼
┌─────────────────────────────────────┐
│  human.request.received             │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  classify_intent(user_text)         │  ← Deterministic, no LLM
│  intent.classified                  │
└─────────────────────────────────────┘
         │
    ┌────┴────┬────────────┬────────────┐
    ▼         ▼            ▼            ▼
INTENT_    INTENT_     INTENT_      INTENT_
HEARTBEAT  FILE_       CONFIRMATION FREE_CHAT
           LOCATION    │             │
    │         │        │             │
    ▼         ▼        ▼             ▼
 Fast Path  Fast Path  Fast Path   LLM + Tools
 (STATE)    (repo_     (Message    + Synthesis
            search)    received)   Guardrail
```

---

## Implementation

| Component | Location |
|-----------|----------|
| Intent classification | `calyx/kernel/intent_orientation.py` |
| Heartbeat fast path | `cbo_hub/cbo_core/app.py` — INTENT_HEARTBEAT |
| File location fast path | `cbo_hub/cbo_core/app.py` — INTENT_FILE_LOCATION |
| Confirmation fast path | `cbo_hub/cbo_core/app.py` — INTENT_CONFIRMATION |
| Synthesis grounding guardrail | `cbo_hub/cbo_core/app.py` — post-synthesis validation |
| STATE extraction | `_extract_heartbeat_from_state()` in app.py |

---

## Intents (v1)

| Intent | Trigger | Fast Path |
|--------|---------|-----------|
| INTENT_HEARTBEAT | "heartbeat", "produce station heartbeat" | STATE.md → JSON |
| INTENT_FILE_LOCATION | "where is" + emit/defined, "event_ledger emit", "which file defines" | repo_search → top hit path |
| INTENT_CONFIRMATION | "confirm receipt", "hello", "ping", etc. | "Message received." |
| INTENT_EXECUTE | "execute" | (future) CBO executor |
| INTENT_STATE_QUERY | "state" (not heartbeat) | (future) STATE summary |
| INTENT_FREE_CHAT | else | LLM + tools + synthesis guardrail |

---

## Telemetry Events

| Event | When |
|-------|------|
| human.request.received | Every /chat ingress |
| intent.classified | After classify_intent |
| fastpath.used | Heartbeat or file location fast path taken |
| heartbeat.fastpath | Heartbeat returned from STATE |
| file_location.deterministic | File path returned from repo_search |
| file_location.none | No matching file found |
| tool.used | Tools executed (repo_list, repo_search) |
| synthesis.invoked | Synthesis pass ran |
| synthesis.violation | Synthesis cited path not in tool results |
| synthesis.hallucination_detected | Synthesis path hallucination; override applied |
| response.finalized | Response sent |

---

## Sample Ledger Traces

### Heartbeat Request

```json
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"human.request.received","msg":"Human ingress","data":{"entry_point":"browser","session_id":"home"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"intent.classified","msg":"Intent classified","data":{"intent":"INTENT_HEARTBEAT","entry_point":"browser"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"fastpath.used","msg":"Heartbeat fast path","data":{"intent":"INTENT_HEARTBEAT","deterministic_path_used":true}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"heartbeat.fastpath","msg":"Heartbeat returned from STATE","data":{"heartbeat_ts":"2026-02-26T14:14:47Z"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"response.finalized","msg":"Response sent (heartbeat fast path)","data":{"intent":"INTENT_HEARTBEAT","deterministic_path_used":true}}
```

### File Location Request

```json
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"human.request.received","msg":"Human ingress","data":{"entry_point":"discord_1465903939659632807","session_id":"discord_1465903939659632807"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"intent.classified","msg":"Intent classified","data":{"intent":"INTENT_FILE_LOCATION","entry_point":"discord_1465903939659632807"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"fastpath.used","msg":"File location deterministic path","data":{"intent":"INTENT_FILE_LOCATION","deterministic_path_used":true,"path":"calyx/kernel/event_ledger.py"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"file_location.deterministic","msg":"File location result","data":{"path":"calyx/kernel/event_ledger.py","query":"event_ledger emit"}}
{"ts":"2026-02-27T...","level":"INFO","component":"cbo","event":"response.finalized","msg":"Response sent (file location fast path)","data":{"intent":"INTENT_FILE_LOCATION","deterministic_path_used":true}}
```

---

## Validation Protocol (Phase 7)

Re-run Three-Channel Smoke Test:

| Prompt | Expected (all channels) |
|--------|-------------------------|
| "Produce the latest Station heartbeat." | Identical JSON from STATE. No repo_search. |
| "Where is the event_ledger emit function defined?" | `calyx/kernel/event_ledger.py`. No invented paths. |

If variance occurs: fail validation, log FE entry, do not proceed to sunrise.

---

## Edge Cases Discovered

1. **Windows paths:** repo_search hits use `path:line:content`; Windows `C:\path` requires regex `^(.+):\d+:` for extraction.
2. **INTENT_FILE_LOCATION without allow_tools:** Falls through to FREE_CHAT; no deterministic path. Consider adding repo_search even when allow_tools=false for this intent.
3. **Synthesis guardrail:** Only triggers when synthesis contains a file extension (.py, .js, etc.) but no allowed path. Plain wrong answers (no path) are not caught.
4. **event_ledger query:** Use `glob: "**/event_ledger.py"` to restrict search to the defining file; otherwise app.py (import) can rank before event_ledger.py.
