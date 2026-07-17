---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# First Public Failure Event — Report

**Date:** 2026-02-27
**Incident:** Calyx Discord Gateway responded to unauthorized channels in Intellectual Hideout server
**Severity:** High — public exposure of Station internals; governance breach

---

## 1. What Happened

### Timeline (2026-02-26, ~20:02–20:44 UTC)

1. **20:02** — User (Narth) sent event_ledger smoke test via DM. Bot responded with hallucinated file: "station/src/components/EventLedger.vue" (correct: `calyx/kernel/event_ledger.py`).

2. **20:07** — Public channel #no-context (ID 783466052566777876): User @Ice typed "true???" — bot responded. Same channel: "?", "PASS", "I need an adult", "help", "they taking over", "INFO DEV ZZZ VE", "INFO C X POTOPE", "LOGS" — bot responded to all.

3. **20:07–20:08** — Bot leaked internal STATE as raw JSON to public channel (status, heartbeat_ts, checks, health, entropy_tier).

4. **20:08** — Bot hallucinated fake log entries: "2026-02-24T12:34:56Z - INFO - CBO Hub maintenance mode activated" (not from any real log).

5. **20:08** — User "@Narth help" triggered repo_list with path that caused "Path escapes repo root" error; model then ran repo_search.

6. **20:25–20:29** — User (Narth) in #no-context: "Oh what is happening", "Okay, testing", "Test" — bot responded. "Test" and "ping" later got "Message received." (confirmation fast path).

7. **20:28, 20:30** — User explicitly asked: "block all discord communication channels except for this one." Bot acknowledged but did not enforce; continued responding in #no-context.

8. **20:35** — User provided correct IDs: channel 1465903939659632807, user 315642751419023371. Bot acknowledged but gateway was not restarted with these allowlists.

9. **20:44** — User revoked bot token to stop unauthorized responses.

---

## 2. Why It Happened

### Primary Cause: Empty Allowlist = Allow All

The gateway's `_allowed_message` logic:

```python
if self.channel_allowlist and channel_id not in self.channel_allowlist:
    return False
return True
```

When `channel_allowlist` is **empty** (`[]`), `self.channel_allowlist` is falsy, so the condition is False — we never return False. We fall through to `return True`. **Empty list = allow all channels.**

Same for DMs: when `authorized_user_ids` is empty, all DMs are allowed.

### Secondary Cause: Start Scripts Never Pass Allowlists

- `start_station_governed.ps1` starts the gateway with no `--channel-allowlist` or `--authorized-users`.
- `sunrise_calyx.ps1` same.
- DISCORD_IDS.md documents the correct IDs (channel 1465903939659632807, user 315642751419023371) but nothing reads them at startup.

### Tertiary: No Deny-by-Default

Station Calyx governance doctrine says "Deny-by-default." The gateway defaulted to allow when allowlists were empty — the opposite.

---

## 3. Impact

| Impact | Description |
|--------|-------------|
| **Public exposure** | Internal STATE (checks, health, heartbeat_ts) visible to anyone in #no-context |
| **Unauthorized access** | Public users could trigger CBO, repo_list, repo_search |
| **Hallucination** | Wrong file paths; fake log entries |
| **Governance breach** | User explicitly requested channel restriction; request was not enforced |
| **Token revocation** | User had to revoke token to stop; service disruption |

---

## 4. How to Avoid It in the Future

### Immediate (Before Next Gateway Start)

1. **Deny-by-default:** When `channel_allowlist` is empty, deny all server channels. When `authorized_user_ids` is empty, deny all DMs. Require explicit allowlist for any response.

2. **Start scripts must pass allowlists:** Read DISCORD_IDS or env; pass `--channel-allowlist 1465903939659632807` and `--authorized-users 315642751419023371` to the gateway.

3. **Env vars:** Support `DISCORD_CHANNEL_ALLOWLIST` and `DISCORD_AUTHORIZED_USERS` (comma-separated) so config can be set without editing start scripts.

### Process

4. **Pre-public checklist:** Before deploying to a server with non-trusted users: verify allowlists are set, test with alt account in disallowed channel, confirm no response.

5. **Documentation:** Add "Public deployment" section to gateway docs: require explicit allowlist; empty = deny.

---

## 5. Related Failure Events

- **FE-9:** Synthesis hallucination (EventLedger.vue, EventLedger.js) — same pattern; model invents paths.
- **FE-4, FE-5, FE-8:** Raw JSON in replies — STATE leak to public is analogous; internal data should not reach unauthorized audiences.

---

## 6. References

- `calyx/cbo/discord_gateway.py` — `_allowed_message`
- `Scripts/start_station_governed.ps1`, `Scripts/sunrise_calyx.ps1`
- `DISCORD_IDS.md`
- `docs/operations/FAILURE_EVENT_LOG.md` — FE-2026-02-27-1

---

## 7. Validation (2026-02-27)

**WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1** validation run:

| Test | Result | Date |
|------|--------|------|
| TEST 1 — Empty allowlists fail closed | PASS | 2026-02-27 |
| TEST 2 — Single allowlisted channel | PENDING (human) | — |
| TEST 3 — Public STATE redaction | PENDING (human) | — |
| Sunrise | PASS | 2026-02-27 |

Commit: 572d5a366bc0cd53dfd49aa2eea37d65590b0512
Report: `docs/operations/GATEWAY_VALIDATION_REPORT_2026-02-27.md`
