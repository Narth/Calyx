# Gateway Contract (Public Edge)

## Non-negotiable deployment rule
**Only the Gateway is public. Station Calyx remains private/loopback-only.**

- Public clients -> Gateway (auth, rate limit, validation)
- Gateway -> Station Calyx (`http://127.0.0.1:8420`) over private path
- Direct internet access to Station Calyx endpoints is forbidden

## Gateway MVP controls
1. **HMAC-signed requests** (shared secret per client)
2. **Rate limiting** (per client/IP)
3. **Schema validation** (strict JSON schema per endpoint)
4. **Allowlisted forwarding** only to explicitly mapped Station endpoints
5. **Audit logs** with redacted payload previews only

## Minimal forwarding contract

### Public endpoint
`POST /gateway/v1/reflect`

### Required headers
- `X-Calyx-Key-Id: <client-id>`
- `X-Calyx-Timestamp: <unix-seconds>`
- `X-Calyx-Signature: sha256=<hex-hmac>`

### Request body
```json
{
  "recent": 100,
  "session_id": "optional"
}
```

### Forwarding behavior
- Validate signature/timestamp skew
- Validate schema (bounds and types)
- Enforce rate limit
- Forward to Station: `POST http://127.0.0.1:8420/v1/reflect`
- Return Station response with gateway `request_id`

## Hardening notes
- Reject timestamp skew > 60s
- Use constant-time HMAC comparison
- Apply strict body size limits
- Never forward arbitrary paths from user input
