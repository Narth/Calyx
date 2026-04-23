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

## Sunrise deployment sequence

When you change any sunrise-wired component, run sunrise to deploy:

1. **Sunset** — `Scripts\sunset_calyx.ps1` (stops loops, Bridge Overseer, CLI Avatar, core services)
2. **Sunrise** — `Scripts\start_calyx_core_services.ps1` (or `Scripts\sunrise_calyx.ps1`)

**Sunrise-wired components:** Dev Harness, CBO Core, Avatar Web, Telemetry Gateway, station_health_loop, navigator_triage_loop, energy_churn_cp9_loop, cp6_cp7_loop, bridge_overseer, **cli_avatar**, discord_gateway.

Changes to CLI Avatar (e.g. `allow_second_opinion` wiring), CBO Core, Bridge Overseer, or loops require sunset → sunrise to take effect.

---

## Config

- `CALYX_HEARTBEAT_PUSH_ENABLED` — gate for heartbeat sender
- `CALYX_GOVERNANCE_REQUIRED` — gate for governed ingress
