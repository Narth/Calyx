---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Station Calyx — Failure Event Log

**Status:** Held in equal importance to the Station Event Ledger. We will never know if we did right if we do not log our failures; we will continue to fail doing right if we do not learn from mistakes.

**Purpose:** Continuously appended and maintained source of Calyx trial and error. Log event failures with full analysis before applying changes. Each entry includes goal, end result, root cause, and rectification path for next test or governance check.

**Process:** Before a change is applied, complete the analysis. Rectification is the path for the next test or policy check.

---

## Event Log Format

Each entry uses:

| Field | Description |
|-------|-------------|
| **ID** | Unique identifier (FE-YYYY-MM-DD-N) |
| **Timestamp** | When observed |
| **Component** | CBO Core, Calyx Discord Gateway, Dev Harness, etc. |
| **Goal** | What the system was supposed to achieve |
| **End Result** | What actually happened |
| **Root Cause** | Why it failed |
| **Rectification** | How to fix for next test / governance check |
| **Status** | open | in_progress | resolved |
| **Detection Signal** | Identifier for automated tripwires / categorization |

---

## FE-2026-02-26-1: event_ledger Smoke Test — Tool Requests Overridden

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-1 |
| **Timestamp** | 2026-02-26 ~19:14 UTC |
| **Component** | CBO Core (`cbo_hub/cbo_core/app.py`) |
| **Goal** | User via Discord: "Search the Station repo for 'event_ledger' and tell me which file defines the emit function." Expected: `repo_search` with query `event_ledger` (or `event_ledger emit`), results synthesized, reply: `calyx/kernel/event_ledger.py`. |
| **End Result** | `repo_search` ran with `query='Calyx'`, `max_hits=5`. Results were from Calyx search, not event_ledger. Model's `tool_requests` JSON was echoed verbatim in reply instead of being executed. |
| **Root Cause** | 1) Deterministic block `if "search" in req.user_text.lower()` always runs `repo_search(query='Calyx', max_hits=5)` and overrides model intent. 2) Model's `tool_requests` may not have been parsed (JSON extraction from pretty-printed or wrapped output). 3) Even if parsed, deterministic block runs after model tool loop and its output appears; model's tool output may have been absent or overwritten. |
| **Rectification** | 1) Remove or gate the deterministic "search" block so it only runs when model has not already requested tools (`len(parsed) == 0`). 2) Improve `_parse_tool_requests` to extract JSON from markdown code blocks or mixed text (regex for `{...}`). 3) When model returns valid `tool_requests`, execute those first; do not run deterministic search if model already requested repo_search. |
| **Status** | resolved |
| **Resolved** | 2026-02-26: Gated deterministic search; improved JSON parse; suppress tool_requests in reply. |

---

## FE-2026-02-26-2: TinyLlama Hallucination on Simple Confirmations

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-2 |
| **Timestamp** | 2026-02-26 ~19:00–19:02 UTC |
| **Component** | CBO Core + Local LLM (TinyLlama) |
| **Goal** | User: "CBO, please confirm receipt of this message. No further action necessary." Expected: Brief "Message received." or similar. |
| **End Result** | Long hallucinated responses about BloomOS runbooks, Phase 6 + Kimi, BlOMOOS scripts, Raspberry Pi, etc. |
| **Root Cause** | TinyLlama too small for reliable instruction-following. Prompt instructed "reply briefly with a confirmation" but model ignored it. |
| **Rectification** | 1) **Applied:** Simple confirmation fast path — `_is_simple_confirmation_request()` bypasses LLM, returns "Message received." 2) **Applied:** Switched `LOCAL_LLM_MODEL_ID` to `qwen2.5-coder:7b`. 3) Band-aid acknowledged: fast path is mitigation; better model is primary fix. |
| **Status** | resolved |
| **Detection Signal** | llm_hallucination_confirmation |

---

## FE-2026-02-26-3: Calyx Discord Gateway — No Response, Agent Offline

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-3 |
| **Timestamp** | 2026-02-26 ~19:00 UTC (first sunrise) |
| **Component** | Calyx Discord Gateway (`calyx/cbo/discord_gateway.py`) |
| **Goal** | Discord DM → CBO /chat → reply to user. System activity observed; user expected reply. |
| **End Result** | No reply on Discord. Calyx Agent went offline. No `openclaw.channel.*` events in ledger. |
| **Root Cause** | 1) `discord.py` not installed in venv — gateway crashed on import. 2) Argparse bug: `args.no_governance_required` referenced but `--no-governance-required` not defined (had `--governance-required` with `type=bool`). 3) Gateway started in separate window; crash was silent. |
| **Rectification** | 1) **Applied:** `pip install discord.py>=2.0`. 2) **Applied:** Fixed argparse to use `--no-governance-required` with `action="store_true"`. 3) **Applied:** Error handling and stderr logging in `_on_message`. |
| **Status** | resolved |
| **Detection Signal** | gateway_crash_import_error, gateway_startup_failure |

---

## FE-2026-02-26-4: Model Returns Raw tool_requests JSON in Reply

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-4 |
| **Timestamp** | 2026-02-26 ~19:11 UTC |
| **Component** | CBO Core + Local LLM |
| **Goal** | User: "Run a tools check and confirm access." Expected: Tool results (repo_list, repo_search) summarized in natural language. |
| **End Result** | Reply included raw JSON block `{"tool_requests": [...]}` verbatim. Tool results (e.g. repo_list) present but mixed with JSON. Confusing UX. |
| **Root Cause** | Reply template includes `model_text` (raw LLM output) unconditionally. When model outputs JSON for tool_requests, that JSON is shown. No post-processing to hide or summarize executed tool_requests. |
| **Rectification** | When `parsed` (tool_requests) is non-empty and tools were executed: omit or replace raw `model_text` in reply with a short summary (e.g. "Tools executed: repo_list, repo_search. Results below."). Or: instruct model to not output raw JSON when requesting tools; have it describe intent instead. |
| **Status** | resolved |
| **Resolved** | 2026-02-26: When executed_tools and model_text is raw tool_requests JSON, suppress from reply. |
| **Detection Signal** | raw_tool_requests_json_in_reply |

---

## FE-2026-02-26-5: Raw tool_requests JSON Still Echoed (No Code Block)

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-5 |
| **Timestamp** | 2026-02-26 ~19:27 UTC |
| **Component** | CBO Core |
| **Goal** | Suppress raw tool_requests from reply when tools executed. |
| **End Result** | Raw JSON `{"tool_requests": [{"tool": "repo_search", ...}]}` still appeared in Discord reply. |
| **Root Cause** | Suppression regex only removes `\`\`\`json ... \`\`\`\` blocks. Model sometimes outputs raw JSON without markdown wrapper. |
| **Rectification** | Also remove standalone `{...}` JSON objects containing `tool_requests` (balanced-brace extraction). |
| **Status** | resolved |
| **Resolved** | 2026-02-26: Added standalone `{...}` removal (balanced-brace) for raw JSON without code block. |
| **Detection Signal** | raw_json_without_code_block |

---

## FE-2026-02-26-6: event_ledger Smoke Test — No Synthesized Reply

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-6 |
| **Timestamp** | 2026-02-26 ~19:31 UTC |
| **Component** | CBO Core (`cbo_hub/cbo_core/app.py`) |
| **Goal** | User: "Search the Station repo for 'event_ledger' and tell me which file defines the emit function. Summarize in one sentence." Expected: `repo_search` with correct query, then a one-sentence synthesized answer. |
| **End Result** | `repo_search` ran correctly with `query='event_ledger emit function'`, but reply contained only tool metadata (`[tool] repo_search(...)`, `Tools used: repo_search`, `Context: STATE.md injected`). No synthesized one-sentence summary. |
| **Root Cause** | Single-shot flow: model outputs `tool_requests`, tools execute, reply = header + tool_notes + display_model_text + footer. When model_text is only JSON (suppressed), display_model_text is empty. No second LLM call to synthesize tool results into a natural-language answer. |
| **Rectification** | Add a second LLM call when tools were executed and user asked for synthesis: inject tool results into prompt, ask model to summarize in one sentence. Or: include tool hits in reply so user at least sees raw results when synthesis is absent. |
| **Status** | resolved |
| **Resolved** | 2026-02-26: Added synthesis pass (second _call_local) when tools ran and display_model_text empty. |
| **Detection Signal** | no_synthesis_after_tool_execution |

---

## FE-2026-02-26-7: repo_search Returned FAILURE_EVENT_LOG Instead of Code

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-7 |
| **Timestamp** | 2026-02-26 ~19:34 UTC |
| **Component** | Dev Harness (`cbo_hub/dev_harness/app.py`) |
| **Goal** | Search for "event_ledger" and "emit function" → return `calyx/kernel/event_ledger.py`. |
| **End Result** | With max_hits=1, search returned `docs/operations/FAILURE_EVENT_LOG.md:114` (FE-6 description containing that phrase). Meta-contamination: failure log describes the search, so it matched. |
| **Root Cause** | repo_search has no exclusions. FAILURE_EVENT_LOG is self-referential; it documents failures using the same phrases users search for. |
| **Rectification** | Exclude FAILURE_EVENT_LOG.md from repo_search via `--glob '!**/FAILURE_EVENT_LOG.md'`. |
| **Status** | resolved |
| **Resolved** | 2026-02-26: Added REPO_SEARCH_IGNORE_GLOBS in dev_harness. |
| **Detection Signal** | repo_search_meta_contamination |

---

## FE-2026-02-26-8: Raw JSON + No Synthesis (19:41)

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-8 |
| **Timestamp** | 2026-02-26 ~19:41 UTC |
| **Component** | CBO Core |
| **Goal** | event_ledger smoke test: correct query, synthesized one-sentence, no raw JSON. |
| **End Result** | `repo_search` ran with `query='event_ledger emit'`, but reply contained raw JSON `{"tool_requests": [{"tool": "repo_search", ...}]}` and no synthesized answer. |
| **Root Cause** | 1) CBO Core likely not restarted — station_patch_sunrise -StopFirst ran but ports stayed in use; old process still serving. 2) Or: suppression/synthesis has edge case (e.g. JSON with `glob` key). |
| **Rectification** | 1) Ensure sunset actually stops processes (elevated run or stronger kill). 2) Add fallback: when executed_tools and display_model_text still contains `tool_requests` after removal, clear it. 3) Run station_patch_sunrise and verify CBO Core restarts (check process PID changed). |
| **Status** | resolved |
| **Resolved** | 2026-02-26: Explicit sunset (sunset_calyx.ps1 with taskkill /F /T) + calyx_sunset_sunrise.ps1. Fallback suppression added. |
| **Detection Signal** | raw_json_no_synthesis, stale_process_not_restarted |

---

## FE-2026-02-26-9: Synthesis Hallucination — Wrong File Cited

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-26-9 |
| **Timestamp** | 2026-02-26 ~19:47 UTC |
| **Component** | CBO Core synthesis pass (qwen2.5-coder:7b) |
| **Goal** | event_ledger smoke test: correct file `calyx/kernel/event_ledger.py`, one-sentence summary. |
| **End Result** | Synthesis ran, no raw JSON, but reply said "src/components/EventLedger.js" — file does not exist in Station repo. Correct: `calyx/kernel/event_ledger.py`. |
| **Root Cause** | Synthesis model hallucinated plausible filename from training (React/JS patterns). May not have grounded in tool_notes; or max_hits=1 returned correct hit but model ignored it. |
| **Rectification** | 1) Increase max_hits for synthesis context. 2) Synthesis prompt: "Cite ONLY files from the tool results below. Do not invent filenames." 3) Pass top hit path explicitly in synthesis prompt. |
| **Status** | in_progress |
| **Applied** | 2026-02-26: Synthesis prompt updated to "cite ONLY files from tool results; use ONLY file paths from tool results above." |
| **Detection Signal** | synthesis_hallucination_wrong_file |

---

## FE-2026-02-27-1: First Public Failure — Gateway Responded to Unauthorized Channels

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-1 |
| **Timestamp** | 2026-02-26 ~20:02–20:44 UTC (public) |
| **Component** | Calyx Discord Gateway (`calyx/cbo/discord_gateway.py`) + start scripts |
| **Goal** | Gateway should respond ONLY to: (1) DM from user 315642751419023371, (2) channel 1465903939659632807 (Station Health). All other channels denied. |
| **End Result** | Gateway responded to ALL channels in Intellectual Hideout server, including #no-context (783466052566777876). Public users (@Ice, Murk2, Ser Barl Slasher, etc.) received CBO replies. Internal STATE/checks JSON leaked to public channel. Synthesis hallucinated "station/src/components/EventLedger.vue". User had to revoke bot token to stop. |
| **Root Cause** | 1) **Empty allowlists = allow all:** `_allowed_message` logic: when `channel_allowlist` is empty, `if self.channel_allowlist and ...` is False (empty list falsy), so we never return False for channels → allow all. Same for `authorized_user_ids` and DMs. 2) **Start scripts never pass allowlists:** `start_station_governed.ps1` and `sunrise_calyx.ps1` start gateway without `--channel-allowlist` or `--authorized-users`. Default = empty = allow everything. 3) **Deny-by-default not implemented:** No explicit "require allowlist or deny" policy. |
| **Rectification** | 1) Change default: empty allowlist = DENY for server channels; empty authorized_user_ids = DENY for DMs. 2) Start scripts MUST pass allowlists from DISCORD_IDS or config. 3) Add DISCORD_CHANNEL_ALLOWLIST and DISCORD_AUTHORIZED_USERS env vars; gateway reads them if args not provided. 4) Document: public deployment requires explicit allowlist. |
| **Status** | resolved |
| **Resolved** | 2026-02-27: WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1 applied. |
| **Rectification Verified** | 2026-02-27: TEST 1 PASS (empty allowlists → exit 2, ledger gateway.config.invalid). TEST 2/3 pending human. Sunrise PASS. See GATEWAY_VALIDATION_REPORT_2026-02-27.md. |
| **Detection Signal** | gateway_responded_unauthorized_channel, empty_allowlist_allow_all, state_json_leaked_public |

---

## FE-2026-02-27-2: Three-Channel Smoke Test — Variance and Failures

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-2 |
| **Timestamp** | 2026-02-27 ~08:02–08:03 UTC |
| **Component** | CBO Core (local model) + Avatar Web + Calyx Discord Gateway |
| **Goal** | Identical prompts via three entry points: (1) event_ledger emit file, (2) produce latest Station heartbeat. Expected: consistent correct answers. |
| **End Result** | **event_ledger:** All three hallucinated wrong file paths (`Station/src/event_handler.c`, `/path/to/station_repo/src/event_ledger/emitter.py`, `src/modules/event_log/ledger.cpp`). Correct: `calyx/kernel/event_ledger.py`. **Heartbeat:** Browser and public channel searched repo instead of producing; DM correctly returned `{"heartbeat_ts": "2026-02-26T14:14:47Z"}`. |
| **Root Cause** | 1) **Synthesis hallucination (FE-9 persists):** qwen2.5-coder synthesis invents paths; does not ground in tool results. 2) **Heartbeat intent misinterpreted:** "Produce latest Station heartbeat" — model sometimes runs repo_search for "heartbeat" instead of using injected STATE. 3) **Non-determinism:** Same prompt, different tool choices and outputs across sessions. |
| **Rectification** | 1) Add heartbeat fast path (`_is_heartbeat_request`) — bypass LLM, return STATE heartbeat JSON. 2) Strengthen synthesis grounding: pass top hit path explicitly; "cite ONLY paths from tool results." 3) Intent disambiguation in prompt: "When user asks for Station heartbeat, answer from STATE; do not search." |
| **Status** | resolved |
| **Resolved** | 2026-02-27: WO_REQUEST_ORIENTATION_PROTOCOL_V1 — heartbeat + file-location fast paths. |
| **Detection Signal** | synthesis_hallucination_wrong_file, heartbeat_intent_misinterpreted, cross_channel_response_variance |
| **Report** | docs/operations/VALIDATION_REPORT_2026-02-27.md |

---

## FE-2026-02-27-3: FILE_LOCATION Ignores Search Target (FAILURE EVENT)

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-3 |
| **Timestamp** | 2026-02-27 ~08:37 UTC |
| **Component** | CBO Core intent orientation + FILE_LOCATION fast path |
| **Goal** | User: "Search the Station repo for FAILURE EVENT and tell me which file defines the emit function." Expected: Consider search target "FAILURE EVENT" → return FAILURE_EVENT_LOG.md or clarify emit vs. failure event. |
| **End Result** | Discord DM & Public: returned `event_ledger.py`. Browser: returned `app.py`. All ignored "FAILURE EVENT" search target. |
| **Root Cause** | INTENT_FILE_LOCATION matches "which file defines" + "emit" and routes to deterministic path. Never considers explicit search target ("FAILURE EVENT"); defaults to emit-defining files. |
| **Rectification** | When "search for X" + "which file defines Y" with X ≠ Y, do not use FILE_LOCATION fast path — route to FREE_CHAT. Add parsing of search target before fast path. |
| **Status** | resolved |
| **Resolved** | 2026-02-27: WO_REQUEST_ORIENTATION_PROTOCOL_V2 — INTENT_COMPOUND_QUERY. |
| **Detection Signal** | file_location_ignores_search_target, compound_query_misrouted |
| **Report** | docs/operations/SMOKE_TEST_REPORT_2026-02-27.md |

---

## FE-2026-02-27-4: "Confirm What a Failure Event Looks Like" — No Knowledge Path

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-4 |
| **Timestamp** | 2026-02-27 ~08:39–08:40 UTC |
| **Component** | CBO Core + local model (FREE_CHAT) |
| **Goal** | User: "CBO, please confirm what a failure event looks like to Station Calyx." Expected: Answer from FAILURE_EVENT_LOG.md — format (ID, Timestamp, Component, Goal, End Result, Root Cause, Rectification, Status). |
| **End Result** | Discord DM: "No matching file found. Tools used: repo_list." Public: Wrong tools (station_health_check, heartbeat_ts). Browser: Synthesized from training (health checks, heartbeat) — not from FAILURE_EVENT_LOG. |
| **Root Cause** | No INTENT_FAILURE_EVENT_QUERY. "confirm what" ≠ INTENT_CONFIRMATION. Model stochasticity; FAILURE_EVENT_LOG excluded from repo_search (REPO_SEARCH_IGNORE_GLOBS). |
| **Rectification** | Add INTENT_FAILURE_EVENT_QUERY for "failure event" + ("looks like" | "format" | "what"). Allow FAILURE_EVENT_LOG in search when query explicitly mentions "failure event". |
| **Status** | resolved |
| **Resolved** | 2026-02-27: WO_REQUEST_ORIENTATION_PROTOCOL_V2 — INTENT_FAILURE_EVENT_QUERY; read FAILURE_EVENT_LOG.md directly. |
| **Detection Signal** | failure_event_query_unhandled, wrong_tools_for_knowledge_query |
| **Report** | docs/operations/SMOKE_TEST_REPORT_2026-02-27.md |

---

## FE-2026-02-27-5: Three-Channel Equivalence Hash Parity — STATE Drift + policy_flags Variance

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-5 |
| **Timestamp** | 2026-02-27 |
| **Component** | CBO Core + canonical_parity_check (`Scripts/canonical_parity_check.py`) |
| **Goal** | 3-channel heartbeat test (api, browser, discord): equivalence_hash identical across entry points for same request. |
| **End Result** | VARIANCE DETECTED. API: response_sha256 e1a104afe1df6ab9...; Browser/Discord: 073aae54f0c249fc... (match). Browser and Discord: same response_sha256 but different equivalence_hash (6ada1eb7 vs 6e6d66c8). |
| **Root Cause** | 1) **STATE drift:** API request ran at T1; Browser/Discord at T2. STATE.md was updated between requests (heartbeat_ts, checks, or update_state_checks). Heartbeat response is derived from STATE.md; different STATE content → different response_sha256 → different equivalence_hash. 2) **policy_flags in equivalence bundle:** Equivalence bundle includes `governance_required`. Discord (governed) has governance_required=true; Browser (direct /chat) has false. Same response text, but policy_flags differ → different equivalence_hash. governance_required does not affect heartbeat output. |
| **Rectification** | 1) **STATE drift:** Run 3-channel test in tight sequence (<30s) with no STATE updates between requests. Or: snapshot STATE.md before test; restore after. Or: document that parity test requires "frozen" STATE. 2) **policy_flags:** Exclude `governance_required` from equivalence bundle (WO_CANONICAL_EQUIVALENCE_HASH_V2 refinement) — it does not affect output. Or: treat governed vs ungoverned as distinct parity groups. |
| **Status** | open |
| **Detection Signal** | crh_parity_equivalence_mismatch, state_drift_heartbeat, policy_flags_governance_variance |

---

## Governance / Policy Checks Before Next Test

Before running the next smoke test or governance check:

1. ~~**FE-2026-02-26-1:** Resolve deterministic search vs model tool_requests conflict.~~ Resolved.
2. ~~**FE-2026-02-26-4:** Suppress raw tool_requests JSON in replies.~~ Resolved.
3. ~~**Validation:** Re-run event_ledger smoke test.~~ Pass (WO_REQUEST_ORIENTATION_PROTOCOL_V1).
4. ~~**FE-6:** Add synthesis pass when tools executed~~ Resolved.
5. ~~**FE-2026-02-27-3:** FILE_LOCATION ignores search target.~~ Resolved (WO_V2 INTENT_COMPOUND_QUERY).
6. ~~**FE-2026-02-27-4:** Add INTENT_FAILURE_EVENT_QUERY.~~ Resolved (WO_V2).

---



---

## FE-2026-02-27-6: [Auto] claim.failed — budget_violation

| Field | Content |
|-------|---------|
| **ID** | FE-2026-02-27-6 |
| **Timestamp** | 2026-02-27 ~20:44 UTC |
| **Component** | CBO Core (`cbo_hub/cbo_core/app.py`) |
| **Goal** | Emit and verify canonical_hash receipt |
| **End Result** | claim.failed |
| **Root Cause** | wall_time_ms=78316>60000 |
| **Rectification** | Investigate artifact_path, verify preflight dirs exist |
| **Status** | open |
| **Detection Signal** | claim_failed_budget_violation, corr_id=58d8e6ff-c0cc-4a |



---

## FE-2026-03-02-1: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-1 |
| **Timestamp** | 2026-03-02 ~21:16 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-2: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-2 |
| **Timestamp** | 2026-03-02 ~21:16 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-3: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-3 |
| **Timestamp** | 2026-03-02 ~21:36 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-4: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-4 |
| **Timestamp** | 2026-03-02 ~21:36 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-5: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-5 |
| **Timestamp** | 2026-03-02 ~21:37 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-6: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-6 |
| **Timestamp** | 2026-03-02 ~21:38 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-7: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-7 |
| **Timestamp** | 2026-03-02 ~21:52 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-02-8: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-02-8 |
| **Timestamp** | 2026-03-02 ~21:52 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-03-1: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-03-1 |
| **Timestamp** | 2026-03-03 ~16:04 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-03-2: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-03-2 |
| **Timestamp** | 2026-03-03 ~16:06 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-03-3: [Auto] governance violation — orphan_outbound_action

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-03-3 |
| **Timestamp** | 2026-03-03 ~16:50 UTC |
| **Component** | calyx_gateway |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | orphan_outbound_action |
| **Root Cause** | Outbound send attempted without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | orphan_outbound_action, id=gateway |



---

## FE-2026-03-03-4: [Auto] claim.failed — budget_violation

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-03-4 |
| **Timestamp** | 2026-03-03 ~18:44 UTC |
| **Component** | CBO Core (`cbo_hub/cbo_core/app.py`) |
| **Goal** | Emit and verify canonical_hash receipt |
| **End Result** | claim.failed |
| **Root Cause** | wall_time_ms=60224>60000 |
| **Rectification** | Investigate artifact_path, verify preflight dirs exist |
| **Status** | open |
| **Detection Signal** | claim_failed_budget_violation, corr_id=801b94e3-4f4b-4d |



---

## FE-2026-03-09-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-09-1 |
| **Timestamp** | 2026-03-09 ~22:43 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-09-2: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-09-2 |
| **Timestamp** | 2026-03-09 ~22:57 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-1 |
| **Timestamp** | 2026-03-10 ~00:02 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-2: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-2 |
| **Timestamp** | 2026-03-10 ~00:02 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-3: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-3 |
| **Timestamp** | 2026-03-10 ~00:03 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-4: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-4 |
| **Timestamp** | 2026-03-10 ~00:03 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-5: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-5 |
| **Timestamp** | 2026-03-10 ~00:30 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-03-10-6: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-03-10-6 |
| **Timestamp** | 2026-03-10 ~00:30 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-1 |
| **Timestamp** | 2026-04-15 ~21:56 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-2: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-2 |
| **Timestamp** | 2026-04-15 ~21:56 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-3: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-3 |
| **Timestamp** | 2026-04-15 ~21:57 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-4: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-4 |
| **Timestamp** | 2026-04-15 ~21:57 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-5: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-5 |
| **Timestamp** | 2026-04-15 ~22:00 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-6: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-6 |
| **Timestamp** | 2026-04-15 ~22:00 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-7: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-7 |
| **Timestamp** | 2026-04-15 ~22:01 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-8: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-8 |
| **Timestamp** | 2026-04-15 ~22:01 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-9: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-9 |
| **Timestamp** | 2026-04-15 ~22:11 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-15-10: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-15-10 |
| **Timestamp** | 2026-04-15 ~22:11 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-1 |
| **Timestamp** | 2026-04-16 ~01:27 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-2: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-2 |
| **Timestamp** | 2026-04-16 ~01:27 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-3: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-3 |
| **Timestamp** | 2026-04-16 ~18:43 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-4: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-4 |
| **Timestamp** | 2026-04-16 ~18:57 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-5: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-5 |
| **Timestamp** | 2026-04-16 ~20:07 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-6: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-6 |
| **Timestamp** | 2026-04-16 ~20:35 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-16-7: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-16-7 |
| **Timestamp** | 2026-04-16 ~23:54 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-17-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-17-1 |
| **Timestamp** | 2026-04-17 ~00:17 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-23-1: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-23-1 |
| **Timestamp** | 2026-04-23 ~21:58 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |



---

## FE-2026-04-23-2: [Auto] governance violation — ungoverned_compute

| Field | Content |
|-------|---------|
| **ID** | FE-2026-04-23-2 |
| **Timestamp** | 2026-04-23 ~21:58 UTC |
| **Component** | cbo_core |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | ungoverned_compute |
| **Root Cause** | Tool execution without corr_id or task_corr_id |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | ungoverned_compute, id=cbo |

## Changelog

| Date | Change |
|------|--------|
| 2026-02-26 | Initial log: FE-1 through FE-4 from Calyx Discord Gateway implementation and smoke tests |
| 2026-02-26 | FE-1, FE-4 resolved. Preamble: log held equal to Station ledger; continuously appended. Rectification applied: gate deterministic search, improve JSON parse, suppress raw tool_requests in reply. |
| 2026-02-26 | FE-5: Raw JSON without code block still echoed. Added standalone `{...}` removal. FE-1 status corrected to resolved. |
| 2026-02-26 | FE-6: Tool ran correctly (query fixed) but no synthesized reply. Single-shot flow; no second LLM call to summarize tool results. |
| 2026-02-26 | FE-6 resolved: Added synthesis pass (second _call_local) when tools ran and model output suppressed. |
| 2026-02-26 | FE-7: repo_search returned FAILURE_EVENT_LOG (meta-contamination). Excluded via REPO_SEARCH_IGNORE_GLOBS. |
| 2026-02-26 | FE-8: Raw JSON + no synthesis at 19:41. Likely CBO Core not restarted; add fallback suppression. |
| 2026-02-26 | FE-9: Synthesis hallucinated src/components/EventLedger.js. Correct: calyx/kernel/event_ledger.py. |
| 2026-02-27 | FE-2026-02-27-1: First public failure. Gateway responded to all channels (empty allowlist = allow all). STATE leaked. Token revoked. |
| 2026-02-27 | WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1: deny-by-default, startup invariants, config sources, public redaction, preflight. Detection signals added to all FE entries. |
| 2026-02-27 | FE-2026-02-27-2: Three-channel smoke test (browser, DM, public). event_ledger: all hallucinated wrong paths; heartbeat: 2/3 searched instead of producing. Refinement: heartbeat fast path, synthesis grounding. |
| 2026-02-27 | WO_REQUEST_ORIENTATION_PROTOCOL_V1: Intent gate, heartbeat/file-location fast paths. FE-2026-02-27-2 resolved. |
| 2026-02-27 | FE-2026-02-27-3: FILE_LOCATION ignores search target (FAILURE EVENT + emit). FE-2026-02-27-4: No failure event knowledge path. |
| 2026-02-27 | WO_REQUEST_ORIENTATION_PROTOCOL_V2: INTENT_COMPOUND_QUERY, INTENT_FAILURE_EVENT_QUERY. FE-3, FE-4 resolved. |
| 2026-02-27 | FE-2026-02-27-5: 3-channel equivalence hash parity. STATE drift (API vs Browser/Discord) + policy_flags variance (Browser vs Discord). |
