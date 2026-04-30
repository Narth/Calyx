---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Station Calyx Isolation Analysis

**Date:** 2026-02-26
**Prepared by:** CBO
**Purpose:** System-wide analysis of what operates through Station governance vs in isolation. Response to: OpenClaw activity not visible in ledger; Discord DM possibly producing isolated fragments.

---

## Executive Summary

**Finding:** OpenClaw and Discord DM traffic do **not** uniformly flow through Station Calyx. Most OpenClaw activity is **isolated** — it only touches CBO when the calyx-cbo-bridge skill is explicitly invoked. Discord via OpenClaw = OpenClaw LLM + workspace by default; no ledger, no governance spine.

**Recommendation:** Require all OpenClaw-originated actions to route through CBO Core (or add an OpenClaw → ledger bridge). Document and remediate isolated paths.

---

## 1. Architecture: What Should Flow Through Station

Per design intent:
- **Every user-visible action** should validate through Station
- **Every significant decision** should emit to the Event Ledger
- **Discord, OpenClaw, Avatar Web, Telemetry** should all route through CBO Core for governance

---

## 2. Current Wiring vs Isolation

### 2.1 Wired to Station (Ledger + Governance)

| Component | Entry Point | Ledger Events | Governance |
|-----------|-------------|---------------|------------|
| **CBO Core** | HTTP 7778 | cbo.chat.*, cbo.state.*, cbo.execute.*, cbo.sponsorship.* | Full |
| **Avatar Web** | HTTP 7780 → proxy to CBO | avatar.chat_proxy, avatar.whiteboard.* | Via CBO |
| **Telemetry Gateway** | HTTP 7781 → proxy to CBO | telemetry.chat_proxy, telemetry.health_check | Via CBO |
| **Dev Harness** | HTTP 7777 | dev_harness.repo_* | Receipts only |
| **discord_intake** (Python) | When running | cbo.discord.inbound, mail.ingest.*, router.* | Full spine |
| **Heartbeat** | update_state_checks.ps1 | heartbeat.tick | STATE.md |

### 2.2 Isolated (No Ledger, No Governance)

| Component | Why Isolated | Impact |
|-----------|--------------|--------|
| **OpenClaw Gateway** | Node.js process; not part of Station Python stack | All Discord/WhatsApp/Telegram traffic when OpenClaw is used |
| **OpenClaw native LLM** | Responds directly from Ollama/Anthropic/OpenAI; does not call CBO | Most Discord DM replies = isolated |
| **calyx-cbo-bridge skill** | **Only when model invokes it** — get_state, send_to_cbo, execute | When invoked → CBO called → ledger. But invocation is model-dependent, not guaranteed |
| **Discord via OpenClaw** | OpenClaw owns Discord; discord_intake is stopped | No cbo.discord.inbound/outbound; no mail spine |
| **calyx.cbo.api** (port 8080) | Separate service; not in start_calyx_core_services | /heartbeat, /objective, /report — no ledger |
| **bridge_overseer** | Python loop; not wired to ledger | Reflect→Plan→Act→Critique — no ledger |
| **station_health_loop** | PowerShell; no emit | health.tick, health.fail — no ledger (emit_heartbeat_tick is from update_state_checks, not loop) |

### 2.3 Discord: Two Mutually Exclusive Paths

| Mode | Handler | Flow | Ledger |
|------|---------|------|--------|
| **OpenClaw** | OpenClaw Gateway | Discord → OpenClaw LLM → response. Optional: bridge skill → CBO | Only when bridge invoked |
| **Calyx-only** | discord_intake | Discord → Mail envelope → CBO ingest → spine → DiscordResponseHandler | cbo.discord.inbound, outbound, mail.*, router.* |

**You cannot run both.** One Discord bot = one connection. When using OpenClaw, discord_intake is stopped. So Discord DM via OpenClaw = **isolated by default**.

---

## 3. OpenClaw Integration Gap

### 3.1 Intended vs Actual

| Intended | Actual |
|----------|--------|
| OpenClaw validates through Station | OpenClaw uses workspace files; CBO only when bridge skill invoked |
| Discord traffic flows through CBO | Discord → OpenClaw → LLM. Bridge is optional tool. |
| All actions auditable in ledger | Only CBO Core HTTP calls appear; OpenClaw activity invisible |
| Governance spine for every decision | OpenClaw makes decisions (LLM, tools) outside spine |

### 3.2 When Bridge *Is* Used

When the OpenClaw model decides to call `get_state`, `send_to_cbo`, `sponsorship`, or `execute`:
- HTTP request hits CBO Core
- Ledger emits: cbo.state.request, cbo.chat.request, cbo.chat.complete, cbo.execute.*, cbo.sponsorship.*
- Governance applies (integrity gate, contract, receipts)

**Problem:** The model chooses. Casual chat ("hello", "what's the status?") may not trigger tools. User must phrase requests to elicit tool use, or we must change the default behavior.

---

## 4. Timeline of Developments — Isolation Map

| Development | Wired? | Ledger? | Notes |
|-------------|--------|---------|-------|
| CBO Core (7778) | Yes | Yes | Phase 1 nervous system |
| Dev Harness (7777) | Yes | Yes | Phase 1 |
| Avatar Web (7780) | Yes | Yes | Proxies to CBO |
| Telemetry Gateway (7781) | Yes | Yes | Proxies to CBO |
| discord_intake | Yes | Yes | When running; mutually exclusive with OpenClaw |
| OpenClaw Gateway | No | No | External Node.js; no Station integration |
| calyx-cbo-bridge skill | Partial | When invoked | Optional tool; not default path |
| calyx.cbo.api (8080) | No | No | Separate CBO API; not in core services |
| bridge_overseer | No | No | Heartbeat loop; no ledger |
| station_health_loop | No | No | Writes station_health.json; no emit |
| Intent pipeline | Partial | Router only | ingest, mint — no emit (Phase 2 plan) |
| Hub runner | No | No | Execution; no emit (Phase 2 plan) |

---

## 5. Recommendations

### 5.1 Immediate: OpenClaw Governance

1. **Default path through CBO:** Configure OpenClaw so that Discord (and other channel) messages are routed to CBO Core by default, not to the native LLM. Options:
   - Custom OpenClaw channel handler that always calls send_to_cbo first
   - Or: Make send_to_cbo the primary response path; LLM used only for local/offline fallback

2. **Emit OpenClaw-originated events:** Add a lightweight HTTP endpoint or sidecar that OpenClaw calls on every message (inbound + outbound) to emit to the ledger. Event: `openclaw.discord.inbound`, `openclaw.discord.outbound` with source=openclaw.

3. **Bridge skill as mandatory:** If bridge cannot be default, document that users must explicitly say "send to CBO" or "get state" to get governance. Add prompt injection: "For station commands, always use get_state or send_to_cbo."

### 5.2 Short-Term: Complete Nervous System

1. **Phase 2 wiring:** Intent pipeline, hub runner, gates (per STATION_NERVOUS_SYSTEM_WIRING_PLAN.md)
2. **station_health_loop:** Invoke Python emit helper for health.tick, health.fail, health.recovered
3. **calyx.cbo.api:** Add ledger middleware and emits if this service is in use
4. **bridge_overseer:** Add bridge.pulse.start, bridge.pulse.complete

### 5.3 Validation

1. **Discord DM test:** Send a message via OpenClaw Discord. Run `ledger_tail -n 20`. If no cbo.chat.* or openclaw.* events, the path is isolated.
2. **Bridge test:** Say "get state" or "send to CBO: hello" via Discord. Ledger should show cbo.state.request or cbo.chat.request.
3. **discord_intake test:** Stop OpenClaw, start discord_intake. Send DM. Ledger should show cbo.discord.inbound, mail.ingest.accept, cbo.discord.outbound.

---

## 6. Conclusion

**OpenClaw is not fully wired to Station Calyx governance.** Discord DM via OpenClaw operates in an isolated fragment unless the user or model explicitly invokes the calyx-cbo-bridge skill. To meet the standard that "every implementation must validate and confirm operations through the Station first," we need either:

- **Option A:** Route all OpenClaw channel traffic through CBO Core by default (architectural change)
- **Option B:** Add an OpenClaw → ledger bridge so at least inbound/outbound messages are auditable, even if governance is partial
- **Option C:** Use discord_intake instead of OpenClaw for Discord when full governance is required (mutually exclusive with OpenClaw)

This document serves as the system-wide isolation analysis for CGPT validation and remediation planning.
