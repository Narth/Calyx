# Network Evidence Push v0 Workflow

**Version:** v0 (LAN-Only)  
**Status:** Token-Gated, Append-Only  
**Date:** 2026-01-10

---

## Overview

This workflow enables evidence push from remote Station Calyx nodes over a private LAN. The receiving node exposes a token-protected HTTP endpoint that accepts evidence envelopes and writes them to append-only per-node journals.

**Use Case:** Push telemetry from a laptop to a workstation over home/office LAN without manual file transfer.

---

## Constraints (Non-Negotiable)

| Constraint | Description |
|------------|-------------|
| **Evidence only** | Ingest accepts evidence envelopes only |
| **No commands** | No remote execution, no task triggers |
| **No remote control** | Receiver stores evidence; no action taken |
| **Append-only** | Evidence journals are never modified |
| **Token-gated** | Network access requires valid token |
| **Bounded** | Request size and envelope count limits enforced |
| **Audited** | All ingest attempts logged to audit trail |

---

## Server Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CALYX_INGEST_TOKEN` | Yes (for LAN) | None | Bearer token for authentication |
| `CALYX_ALLOWED_NODE_IDS` | No | (allow all) | Comma-separated list of allowed node IDs |
| `CALYX_INGEST_MAX_ENVELOPES` | No | 100 | Max envelopes per request |
| `CALYX_INGEST_MAX_BYTES` | No | 1048576 (1MB) | Max request body size |
| `CALYX_INGEST_ENABLED` | No | false | Must be "true" to enable network ingest |

### Generate a Token

```powershell
# Generate a secure random token
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `EXAMPLE_TOKEN_REDACTED_DO_NOT_USE_IN_PRODUCTION`

### Start Server on LAN IP

```powershell
# Set environment variables
$env:CALYX_INGEST_TOKEN = "your-secure-token-here"
$env:CALYX_INGEST_ENABLED = "true"

# Optional: Restrict to specific nodes
$env:CALYX_ALLOWED_NODE_IDS = "laptop-001,laptop-002"

# Start server bound to LAN IP (not 127.0.0.1)
python -B -m station_calyx.api.server --host 192.168.1.100 --port 8420
```

**Important:** Replace `192.168.1.100` with your workstation's actual LAN IP.

### Find Your LAN IP

```powershell
# Windows
ipconfig | Select-String "IPv4"

# Or
(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*"}).IPAddress
```

---

## Client Configuration (Laptop)

### Push Evidence to Server

```powershell
# Set the token
$token = "<REDACTED_TOKEN>"
$server = "http://192.168.1.100:8420"

# Read evidence bundle
$bundle = Get-Content "exports/evidence_bundle_*.jsonl" -Raw

# Parse as array of envelopes
$envelopes = $bundle -split "`n" | Where-Object { $_ } | ForEach-Object { $_ | ConvertFrom-Json }

# Create request body
$body = @{ envelopes = $envelopes } | ConvertTo-Json -Depth 10

# Send to server
Invoke-RestMethod -Uri "$server/v1/ingest/evidence" `
    -Method POST `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body $body
```

### Using curl

```bash
# Export bundle to JSON array format first
curl -X POST "http://192.168.1.100:8420/v1/ingest/evidence" \
    -H "Authorization: Bearer <REDACTED_TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"envelopes": [...]}'
```

---

## API Reference

### POST /v1/ingest/evidence

**Request:**
```http
POST /v1/ingest/evidence HTTP/1.1
Host: 192.168.1.100:8420
Authorization: Bearer <token>
Content-Type: application/json

{
    "envelopes": [
        {
            "envelope_version": "v1",
            "node_id": "laptop-001",
            "seq": 0,
            "event_type": "SYSTEM_SNAPSHOT",
            "payload": {...},
            "payload_hash": "...",
            "prev_hash": null,
            "collector_version": "v1.7.0"
        }
    ]
}
```

**Response (Success):**
```json
{
    "success": true,
    "accepted_count": 5,
    "rejected_count": 0,
    "rejection_reasons": [],
    "message": "Ingested 5 envelope(s), rejected 0"
}
```

**Response (Auth Failure):**
```http
HTTP/1.1 401 Unauthorized
{"detail": "Authorization required"}
```

**Response (Invalid Token):**
```http
HTTP/1.1 403 Forbidden
{"detail": "Invalid token"}
```

---

## Audit Logging

All ingest attempts are logged to:
```
logs/ingest/audit.jsonl
```

**Audit Event Format:**
```json
{
    "received_at": "2026-01-10T12:00:00+00:00",
    "remote_addr": "192.168.1.50",
    "node_id": "laptop-001",
    "auth_status": "authenticated",
    "envelope_count_received": 10,
    "request_size_bytes": 5432,
    "accepted_count": 10,
    "rejected_count": 0,
    "last_seq_after": 42,
    "rejection_reasons": []
}
```

### View Audit Log

```powershell
Get-Content logs/ingest/audit.jsonl | ConvertFrom-Json | Format-Table
```

---

## Threat Model

### What This Protects Against

| Threat | Mitigation |
|--------|------------|
| **Unauthorized access** | Token required for all network requests |
| **Replay attacks** | Monotonic seq rejection per node |
| **Payload tampering** | SHA256 payload hash verification |
| **Chain tampering** | prev_hash chain verification |
| **DoS (large requests)** | Max bytes limit enforced |
| **DoS (many envelopes)** | Max envelope count enforced |
| **Rogue nodes** | Optional node ID allowlist |
| **Audit evasion** | All attempts logged (including failures) |

### What This Does NOT Protect Against

| Threat | Notes |
|--------|-------|
| **Token theft** | Protect token as a secret; rotate if compromised |
| **Network sniffing** | Use HTTPS/TLS in production (see below) |
| **Compromised client** | Token holder can push any valid envelope |
| **Physical access** | Out of scope for this layer |

### Recommended for Production

1. **Use HTTPS** - Deploy behind a reverse proxy (nginx, caddy) with TLS
2. **Firewall** - Restrict ingest port to known client IPs
3. **Token rotation** - Rotate tokens periodically
4. **Monitoring** - Alert on auth failures in audit log

---

## Verification Tests

### Test 1: Missing Token (Should Reject)

```powershell
Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"envelopes": []}'
```

Expected: `401 Unauthorized`

### Test 2: Wrong Token (Should Reject)

```powershell
Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
    -Method POST `
    -Headers @{ Authorization = "Bearer <INVALID_TOKEN_EXAMPLE>" } `
    -ContentType "application/json" `
    -Body '{"envelopes": []}'
```

Expected: `403 Forbidden`

### Test 3: Valid Token (Should Accept)

```powershell
$token = $env:CALYX_INGEST_TOKEN
Invoke-RestMethod -Uri "http://localhost:8420/v1/ingest/evidence" `
    -Method POST `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body '{"envelopes": []}'
```

Expected: `{"success": false, "message": "No envelopes to ingest", ...}`

---

## Quick Reference

| Action | Command/Location |
|--------|------------------|
| Set token | `$env:CALYX_INGEST_TOKEN = "..."` |
| Enable ingest | `$env:CALYX_INGEST_ENABLED = "true"` |
| Set allowlist | `$env:CALYX_ALLOWED_NODE_IDS = "node1,node2"` |
| View audit log | `logs/ingest/audit.jsonl` |
| Check nodes | `GET /v1/nodes` |

---

## Troubleshooting

### "Authorization required"
Token not provided. Add `Authorization: Bearer <token>` header.

### "Invalid token"
Token doesn't match `CALYX_INGEST_TOKEN`. Check spelling.

### "Ingest not configured for network access"
Server not bound to LAN IP or token not set. Localhost bypasses token check.

### "Node not in allowlist"
`CALYX_ALLOWED_NODE_IDS` is set and doesn't include the sender's node ID.

### "Request too large"
Request exceeds `CALYX_INGEST_MAX_BYTES`. Send smaller batches.

### "Too many envelopes"
Envelope count exceeds `CALYX_INGEST_MAX_ENVELOPES`. Send in batches.

---

*This is evidence transport only. No commands are executed. All operations are advisory-only.*
