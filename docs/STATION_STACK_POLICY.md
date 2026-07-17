# Station Calyx - Stack completion and browser API policy

Status: canonical support policy with current accuracy correction, 2026-07-17.

Purpose: finish building and hardening the Station Calyx stack before exposing any browser-based API service. Harden the tools first.

Authority boundary: this policy supports the canonical control plane. It does not make Telemetry Gateway a core service, does not make `STATE.md` sole authoritative truth, and does not authorize new runtime exposure.

> [!CAUTION]
> The checklists below are not satisfied, and remote exposure is not approved by this document. The current gateway enforces a shared secret only when one is inherited by its process, uses a self-asserted client label rather than identity isolation, does not integrate with CBO Core strict source attestation, exposes unauthenticated health/schema routes, and has no claimed automatic audit-log rotation. See [gateway.md](gateway.md) and [SECURITY.md](../SECURITY.md).

---

## Policy

1. **Stack first.** Station Calyx canonical core services (Dev Harness, CBO Core, Avatar Web), canonical support services (Telemetry Gateway and CLI Avatar where applicable), scripts (start, check, update_state_checks), and gateway auth/audit must be complete and hardened before we consider opening any new browser-based API or exposing the existing Avatar Web beyond localhost.

2. **Avatar Web is localhost-only.** Avatar Web (7780) binds to `127.0.0.1` only. Do **not** expose it via ngrok or any public URL until this policy is updated to allow it. If a future remote path is explicitly approved, it must use a corrected and bounded **Telemetry Gateway** (7781), not direct core exposure. The current gateway is canonical support, not core reasoning authority or the normal operator path; its wider bind does not itself authorize remote use.

3. **No new browser API surface** until the stack-complete and hardened checklists below are satisfied and an explicit decision is made to open browser-based access.

---

## Stack-complete checklist

- [ ] Core services and support services start reliably via `Scripts\start_calyx_core_services.ps1` and pass `Scripts\check_calyx_core_services.ps1`.
- [ ] `STATE.md` is refreshed after start (validation delay + update_state_checks) and on each heartbeat; gateway runs refresh home node STATE. `STATE.md` remains an advisory digest, not sole authoritative truth.
- [ ] Telemetry Gateway: require a non-empty inherited `TELEMETRY_SECRET`; treat `X-Telemetry-Client-ID` as an untrusted label; integrate strict source attestation; restrict health/schema routes; verify the configured upstream; and enforce bounded audit retention.
- [ ] Runbooks and `CALYX_CORE_SERVICES.md` are current; `HEARTBEAT.md` drives state refresh.

---

## Hardened-tools checklist

- [ ] Check script: TCP probe with sensible timeout; exit code or output usable by callers.
- [ ] Update_state_checks: requires check script and `STATE.md`; does not corrupt STATE on failure.
- [ ] Start script: correct order; optional `-StopFirst`; post-start validation (check + update_state) runs after delay.
- [ ] Gateway: fail closed when no secret is configured; authenticate approved callers; document and audit rejected as well as admitted attempts; prevent session-namespace collisions; restrict routes and upstreams; enforce body limits and bounded retention.

---

## When we're ready

When both checklists are satisfied and the architect approves, we can:
- Revisit exposing Avatar Web (for example behind auth) or adding a dedicated browser API service.
- Update this doc to reflect the new allowance and any conditions.

Until then, harden the tools; do not open browser-based API service.
