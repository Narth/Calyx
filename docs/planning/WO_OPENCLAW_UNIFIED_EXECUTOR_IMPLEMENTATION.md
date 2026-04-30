---
status: deprecated
owner: station
last_reviewed_utc: "2026-02-27"
superseded_by: docs/operations/CANONICAL_OPS_INDEX.md
doctrine_scope: historical
---

# WO_OPENCLAW_UNIFIED_EXECUTOR_V1 — Implementation Report

> **⚠️ OpenClaw is deprecated and forbidden as an executor/sender.**
> **If OpenClaw is running, Calyx may enter fail-closed mode.** See docs/operations/OPENCLAW_DECOMMISSION_PLAYBOOK.md.

**Date:** 2026-02-26
**Status:** Implemented (Phase 1–4)
**Reference:** STATION_ISOLATION_ANALYSIS_2026-02-26.md, OPENCLAW_CALYX_INTEGRATION.md

---

## Objective

Adopt OpenClaw (and governed Discord paths) as Calyx Executors under mandatory governance:

- Every OpenClaw-originated interaction must enter Station governance first, emit to the Event Ledger, pass integrity + sponsorship gates, and execute only via CBO-controlled path.
- OpenClaw must not respond directly from native LLM without Station approval, execute tools independently, or bypass the governance spine via optional skill invocation.

---

## Architectural Change

### Before

```
Discord → OpenClaw LLM → (optional bridge) → CBO
```

### After

```
Discord → Calyx Discord Gateway → CBO Core (7778) → Governance → Execution → Response → Gateway → Discord
         OR
Discord → OpenClaw → calyx-cbo-bridge (send_to_cbo) → CBO Core → Governance → ...
```

**CBO Core** is first responder, decision authority, execution controller, and ledger emitter.

---

## Implemented Changes

### Phase 1 — CBO Core: Governed Channel Detection

**File:** `cbo_hub/cbo_core/app.py`

- Added `_is_governed_channel(request, req)` — detects traffic via:
  - `X-Calyx-Source` header: `openclaw`, `calyx-discord-gateway`, `openclaw_bridge`
  - `session_id` containing `openclaw`
- **Ledger emits:**
  - `openclaw.channel.inbound` — at start of governed request
  - `openclaw.channel.rejected` — on integrity gate failure
  - `openclaw.channel.outbound` — on successful chat completion

### Phase 2 — Calyx Discord Gateway

**File:** `calyx/cbo/discord_gateway.py`

- New governed Discord path: Discord → CBO `/chat` → Discord.
- No local LLM. All messages POST to CBO with `X-Calyx-Source: calyx-discord-gateway`.
- **Environment:** `CALYX_GOVERNANCE_REQUIRED=true` (default) — never fall back to LLM when CBO down.
- **On CBO unreachable:** Emits `openclaw.channel.timeout`, replies "Station unavailable."
- **On boot:** Emits `openclaw.service.identity` (cwd, pid, governance_mode, cbo_base).

**Usage:**
```bash
# Requires: DISCORD_BOT_TOKEN, CBO Core running on 7778
python -m calyx.cbo.discord_gateway
# Or with options:
python -m calyx.cbo.discord_gateway --cbo-base http://127.0.0.1:7778 --timeout 90
```

**Discord Developer Portal:** Enable **Message Content Intent** (Bot → Privileged Gateway Intents) or the bot cannot read message content.

**Model role:** Default `model_role=local` (Ollama). Set `CBO_DISCORD_MODEL_ROLE` or `--model-role` for `none`, `workhorse`, `architect`, `second_opinion`. Tools (repo_list, repo_search) enabled when model_role supports them.

**Simple confirmation fast path:** Requests like "confirm receipt", "CBO?", "test message", "hello" bypass the LLM and return "Message received." to avoid TinyLlama hallucination. For general queries, use a stronger local model (e.g. `LOCAL_LLM_MODEL_ID=qwen2.5-coder:7b`) in `.env.cbo`.

**Discord ownership:** When using Calyx Discord Gateway, stop OpenClaw (same bot token). One bot = one connection.

### Phase 3 — Bridge Skill: Mandatory Header

**File:** `skills/calyx-cbo-bridge/index.js`

- `send_to_cbo` now sends `X-Calyx-Source: openclaw_bridge` on every CBO `/chat` call.
- Ensures bridge-originated traffic is detected as governed and emits `openclaw.channel.*`.

### Phase 4 — Ledger Visibility

All governed channel traffic now produces a visible chain:

| Event | When |
|-------|------|
| `openclaw.channel.inbound` | CBO receives governed request |
| `cbo.chat.request` | Chat processing starts |
| `cbo.chat.integrity_fail` + `openclaw.channel.rejected` | Integrity gate blocks |
| `cbo.chat.complete` | Chat success |
| `openclaw.channel.outbound` | Governed response sent |
| `openclaw.channel.timeout` | Gateway could not reach CBO |

---

## Required Safeguards (Implemented)

| Safeguard | Implementation |
|-----------|-----------------|
| **Circuit breaker** | Integrity gate failure → `openclaw.channel.rejected`; no direct LLM answer |
| **Timeout guard** | Gateway emits `openclaw.channel.timeout`; replies "Station unavailable." when governance required |
| **Identity emission** | Gateway emits `openclaw.service.identity` on boot |

---

## Validation Tests

### Test 1 — Casual Discord Message (Calyx Discord Gateway)

1. Start CBO Core: `Scripts\start_calyx_core_services.ps1`
2. Start Calyx Discord Gateway: `python -m calyx.cbo.discord_gateway`
3. Send "hello" via Discord

**Expected ledger chain:**
```
openclaw.channel.inbound
cbo.chat.request
cbo.chat.complete
openclaw.channel.outbound
```

### Test 2 — Integrity Failure

1. Trigger sponsorship invalid state (or mock integrity gate failure).
2. Send message via governed path.

**Expected:**
```
cbo.chat.integrity_fail
openclaw.channel.rejected
```
No direct LLM answer.

### Test 3 — Simulated CBO Offline

1. Stop CBO Core.
2. Send message via Calyx Discord Gateway.

**Expected:**
```
openclaw.channel.timeout
```
Reply: "Station unavailable." No native LLM answer when governance required.

---

## Discord Ownership Model

**Singular:** One Discord bot connection at a time.

| Mode | Handler | Flow |
|------|---------|------|
| **Calyx Discord Gateway** | `calyx.cbo.discord_gateway` | Discord → CBO /chat → Discord. Full governance, ledger visibility. |
| **OpenClaw + bridge** | OpenClaw Gateway + calyx-cbo-bridge skill | Discord → OpenClaw LLM. When model invokes `send_to_cbo` → CBO. Partial governance. |
| **discord_intake** | `calyx.cbo.discord_intake` | Discord → Mail envelope → CBO ingest → spine. Full governance. |

**Recommendation:** Use Calyx Discord Gateway when governance is mandatory. Use OpenClaw when multi-channel (WhatsApp, Telegram, etc.) is needed and bridge invocation is acceptable for CBO integration.

---

## OpenClaw Modifications — Not Feasible

The WO requested modifying OpenClaw to route all messages to CBO. **This is not feasible** with the current OpenClaw plugin/hook API:

- `message:received` hook fires but `event.messages.push()` has no effect (GitHub #23430) — cannot inject or replace the agent response
- No `agent:before-turn` hook exists to short-circuit the LLM
- OpenClaw source is external; we cannot patch the core message flow

**Solution: Harness / Wrapper**

Use `Scripts\start_station_governed.ps1` — the canonical harness that ensures:

1. **Discord never routes through OpenClaw** when governance is required
2. **Calyx Discord Gateway** owns Discord: Discord → CBO /chat → Discord
3. **OpenClaw is stopped** (or not started for Discord) — one bot = one connection
4. **No activity reaches this machine** without passing through Station Calyx

The `calyx-governance` plugin (`.openclaw/extensions/calyx-governance/`) emits a startup warning when OpenClaw runs: "For governed Discord, run start_station_governed.ps1".

---

## Deliverables Checklist

- [x] Code diff summary of CBO Core modifications (governed channel detection, openclaw.* emits)
- [x] Confirmation that native LLM path is disabled when governance required (Calyx Discord Gateway)
- [x] Ledger output chain documented (inbound → request → complete → outbound)
- [x] Discord ownership model documented and singular
- [x] calyx-cbo-bridge sends X-Calyx-Source for governed detection
