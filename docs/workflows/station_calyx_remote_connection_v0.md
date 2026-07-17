# Station Calyx Remote Connection (Telemetry) v0

> [!WARNING]
> **Superseded historical runbook. Do not follow its former quickstart.** The earlier version treated a shared secret as optional, overstated client isolation, encouraged direct tunnel exposure, and did not disclose current route, upstream, governance, or retention limits.

Status: retained as a historical pointer. It is not the current remote-access procedure or a canonical authorization.

Use these current sources instead:

- [Governed Network Gateway](../gateway.md)
- [Security Policy](../../SECURITY.md)
- [Getting Started](../GETTING_STARTED.md)
- [Station Stack Policy](../STATION_STACK_POLICY.md)

## Why the v0 procedure was retired

The implemented gateway currently has boundaries that the original runbook did not describe accurately:

- `TELEMETRY_SECRET` is enforced only when a non-empty value is inherited by the gateway process.
- `X-Telemetry-Client-ID` is a self-asserted label, not authentication.
- delimiter-based session namespacing can collide and is not tenant isolation.
- `/health` is unauthenticated, and FastAPI exposes `/docs`, `/redoc`, and `/openapi.json` by default.
- `CBO_CHAT_URL` defaults to loopback but can be configured to another endpoint.
- strict CBO Core source attestation currently rejects Telemetry Gateway chat forwarding.
- gateway audit metadata can be identifying or sensitive, and automatic log rotation is not currently claimed.

Do not expose Avatar Web (`7780`) or CBO Core (`7778`) directly. Treat any experiment involving Telemetry Gateway (`7781`) as bounded research behind a trusted outer network boundary, with the current limitations accepted explicitly.

No active remote quickstart is provided in this historical file.
