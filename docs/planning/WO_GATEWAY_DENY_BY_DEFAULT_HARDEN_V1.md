---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1

**Status:** Implemented 2026-02-27
**Trigger:** FE-2026-02-27-1 (first public failure — gateway responded to unauthorized channels)

---

## Requirements

1. **Change _allowed_message semantics:**
   - `channel_allowlist == []` ⇒ deny all guild channels
   - `authorized_user_ids == []` ⇒ deny all DMs

2. **Add startup invariants:**
   - If `governance_required` and allowlists empty → exit(2) with clear stderr + ledger `gateway.config.invalid`

3. **Add config sources (order):**
   - CLI args
   - Env vars: `DISCORD_CHANNEL_ALLOWLIST`, `DISCORD_AUTHORIZED_USERS`
   - (optional) `DISCORD_IDS.md` parse

4. **Add "public redaction":**
   - If message destination is guild channel, never emit raw STATE JSON; summarize only

5. **Add preflight test script:**
   - `Scripts/discord_gateway_preflight.py` — validates config (deny-by-default, allowlist resolution)

---

## Implementation

| Item | Location |
|------|----------|
| _allowed_message | `calyx/cbo/discord_gateway.py` |
| Startup invariant | `main()` in discord_gateway.py |
| Config resolution | `_resolve_config()`, `_parse_discord_ids_md()` |
| Public redaction | `_redact_for_public()` in _on_message |
| Preflight | `Scripts/discord_gateway_preflight.py` |
| Start script env | `start_station_governed.ps1`, `sunrise_calyx.ps1` |

---

## Detection Signals (FE entries)

Added to each FE in FAILURE_EVENT_LOG.md for automated tripwire categorization.
