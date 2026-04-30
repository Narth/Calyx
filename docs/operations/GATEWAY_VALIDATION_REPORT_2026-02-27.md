---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Gateway Validation Report — WO_GATEWAY_DENY_BY_DEFAULT_HARDEN_V1

**Date:** 2026-02-27
**Runbook:** Validation & Troubleshooting (CBO)
**Commit:** 572d5a366bc0cd53dfd49aa2eea37d65590b0512
**Branch:** federation-sync-20260214

---

## Summary

| Test | Result | Notes |
|------|--------|------|
| TEST 1 — Governance + empty allowlists fail closed | **PASS** | Exit 2, stderr clear, ledger gateway.config.invalid |
| TEST 2 — Single allowlisted channel contains output | **PENDING** | Human user test required |
| TEST 3 — Public STATE leak prevention redacts | **PENDING** | Human user test required |
| Sunrise | **PASS** | All services started; gateway launched with valid allowlists |

---

## TEST 1 — Governance + Empty Allowlists Must FAIL CLOSED

**Goal:** Prove gateway refuses to start when governance required and allowlists empty.

**Steps executed:**
1. Cleared env: `DISCORD_CHANNEL_ALLOWLIST`, `DISCORD_AUTHORIZED_USERS` unset
2. Started gateway: `python -m calyx.cbo.discord_gateway` (no CLI allowlist args)

**Result:** **PASS**

| Criterion | Expected | Observed |
|-----------|----------|----------|
| Exit code | 2 | 2 |
| stderr | Clear invalid config message | "gateway.config.invalid: governance_required but allowlists empty. Set DISCORD_CHANNEL_ALLOWLIST and/or DISCORD_AUTHORIZED_USERS, or pass --channel-allowlist and --authorized-users." |
| Ledger event | gateway.config.invalid | Present: `14:09:20 ERROR gateway.config.invalid` |
| Discord messages | None | N/A (process exited before connect) |

**Ledger excerpt:**
```
14:09:20 ERROR gateway.config.invalid       gateway.config.invalid: governance_required but allowlists e corr=d68d8b1b…
```

---

## TEST 2 — Single Allowlisted Channel Must CONTAIN OUTPUT

**Goal:** Prove gateway responds only in allowlisted channel; no response in disallowed channels.

**Status:** **PENDING — Human user test required**

**Configuration used by sunrise:**
- `DISCORD_CHANNEL_ALLOWLIST` = 1465903939659632807 (CONTROL_CHANNEL_ID)
- `DISCORD_AUTHORIZED_USERS` = 315642751419023371 (AUTHORIZED_USER_ID)

**Human test steps (Architect):**
1. **Disallowed channel:** Send "ping" or "state" → expect no reply
2. **Allowed channel (1465903939659632807):** Send "ping" → expect reply only here
3. **DM (authorized user 315642751419023371):** Send "ping" → expect reply

**Preflight verification:** With allowlists set, preflight returns PASS.

---

## TEST 3 — Public STATE Leak Prevention Must REDACT

**Goal:** Prove guild channels never receive raw STATE JSON.

**Status:** **PENDING — Human user test required**

**Code verification:** `_redact_for_public()` in `calyx/cbo/discord_gateway.py`:
- Detects STATE-like JSON (`"status"`, `"checks"` keys)
- Replaces with: "Station status: see DM for details. (Public channels do not receive raw state.)"
- Applied when `is_guild_channel` before `channel.send()`

**Human test steps (Architect):**
1. In allowlisted guild channel: Send "state" or "get status"
2. Verify response is redacted summary only (no JSON)
3. In DM (authorized user): Send "state" → verify policy-compliant detail

---

## Final Sunrise

**Command:** `Scripts\calyx_sunset_sunrise.ps1 -SkipReadiness`

**Result:** PASS
- Sunset: All ports freed (7777, 7778, 7780, 7781)
- Sunrise: Dev Harness, CBO Core, Avatar Web, Telemetry Gateway started
- Validation: checks=dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok
- Gateway: Started with env vars (DISCORD_CHANNEL_ALLOWLIST, DISCORD_AUTHORIZED_USERS from sunrise script)

---

## Deviations / Fixes Applied

None. All automated steps passed.

---

## Human User Test Required

**Architect must perform:**
1. Message in disallowed channel → expect silence
2. Message in allowed channel (1465903939659632807) → expect response
3. "state" in allowed channel → expect redacted (no raw JSON)
4. "state" in DM (authorized user) → expect policy-compliant detail

**Note:** If DISCORD_BOT_TOKEN was revoked, gateway will not connect to Discord. Re-issue token before human test.

---

## Scratch Log

`runtime/notes/gateway_validation__20260227_1200.md`
