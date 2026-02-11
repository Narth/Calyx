# Gateway MVP Skeleton

This folder contains a minimal reference gateway used to expose Station Calyx safely.

- Public binds: allowed
- Station binds: loopback/private only
- Forwarding target default: `http://127.0.0.1:8420`

## Run locally

```bash
pip install -r deploy/gateway/requirements.txt
uvicorn deploy.gateway.gateway:app --host 127.0.0.1 --port 9443
```

## Environment
- `CALYX_GATEWAY_HMAC_SECRET` (required)
- `CALYX_GATEWAY_MAX_RPM` (default: 60)
- `CALYX_STATION_BASE_URL` (default: `http://127.0.0.1:8420`)
