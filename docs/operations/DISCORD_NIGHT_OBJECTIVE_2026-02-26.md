---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Discord Gateway Night Objective — 2026-02-26

**Extended objective:** Make the Discord agent a reliable tool and disciplined extension of Station Calyx via remote calls and operations.

**Scope:** Plan, calculate, formulate, and execute subtle but relevant fixes until the Discord Gateway functions according to Station Calyx and BloomOS standards.

---

## Success Criteria

| Criterion | Target |
|-----------|--------|
| **event_ledger smoke test** | Correct file (`calyx/kernel/event_ledger.py`), no hallucination |
| **Raw JSON** | Never in reply (FE-4, FE-5, FE-8) |
| **Synthesis** | Grounded in tool results only (FE-9) |
| **Heartbeat via Discord** | STATE, HEALTH, HEARTBEAT status reported to user DM on schedule |
| **Sunset/sunrise** | Explicit procedure works; services load new code |

---

## Microfixes (ordered)

1. ~~**FE-9: Synthesis grounding**~~ — Applied: prompt "cite ONLY files from tool results; use ONLY file paths from tool results above."
2. **FE-9: max_hits** — Deferred (prompt fix sufficient for now).
3. ~~**Gateway heartbeat**~~ — Applied: _heartbeat_loop sends STATE/HEALTH every 30 min to DISCORD_HEARTBEAT_USER_ID.
4. **Gateway DM persistence** — Not needed; fetch_user + create_dm works.
5. ~~**Outbox for agent→Discord**~~ — Applied: runtime/discord_outbox.jsonl; gateway processes every 60s.

---

## Heartbeat Schedule (Discord)

- **Interval:** 30 minutes (configurable via env)
- **Content:** Status, checks, health, heartbeat_ts, entropy_tier
- **Recipient:** Authorized user DM (DISCORD_IDS: 315642751419023371)
- **Format:** Compact; Discord-friendly (no markdown tables)

---

## References

- FAILURE_EVENT_LOG.md (FE-1 through FE-9)
- calyx/cbo/discord_gateway.py
- cbo_hub/cbo_core/app.py (synthesis pass)
- HEARTBEAT.md
- STATE.md
