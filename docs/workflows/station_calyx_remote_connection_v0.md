# Station Calyx — Remote Connection (Telemetry) v0

**Purpose:** Let the human submit commands and work via Station Calyx from a laptop (or other device) on a **different network** — e.g. when away from the host running Calyx Core.

**Status:** v0 design + minimal gateway.

---

## Options

| Option | Description | Pros | Cons |
|--------|-------------|------|-----|
| **A. Ngrok to Avatar Web** | Expose Avatar Web (7780) via ngrok; use browser on laptop to hit the ngrok URL. | No new code; full UI. | No built-in auth; anyone with URL can use UI. |
| **B. Ngrok to CBO Core** | Expose CBO Core (7778) via ngrok; laptop sends POST /chat to ngrok URL. | Direct API; scripts/CLI easy. | No UI; need to secure (e.g. secret query param or header). |
| **C. Telemetry gateway** | Run a small gateway (e.g. port 7781) that checks a secret and proxies to CBO Core; expose gateway via ngrok. | Single place for auth; can add rate limit or audit later. | One more process. |

Recommended for v0: **C** — run the telemetry gateway, expose it with ngrok, call it from the laptop with a shared secret.

---

## Telemetry gateway (v0)

- **Listen:** `http://0.0.0.0:7781` (part of core services; started with `Scripts\start_calyx_core_services.ps1` or `Scripts\start_telemetry_gateway.ps1`).
- **Endpoint:** `POST /chat` — same JSON body as CBO Core `/chat` (user_text, session_id, mode, allow_tools, model_role, allow_second_opinion).
- **Auth:** If env `TELEMETRY_SECRET` is set, request must include `X-Telemetry-Secret: <value>` or `Authorization: Bearer <value>`. **Recommend setting it** when exposing via ngrok.
- **Identity isolation:** Header **`X-Telemetry-Client-ID`** is **required** (e.g. `jorge_laptop`). Session IDs are namespaced per client (`tg_<client_id>_<session>`) so your context never mixes with another user or with local Avatar Web.
- **Audit log:** Every `/chat` request is logged to `cbo_hub/logs/telemetry_gateway_audit.jsonl` (timestamp, client_id, path, status, body_sha256_16, forwarded_for). No PII in log; auditorial level for security review.
- **Home node refresh:** After each successful `/chat`, the gateway runs `Scripts\update_state_checks.ps1` in the background so the home node’s STATE.md is updated and gateway runs always make it back to the hub.
- **Proxy:** Forwards to `http://127.0.0.1:7778/chat`, returns CBO response.
- **Health:** `GET /health` returns 200 when CBO Core is reachable.

**Start:** Gateway is started with core services. Or run only the gateway: `.\Scripts\start_telemetry_gateway.ps1 [-StopFirst]`. Set `TELEMETRY_SECRET` in env before starting if you want auth.

**Expose from your host (e.g. with ngrok):**

```bash
ngrok http 7781
```

From the laptop (different network, different internet connection):

```powershell
$headers = @{
  "Content-Type" = "application/json"
  "X-Telemetry-Secret" = "your-shared-secret"
  "X-Telemetry-Client-ID" = "jorge_laptop"
}
$body = '{"user_text":"CBO, please confirm receipt.","session_id":"home","mode":"dev","allow_tools":true,"model_role":"workhorse"}'
Invoke-RestMethod -Uri "https://<ngrok-host>/chat" -Method Post -Body $body -Headers $headers
```

---

## Security notes

- **TELEMETRY_SECRET:** Use a long random string; do not commit it. Set it in env before starting the gateway. **Strongly recommended** when opening the station via ngrok to prevent unauthorized access.
- **X-Telemetry-Client-ID:** Required. Use a stable id per device (e.g. `jorge_laptop`). Prevents mixing your session context with others; all sessions are namespaced `tg_<client_id>_<session>`.
- **Audit log:** `cbo_hub/logs/telemetry_gateway_audit.jsonl` — one JSON line per request (ts_utc, client_id, path, status, body_sha256_16, forwarded_for). Review periodically for abuse or anomalies.
- **Ngrok:** Free tier gives a random URL; only people with the URL (and secret, if set) can reach the gateway. For fixed hostnames or IP allowlists, use ngrok paid or another tunnel.
- **HTTPS:** Ngrok provides TLS; the gateway itself runs HTTP and is only bound to 0.0.0.0 so the tunnel can forward to it.

---

## Runbook (quick start)

1. On Station Calyx host: `.\Scripts\start_calyx_core_services.ps1 [-StopFirst]` (includes Telemetry Gateway). Set `$env:TELEMETRY_SECRET` if you want auth.
2. Expose gateway: `ngrok http 7781`.
3. On laptop (different location/network): POST to `https://<ngrok-url>/chat` with headers `X-Telemetry-Secret`, `X-Telemetry-Client-ID`, and same JSON body as CBO Core.

---

*Canonical doc for remote command/telemetry access to Station Calyx. Update when adding auth schemes or new endpoints.*
