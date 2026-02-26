---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Canonical Operations Index

**Source of truth for current Station Calyx operations.** WO_DOC_HYGIENE_DEPRECATION_GATES_V1.

---

## Canonical Paths

| Capability | Canonical Path | Doc |
|------------|----------------|-----|
| Discord executor | Calyx Discord Gateway | `calyx/cbo/discord_gateway.py` |
| Governance ingress | Calyx Sign / gateway | `docs/operations/WO_CALYX_SIGN_INGRESS_AUTH_V4_VALIDATION_2026-02-26.md`, `docs/operations/calyx_sign.md` |
| Heartbeat sender | Calyx Discord Gateway (task-governed) | `docs/operations/WO_HEARTBEAT_SENDER_UNIFICATION_V1_VALIDATION_2026-02-27.md` |
| Audit tooling | `Scripts/audit_trace.py`, `Scripts/audit_anomalies.py`, `Scripts/audit_health.py` | `docs/operations/WO_AUDIT_QUERY_TOOLING_V1_VALIDATION_2026-02-27.md` |

---

## Startup

- **Sunrise:** `Scripts/start_calyx_core_services.ps1` (or `Scripts/sunrise_calyx.ps1` for full stack including Discord Gateway)
- **Discord Gateway:** `python -m calyx.cbo.discord_gateway`

---

## Config

- `CALYX_HEARTBEAT_PUSH_ENABLED` — gate for heartbeat sender
- `CALYX_GOVERNANCE_REQUIRED` — gate for governed ingress
