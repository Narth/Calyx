"""
Station Calyx telemetry gateway - remote connection point for commands from another network.
- Auth via TELEMETRY_SECRET (required when set).
- Identity isolation: X-Telemetry-Client-ID required; session_id namespaced per client so contexts never mix.
- Local audit path must be writable before governed ingress is allowed.
- Audit logging is append-only JSONL with explicit trust-state signaling.
Run: python -m cbo_hub.telemetry_gateway or uvicorn ... --host 0.0.0.0 --port 7781
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

from calyx.kernel.boot_context_budget import is_observe_mode_forced
from calyx.kernel.boot_evidence import assert_boot_evidence_or_fail
from calyx.kernel.event_ledger import clear_system_phase, set_system_phase

CBO_CHAT = os.getenv("CBO_CHAT_URL", "http://127.0.0.1:7778/chat")

# Boot Evidence Pre-Network Gate (V1): fail closed before network bind.
assert_boot_evidence_or_fail(
    component="telemetry",
    required_session_id=(os.environ.get("CALYX_BOOT_SESSION_ID") or None),
)


def _emit(event: str, msg: str, level: str = "INFO", data: dict | None = None) -> None:
    """Emit to Station Event Ledger. Never throws."""
    try:
        from calyx.kernel.event_ledger import emit as _le

        _le(level=level, component="telemetry", event=event, msg=msg, data=data or {})
    except Exception:
        pass


def _ts_utc() -> str:
    return datetime.now(UTC).isoformat()


TELEMETRY_SECRET = (os.getenv("TELEMETRY_SECRET") or "").strip()
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_FOR_RUNTIME = Path(os.getenv("CALYX_REPO_ROOT", str(_REPO_ROOT)))
_RUNTIME_DIR = Path(os.getenv("CALYX_RUNTIME_DIR", str(_ROOT_FOR_RUNTIME / "runtime")))

AUDIT_LOG_DIR = _ROOT_FOR_RUNTIME / "cbo_hub" / "logs"
AUDIT_LOG_PATH = AUDIT_LOG_DIR / "telemetry_gateway_audit.jsonl"
AUDIT_STATUS_PATH = _RUNTIME_DIR / "telemetry_gateway_audit_status.json"
SECURITY_RECEIPTS_DIR = _RUNTIME_DIR / "receipts" / "security"

_CLIENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
_AUDIT_WRITE_LOCK = threading.Lock()
_AUDIT_STATE_LOCK = threading.Lock()
_AUDIT_STATE: dict[str, Any] = {
    "schema": "telemetry_gateway.audit_status.v1",
    "ts_utc": "",
    "gateway_pid": os.getpid(),
    "trust_state": "untrusted",
    "startup_ready": False,
    "audit_log_path": str(AUDIT_LOG_PATH),
    "confirmation_boundary": "",
    "last_readiness_check_ts": "",
    "last_append_ok_ts": "",
    "last_append_error_ts": "",
    "last_error": "",
    "reason": "startup_pending",
    "last_failed_request_id": "",
}

app = FastAPI(title="Station Calyx Telemetry Gateway", version="0.2")

try:
    from calyx.kernel.ledger_middleware import LedgerCorrIdMiddleware

    app.add_middleware(LedgerCorrIdMiddleware, service_name="telemetry")
except Exception:
    pass


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _write_security_receipt(prefix: str, payload: dict[str, Any]) -> Path:
    SECURITY_RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    path = SECURITY_RECEIPTS_DIR / f"{prefix}__{tag}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _persist_audit_status(**updates: Any) -> dict[str, Any]:
    with _AUDIT_STATE_LOCK:
        _AUDIT_STATE.update(updates)
        _AUDIT_STATE["schema"] = "telemetry_gateway.audit_status.v1"
        _AUDIT_STATE["ts_utc"] = _ts_utc()
        _AUDIT_STATE["gateway_pid"] = os.getpid()
        _AUDIT_STATE["audit_log_path"] = str(AUDIT_LOG_PATH)
        snapshot = dict(_AUDIT_STATE)
        _write_json_atomic(AUDIT_STATUS_PATH, snapshot)
        return snapshot


def _current_trust_state() -> str:
    with _AUDIT_STATE_LOCK:
        return str(_AUDIT_STATE.get("trust_state") or "untrusted")


def _append_audit_entry(entry: dict[str, Any]) -> tuple[bool, str, str]:
    """
    Confirmation boundary:
    - success means the JSONL line was appended, flushed, and fsync'd when available
    - if fsync is unavailable, success falls back to append+flush and records that boundary explicitly
    """
    payload = json.dumps(entry, ensure_ascii=False) + "\n"
    boundary = "append+flush"
    try:
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _AUDIT_WRITE_LOCK:
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                    boundary = "append+flush+fsync"
                except (AttributeError, OSError):
                    boundary = "append+flush"
        return True, boundary, ""
    except Exception as exc:
        return False, "", str(exc)[:200]


def _mark_audit_untrusted(
    *,
    reason: str,
    phase: str,
    request_id: str = "",
    failure_class: str,
    error_snippet: str,
) -> Path:
    now = _ts_utc()
    status = _persist_audit_status(
        trust_state="untrusted",
        last_append_error_ts=now,
        last_error=error_snippet,
        reason=reason,
        last_failed_request_id=request_id,
    )
    receipt = {
        "schema": "telemetry_gateway.audit_failure.v1",
        "timestamp_utc": now,
        "phase": "runtime",
        "status": "failed",
        "receipt_type": "telemetry_gateway_audit_failure",
        "trust_state": status["trust_state"],
        "audit_log_path": str(AUDIT_LOG_PATH),
        "request_id": request_id,
        "failure_class": failure_class,
        "failure_phase": phase,
        "error_snippet": error_snippet,
        "confirmation_boundary": status.get("confirmation_boundary", ""),
    }
    receipt_path = _write_security_receipt("telemetry_gateway_audit_failure", receipt)
    _emit(
        "telemetry.audit.append.failed",
        "Telemetry audit append failed; ingress trust downgraded",
        level="ERROR",
        data={
            "request_id": request_id,
            "failure_class": failure_class,
            "failure_phase": phase,
            "receipt_path": str(receipt_path),
        },
    )
    return receipt_path


def _record_startup_readiness() -> None:
    readiness_id = f"startup-{uuid.uuid4()}"
    readiness_ts = _ts_utc()
    entry = {
        "ts_utc": readiness_ts,
        "request_id": readiness_id,
        "phase": "startup_readiness",
        "client_id": "telemetry_gateway",
        "path": "/chat",
        "audit_outcome": "readiness_confirmed",
        "body_sha256_16": "",
        "forwarded_for": "",
        "trust_state": "trusted",
    }
    ok, boundary, error = _append_audit_entry(entry)
    if not ok:
        status = _persist_audit_status(
            trust_state="untrusted",
            startup_ready=False,
            last_readiness_check_ts=readiness_ts,
            last_append_error_ts=readiness_ts,
            last_error=error,
            reason="startup_readiness_failed",
            confirmation_boundary="",
            last_failed_request_id=readiness_id,
        )
        receipt = {
            "schema": "telemetry_gateway.audit_readiness.v1",
            "timestamp_utc": readiness_ts,
            "phase": "startup",
            "status": "failed",
            "receipt_type": "telemetry_gateway_audit_readiness",
            "trust_state": status["trust_state"],
            "startup_ready": False,
            "audit_log_path": str(AUDIT_LOG_PATH),
            "request_id": readiness_id,
            "confirmation_boundary": "",
            "error_snippet": error,
        }
        receipt_path = _write_security_receipt("telemetry_gateway_audit_readiness", receipt)
        _emit(
            "governance.assertion.failed",
            "Telemetry audit readiness failed closed",
            level="ERROR",
            data={"receipt_path": str(receipt_path), "reason": "audit_path_unwritable"},
        )
        raise RuntimeError(f"telemetry_audit_untrusted: {error}")

    status = _persist_audit_status(
        trust_state="trusted",
        startup_ready=True,
        last_readiness_check_ts=readiness_ts,
        last_append_ok_ts=readiness_ts,
        last_error="",
        reason="startup_readiness_confirmed",
        confirmation_boundary=boundary,
        last_failed_request_id="",
    )
    receipt = {
        "schema": "telemetry_gateway.audit_readiness.v1",
        "timestamp_utc": readiness_ts,
        "phase": "startup",
        "status": "ok",
        "receipt_type": "telemetry_gateway_audit_readiness",
        "trust_state": status["trust_state"],
        "startup_ready": True,
        "audit_log_path": str(AUDIT_LOG_PATH),
        "request_id": readiness_id,
        "confirmation_boundary": boundary,
    }
    receipt_path = _write_security_receipt("telemetry_gateway_audit_readiness", receipt)
    _emit(
        "telemetry.audit.readiness.confirmed",
        "Telemetry audit path confirmed writable",
        data={"receipt_path": str(receipt_path), "confirmation_boundary": boundary},
    )


def _record_shutdown_status() -> None:
    shutdown_ts = _ts_utc()
    status = _persist_audit_status(
        trust_state="untrusted",
        reason="gateway_shutdown",
        last_error="",
    )
    receipt = {
        "schema": "telemetry_gateway.audit_shutdown.v1",
        "timestamp_utc": shutdown_ts,
        "phase": "shutdown",
        "status": "ok",
        "receipt_type": "telemetry_gateway_audit_shutdown",
        "trust_state": status["trust_state"],
        "audit_log_path": str(AUDIT_LOG_PATH),
    }
    receipt_path = _write_security_receipt("telemetry_gateway_audit_shutdown", receipt)
    _emit(
        "telemetry.audit.shutdown",
        "Telemetry gateway marked audit trust untrusted on shutdown",
        data={"receipt_path": str(receipt_path)},
    )


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
            detail="X-Telemetry-Client-ID must be 1-128 chars: letters, digits, underscore, hyphen only.",
        )
    return cid


def _namespace_session(client_id: str, session_id: str) -> str:
    """Namespace session_id so telemetry clients never share context with each other or local UI."""
    safe = (session_id or "default").strip() or "default"
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", safe)[:64]
    return f"tg_{client_id}_{safe}"


async def _forward_to_cbo(body: dict[str, Any], request_id: str) -> tuple[dict[str, Any], int]:
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(CBO_CHAT, json=body)
        response.raise_for_status()
        return response.json(), response.status_code


def _append_pre_forward_or_fail(entry: dict[str, Any], request_id: str) -> str:
    ok, boundary, error = _append_audit_entry(entry)
    if not ok:
        _mark_audit_untrusted(
            reason="pre_forward_append_failed",
            phase="pre_forward",
            request_id=request_id,
            failure_class="audit_append_pre_forward_failed",
            error_snippet=error,
        )
        raise HTTPException(
            status_code=503,
            detail="Telemetry ingress unavailable: local audit append could not be confirmed.",
        )

    _persist_audit_status(
        trust_state="trusted",
        last_append_ok_ts=entry["ts_utc"],
        last_error="",
        reason="append_confirmed",
        confirmation_boundary=boundary,
        last_failed_request_id="",
    )
    return boundary


def _append_post_forward_and_maybe_downgrade(entry: dict[str, Any], request_id: str) -> None:
    ok, boundary, error = _append_audit_entry(entry)
    if not ok:
        _mark_audit_untrusted(
            reason="post_forward_append_failed",
            phase="post_forward",
            request_id=request_id,
            failure_class="audit_append_post_forward_failed",
            error_snippet=error,
        )
        return

    _persist_audit_status(
        trust_state="trusted",
        last_append_ok_ts=entry["ts_utc"],
        last_error="",
        reason="append_confirmed",
        confirmation_boundary=boundary,
        last_failed_request_id="",
    )


@app.on_event("startup")
def _telemetry_startup() -> None:
    try:
        set_system_phase("boot")
        _emit("station.boot", "Telemetry Gateway started", data={})
        _emit(
            "station.service.identity",
            "Telemetry Gateway identity",
            data={
                "service": "telemetry_gateway",
                "pid": os.getpid(),
                "cwd": str(Path.cwd()),
            },
        )
        _emit(
            "audit.runtime.network.bind_override",
            "Telemetry Gateway binding to 0.0.0.0:7781 (explicit override per STATION_STACK_POLICY)",
            data={"host": "0.0.0.0", "port": 7781, "service": "telemetry_gateway"},
        )
        _record_startup_readiness()
    finally:
        clear_system_phase()


@app.on_event("shutdown")
def _telemetry_shutdown() -> None:
    _record_shutdown_status()


@app.get("/health")
async def health() -> dict[str, Any]:
    """200 if CBO Core is reachable (it only has POST /chat; any response means up)."""
    _emit("telemetry.health_check", "GET /health", level="DEBUG")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.get("http://127.0.0.1:7778/")
        return {
            "status": "ok",
            "cbo_core_reachable": True,
            "audit_trust_state": _current_trust_state(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"CBO Core unreachable: {exc}") from exc


@app.post("/chat")
async def chat(
    request: Request,
    x_telemetry_secret: str | None = Header(None, alias="X-Telemetry-Secret"),
    authorization: str | None = Header(None),
    x_telemetry_client_id: str | None = Header(None, alias="X-Telemetry-Client-ID"),
) -> Any:
    """Proxy to CBO Core /chat with fail-closed local audit confirmation."""
    if _current_trust_state() != "trusted":
        raise HTTPException(
            status_code=503,
            detail="Telemetry ingress unavailable: audit trust state is untrusted.",
        )

    forced, marker = is_observe_mode_forced()
    if forced:
        _emit(
            "governance.assertion.failed",
            "outbound_blocked_observe_mode",
            level="ERROR",
            data={
                "reason": "boot_context_budget_exceeded",
                "observe_mode_forced": True,
                "marker_reason": marker.get("reason", ""),
            },
        )
        raise HTTPException(status_code=503, detail="Observe mode forced: outbound blocked.")

    _check_secret(x_telemetry_secret, authorization)
    client_id = _require_client_id(x_telemetry_client_id)
    request_id = str(uuid.uuid4())
    _emit(
        "telemetry.chat_proxy",
        "POST /chat -> CBO Core",
        data={"client_id": client_id[:32], "request_id": request_id},
    )

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object.")

    original_session = body.get("session_id") or "home"
    body = {**body, "session_id": _namespace_session(client_id, original_session)}
    body_bytes = json.dumps(body, sort_keys=True).encode("utf-8")
    body_hash = hashlib.sha256(body_bytes).hexdigest()[:16]
    forwarded_for = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")

    pre_forward_ts = _ts_utc()
    pre_entry = {
        "ts_utc": pre_forward_ts,
        "request_id": request_id,
        "phase": "pre_forward",
        "client_id": client_id,
        "path": "/chat",
        "audit_outcome": "append_confirmed",
        "body_sha256_16": body_hash,
        "forwarded_for": forwarded_for,
        "session_namespaced": body["session_id"],
        "trust_state": "trusted",
    }
    boundary = _append_pre_forward_or_fail(pre_entry, request_id)
    pre_entry["confirmation_boundary"] = boundary

    post_ts = _ts_utc()
    try:
        out, downstream_status_code = await _forward_to_cbo(body, request_id)
        post_entry = {
            "ts_utc": post_ts,
            "request_id": request_id,
            "phase": "post_forward",
            "client_id": client_id,
            "path": "/chat",
            "audit_outcome": "downstream_completed",
            "body_sha256_16": body_hash,
            "forwarded_for": forwarded_for,
            "session_namespaced": body["session_id"],
            "trust_state": "trusted",
            "downstream_status_code": downstream_status_code,
        }
        _append_post_forward_and_maybe_downgrade(post_entry, request_id)
        _refresh_home_state_background()
        return out
    except httpx.HTTPStatusError as exc:
        post_entry = {
            "ts_utc": post_ts,
            "request_id": request_id,
            "phase": "post_forward",
            "client_id": client_id,
            "path": "/chat",
            "audit_outcome": "downstream_http_error",
            "body_sha256_16": body_hash,
            "forwarded_for": forwarded_for,
            "session_namespaced": body["session_id"],
            "trust_state": "trusted",
            "downstream_status_code": exc.response.status_code,
            "error_snippet": (exc.response.text or "")[:200],
        }
        _append_post_forward_and_maybe_downgrade(post_entry, request_id)
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except Exception as exc:
        post_entry = {
            "ts_utc": post_ts,
            "request_id": request_id,
            "phase": "post_forward",
            "client_id": client_id,
            "path": "/chat",
            "audit_outcome": "downstream_transport_error",
            "body_sha256_16": body_hash,
            "forwarded_for": forwarded_for,
            "session_namespaced": body["session_id"],
            "trust_state": "trusted",
            "downstream_status_code": 502,
            "error_snippet": str(exc)[:200],
        }
        _append_post_forward_and_maybe_downgrade(post_entry, request_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _refresh_home_state_background() -> None:
    """Fire-and-forget: refresh STATE.md after a successful gateway run on Windows."""
    if os.name != "nt":
        return
    script = _REPO_ROOT / "Scripts" / "update_state_checks.ps1"
    if not script.exists():
        return
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=str(_REPO_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
