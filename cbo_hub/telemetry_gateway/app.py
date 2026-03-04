"""
Station Calyx telemetry gateway — remote connection point for commands from another network.
- Auth via TELEMETRY_SECRET (required when set).
- Identity isolation: X-Telemetry-Client-ID required; session_id namespaced per client so contexts never mix.
- Audit logging: every /chat request logged (client_id, path, status, body_hash, timestamp); no PII in log.
Run: python -m cbo_hub.telemetry_gateway or uvicorn ... --host 0.0.0.0 --port 7781
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

CBO_CHAT = os.getenv("CBO_CHAT_URL", "http://127.0.0.1:7778/chat")
TELEMETRY_SECRET = (os.getenv("TELEMETRY_SECRET") or "").strip()

# Audit log: one JSON object per line (no PII). Dir created if missing.
_REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOG_DIR = Path(os.getenv("CALYX_REPO_ROOT", str(_REPO_ROOT))) / "cbo_hub" / "logs"
AUDIT_LOG_PATH = AUDIT_LOG_DIR / "telemetry_gateway_audit.jsonl"

# Client ID: alphanumeric, underscore, hyphen; max 128 chars (no mixing with other identities)
_CLIENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

app = FastAPI(title="Station Calyx Telemetry Gateway", version="0.1")


def _check_secret(x_telemetry_secret: str | None, authorization: str | None) -> None:
    if not TELEMETRY_SECRET:
        return
    secret = None
    if x_telemetry_secret and x_telemetry_secret.strip():
        secret = x_telemetry_secret.strip()
    if authorization and authorization.startswith("Bearer "):
        secret = authorization[7:].strip()
    if secret != TELEMETRY_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing telemetry secret.")


def _require_client_id(raw: str | None) -> str:
    """Require and validate X-Telemetry-Client-ID so identity never mixes across callers."""
    if not raw or not raw.strip():
        raise HTTPException(
            status_code=400,
            detail="X-Telemetry-Client-ID required. Use a stable id per client (e.g. jorge_laptop) so session context is isolated.",
        )
    cid = raw.strip()
    if not _CLIENT_ID_PATTERN.match(cid):
        raise HTTPException(
            status_code=400,
            detail="X-Telemetry-Client-ID must be 1–128 chars: letters, digits, underscore, hyphen only.",
        )
    return cid


def _namespace_session(client_id: str, session_id: str) -> str:
    """Namespace session_id so telemetry clients never share context with each other or local UI."""
    safe = (session_id or "default").strip() or "default"
    # Restrict to safe chars so we don't inject anything
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", safe)[:64]
    return f"tg_{client_id}_{safe}"


def _write_audit(entry: dict) -> None:
    """Append one JSON line to audit log (auditorial level; no PII in entry)."""
    try:
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # do not fail request on log write


@app.get("/health")
async def health():
    """200 if CBO Core is reachable (it only has POST /chat; any response means up)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://127.0.0.1:7778/")
        return {"status": "ok", "cbo_core_reachable": True}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"CBO Core unreachable: {e}")


@app.post("/chat")
async def chat(
    request: Request,
    x_telemetry_secret: str | None = Header(None, alias="X-Telemetry-Secret"),
    authorization: str | None = Header(None),
    x_telemetry_client_id: str | None = Header(None, alias="X-Telemetry-Client-ID"),
):
    """Proxy to CBO Core /chat. Same JSON body as CBO. Session is namespaced by X-Telemetry-Client-ID so identities never mix."""
    _check_secret(x_telemetry_secret, authorization)
    client_id = _require_client_id(x_telemetry_client_id)
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object.")

    # Namespace session_id so this client's context is isolated from others and from local Avatar Web
    original_session = body.get("session_id") or "home"
    body = {**body, "session_id": _namespace_session(client_id, original_session)}

    # Audit: timestamp, client_id, path, body_hash (no PII), forwarded_for
    body_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
    body_hash = hashlib.sha256(body_bytes).hexdigest()[:16]
    forwarded_for = request.headers.get("x-forwarded-for") or request.client.host if request.client else None
    audit_entry = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "client_id": client_id,
        "path": "/chat",
        "session_namespaced": body["session_id"],
        "body_sha256_16": body_hash,
        "forwarded_for": forwarded_for,
    }

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(CBO_CHAT, json=body)
            r.raise_for_status()
            out = r.json()
    except httpx.HTTPStatusError as e:
        audit_entry["status"] = e.response.status_code
        audit_entry["error_snippet"] = (e.response.text or "")[:200]
        _write_audit(audit_entry)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        audit_entry["status"] = 502
        audit_entry["error_snippet"] = str(e)[:200]
        _write_audit(audit_entry)
        raise HTTPException(status_code=502, detail=str(e))

    audit_entry["status"] = 200
    _write_audit(audit_entry)
    # Ensure gateway runs make it back to the home node: refresh STATE.md so hub has current validation
    _refresh_home_state_background()
    return out


def _refresh_home_state_background() -> None:
    """Fire-and-forget: run update_state_checks.ps1 on the home node so STATE reflects latest after this gateway run."""
    script = _REPO_ROOT / "Scripts" / "update_state_checks.ps1"
    if not script.exists():
        return
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=str(_REPO_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
