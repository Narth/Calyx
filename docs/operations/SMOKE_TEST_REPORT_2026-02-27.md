---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Three-Channel Smoke Test — Failure Event Report

**Date:** 2026-02-27
**Context:** Post WO_REQUEST_ORIENTATION_PROTOCOL_V1. Four prompts tested across Browser, Discord DM, and Public Channel.

---

## Test Matrix

| Test | Prompt | Discord DM | Public Channel | Browser |
|------|--------|------------|----------------|----------|
| 1 | event_ledger emit | ✅ event_ledger.py | ✅ event_ledger.py | ✅ event_ledger.py |
| 2 | FAILURE EVENT + emit | ❌ event_ledger.py | ❌ event_ledger.py | ❌ app.py |
| 3 | Produce latest Station heartbeat | ✅ JSON | ✅ JSON | ✅ JSON |
| 4 | Confirm what a failure event looks like | ❌ No matching file found | ❌ Wrong tools | ⚠️ Synthesized (not from FE log) |

---

## FE-2026-02-27-3: FILE_LOCATION Ignores Search Target (FAILURE EVENT)

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-3 |
| **Timestamp** | 2026-02-27 ~08:37 UTC |
| **Component** | CBO Core intent orientation + FILE_LOCATION fast path |
| **Goal** | User: "Search the Station repo for FAILURE EVENT and tell me which file defines the emit function." Expected: Consider search target "FAILURE EVENT" → return `docs/operations/FAILURE_EVENT_LOG.md` (documents failure events) or clarify that emit is in event_ledger.py while FAILURE_EVENT_LOG documents failure event format. |
| **End Result** | Discord DM & Public: returned `event_ledger.py`. Browser: returned `app.py`. All ignored "FAILURE EVENT" search target. |
| **Root Cause** | INTENT_FILE_LOCATION matches on "which file defines" + "emit" and routes to deterministic file-location path. The path uses `event_ledger` in user text to set query/glob; when user says "FAILURE EVENT" (not "event_ledger"), we default to `def emit` with no glob. We never consider the explicit search target ("FAILURE EVENT") — we only look for emit-defining files. |
| **Rectification** | 1) When user says "search for X" + "which file defines Y", parse both X and Y. If X ≠ Y (e.g. X=FAILURE_EVENT, Y=emit), do not use FILE_LOCATION fast path — route to FREE_CHAT for nuanced answer. 2) Add INTENT_FAILURE_EVENT_QUERY: "failure event" + ("looks like" | "format" | "confirm") → repo_search FAILURE_EVENT_LOG, return format summary. 3) Or: require search target to match file-location target before using fast path. |
| **Status** | open |
| **Detection Signal** | file_location_ignores_search_target, compound_query_misrouted |

---

## FE-2026-02-27-4: "Confirm What X Looks Like" — No Failure Event Knowledge Path

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-4 |
| **Timestamp** | 2026-02-27 ~08:39–08:40 UTC |
| **Component** | CBO Core + local model (FREE_CHAT) |
| **Goal** | User: "CBO, please confirm what a failure event looks like to Station Calyx." Expected: Answer from FAILURE_EVENT_LOG.md — format (ID, Timestamp, Component, Goal, End Result, Root Cause, Rectification, Status, Detection Signal). |
| **End Result** | Discord DM: "No matching file found. Tools used: repo_list" — model ran only local availability check, no repo_search for failure event. Public: Ran repo_search for 'station_health_check.ps1' and 'heartbeat_ts' — wrong tools, wrong answer. Browser: Synthesized answer about health checks, heartbeat stale, lock status — reasonable but not from FAILURE_EVENT_LOG.md; from general training. |
| **Root Cause** | 1) No INTENT_FAILURE_EVENT_QUERY — "failure event" + "looks like" / "confirm" routes to FREE_CHAT. 2) "confirm" does not match INTENT_CONFIRMATION (we require "confirm receipt" etc.; "confirm what" is different). 3) Model stochasticity: sometimes requests no tools (repo_list only), sometimes wrong tools, sometimes synthesizes from training instead of tool results. 4) FAILURE_EVENT_LOG excluded from repo_search (REPO_SEARCH_IGNORE_GLOBS) — so even if model searched "failure event", it would not find the log. |
| **Rectification** | 1) Add INTENT_FAILURE_EVENT_QUERY: when "failure event" + ("looks like" | "format" | "what" | "confirm") → deterministic path: repo_search with glob override to include FAILURE_EVENT_LOG, or read FAILURE_EVENT_LOG directly, return format summary. 2) Revisit REPO_SEARCH_IGNORE_GLOBS: FAILURE_EVENT_LOG was excluded to avoid meta-contamination for "event_ledger" searches; for explicit "failure event" queries we should allow it. 3) Consider allowlist: when user explicitly asks about "failure event", include FAILURE_EVENT_LOG in search. |
| **Status** | open |
| **Detection Signal** | failure_event_query_unhandled, wrong_tools_for_knowledge_query |

---

## Summary

| Outcome | Count |
|---------|-------|
| **Pass** | 6 (event_ledger ×3, heartbeat ×3) |
| **Fail** | 5 (FAILURE EVENT ×3, confirm failure event ×2) |
| **Partial** | 1 (browser confirm — synthesized but not grounded) |

**WO_REQUEST_ORIENTATION_PROTOCOL_V1 validation:** Tests 1 and 3 now pass consistently across all channels. Deterministic fast paths work. New failure modes exposed: compound queries (search target vs. file target) and knowledge queries (failure event format) lack dedicated handling.

---

## WO_REQUEST_ORIENTATION_PROTOCOL_V2 Validation (2026-02-27)

| Test | Expected | Result |
|------|----------|--------|
| Test A: "Search for FAILURE EVENT and which file defines emit" | Two-section; X=FAILURE_EVENT_LOG, Y=event_ledger.py | PASS |
| Test B: "Confirm what a failure event looks like" | Structured format from FAILURE_EVENT_LOG.md | PASS |
