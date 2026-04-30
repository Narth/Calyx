# Station Calyx - Stack completion and browser API policy

Status: canonical support policy, 2026-04-23.

Purpose: finish building and hardening the Station Calyx stack before exposing any browser-based API service. Harden the tools first.

Authority boundary: this policy supports the canonical control plane. It does not make Telemetry Gateway a core service, does not make `STATE.md` sole authoritative truth, and does not authorize new runtime exposure.

---

## Policy

1. **Stack first.** Station Calyx canonical core services (Dev Harness, CBO Core, Avatar Web), canonical support services (Telemetry Gateway and CLI Avatar where applicable), scripts (start, check, update_state_checks), and gateway auth/audit must be complete and hardened before we consider opening any new browser-based API or exposing the existing Avatar Web beyond localhost.

2. **Avatar Web is localhost-only.** Avatar Web (7780) binds to `127.0.0.1` only. Do **not** expose it via ngrok or any public URL until this policy is updated to allow it. Remote access is via the **Telemetry Gateway** (7781) only - auth, client isolation, and audit in place. **Telemetry Gateway** is canonical support, not core reasoning authority and not the normal operator path. It is the explicit network-binding override: it binds to `0.0.0.0:7781` (not loopback) so it is reachable via tunnel from the laptop node; all other Station services bind to `127.0.0.1`.

3. **No new browser API surface** until the stack-complete and hardened checklists below are satisfied and an explicit decision is made to open browser-based access.

---

## Stack-complete checklist

- [ ] Core services and support services start reliably via `Scripts\start_calyx_core_services.ps1` and pass `Scripts\check_calyx_core_services.ps1`.
- [ ] `STATE.md` is refreshed after start (validation delay + update_state_checks) and on each heartbeat; gateway runs refresh home node STATE. `STATE.md` remains an advisory digest, not sole authoritative truth.
- [ ] Telemetry Gateway: `TELEMETRY_SECRET` recommended when exposed; `X-Telemetry-Client-ID` required; audit log in use; health check implemented.
- [ ] Runbooks and `CALYX_CORE_SERVICES.md` are current; `HEARTBEAT.md` drives state refresh.

---

## Hardened-tools checklist

- [ ] Check script: TCP probe with sensible timeout; exit code or output usable by callers.
- [ ] Update_state_checks: requires check script and `STATE.md`; does not corrupt STATE on failure.
- [ ] Start script: correct order; optional `-StopFirst`; post-start validation (check + update_state) runs after delay.
- [ ] Gateway: auth when secret set; audit every request; no forwarding of arbitrary paths; body size/validation as needed.

---

## When we're ready

When both checklists are satisfied and the architect approves, we can:
- Revisit exposing Avatar Web (for example behind auth) or adding a dedicated browser API service.
- Update this doc to reflect the new allowance and any conditions.

Until then, harden the tools; do not open browser-based API service.
