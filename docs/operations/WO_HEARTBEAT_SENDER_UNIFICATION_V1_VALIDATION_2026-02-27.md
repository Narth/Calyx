---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# WO_HEARTBEAT_SENDER_UNIFICATION_V1 — Validation Report

**Date:** 2026-02-27
**Status:** Implementation complete

---

## Implementation Summary

| Requirement | Status |
|-------------|--------|
| `discord.heartbeat.sender.identity` on gateway startup | Done |
| CALYX_HEARTBEAT_PUSH_ENABLED respected by all senders | Done (gateway only sender) |
| Legacy sender deprecation (OpenClaw note) | Done |
| audit_health heartbeat validation | Done |

---

## discord.heartbeat.sender.identity

Emitted by Calyx Discord Gateway on startup. Fields:

- `component`: calyx_gateway
- `pid`: process ID
- `module_entrypoint`: calyx.cbo.discord_gateway
- `heartbeat_sender_enabled`: true when CALYX_HEARTBEAT_PUSH_ENABLED and config allow; false otherwise

---

## Validation (audit_health)

After sunrise:

```bash
python Scripts/audit_health.py --since-minutes 60
```

Expected:

- Task triggers/budgets match heartbeat sends (each calyx_gateway.heartbeat has system.task.triggered and budget.task.recorded within ±5s)
- No calyx_gateway.heartbeat without adjacent task events
- Exactly one discord.heartbeat.sender.identity with heartbeat_sender_enabled=true (when gateway is the active sender)

---

## Legacy Sender (OpenClaw)

When using OpenClaw as Discord handler: disable any periodic heartbeat in OpenClaw config. See `docs/OPENCLAW_CALYX_INTEGRATION.md` step 7.
