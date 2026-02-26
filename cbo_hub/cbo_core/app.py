from __future__ import annotations

import json
import os
import time
import hashlib
import pathlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# WO_REQUEST_ORIENTATION_PROTOCOL_V1/V2
from calyx.kernel.intent_orientation import (
    classify_intent,
    extract_file_path_from_hit,
    parse_compound_targets,
)
# WO_CANONICAL_RESPONSE_HASH_V1
from calyx.kernel.canonical_bundle import evidence_file, evidence_repo_hit, evidence_state
import httpx
from dotenv import load_dotenv


def _resolve_repo_root() -> pathlib.Path:
    """Resolve repo root. CALYX_REPO_ROOT env overrides; else parents[2] from this file."""
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return pathlib.Path(env_root).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


REPO_ROOT = _resolve_repo_root()
RECEIPTS = REPO_ROOT / "cbo_hub" / "receipts" / "cbo_core.jsonl"

load_dotenv(dotenv_path=REPO_ROOT / ".env.cbo")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KIMI_API_KEY = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")

DEV_HARNESS_BASE = "http://127.0.0.1:7777"


def _emit(event: str, msg: str, level: str = "INFO", data: dict | None = None) -> None:
    """Emit to Station Event Ledger. Never throws."""
    try:
        from calyx.kernel.event_ledger import emit as ledger_emit
        ledger_emit(level=level, component="cbo", event=event, msg=msg, data=data or {})
    except Exception:
        pass


def _run_sunrise_preflight() -> None:
    """WO_VERIFIED_CLAIMS_LEDGER_V1: Verify required dirs exist; create if missing; abort on failure.
    WO_IDLE_ACTIVITY_GOVERNANCE_V3: Verify task budget path writable; emit station.config.effective.
    WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: Set system phase for preflight emits."""
    import sys
    try:
        from calyx.kernel.event_ledger import set_system_phase, clear_system_phase
        set_system_phase("preflight")
    except Exception:
        pass
    required = [
        REPO_ROOT / "runtime" / "ledger",
        REPO_ROOT / "runtime" / "receipts",
        REPO_ROOT / "runtime" / "receipts" / "canonical",
        REPO_ROOT / "runtime" / "receipts" / "security",  # WO_CALYX_SIGN_INGRESS_AUTH_V4: nonce ledger
        REPO_ROOT / "runtime" / "receipts" / "budget",  # WO_GOVERNANCE_BUDGET_ACCOUNTING_V1 + task budget
    ]
    for d in required:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[preflight] Failed to create {d}: {e}", file=sys.stderr)
            try:
                from calyx.kernel.event_ledger import emit as _le
                _le("ERROR", "cbo", "station.preflight.failed", f"Preflight: dir create failed: {d}", data={"path": str(d), "reason": str(e)[:200]})
            except Exception:
                pass
            sys.exit(1)
    for d in required:
        if not d.exists() or not d.is_dir():
            print(f"[preflight] Required dir missing: {d}", file=sys.stderr)
            try:
                from calyx.kernel.event_ledger import emit as _le
                _le("ERROR", "cbo", "station.preflight.failed", f"Preflight: dir missing after create: {d}", data={"path": str(d)})
            except Exception:
                pass
            sys.exit(1)
    # WO_IDLE_ACTIVITY_GOVERNANCE_V3: Task budget path must be writable
    budget_dir = REPO_ROOT / "runtime" / "receipts" / "budget"
    try:
        probe = budget_dir / ".preflight_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except Exception as e:
        print(f"[preflight] Task budget dir not writable: {budget_dir}: {e}", file=sys.stderr)
        try:
            from calyx.kernel.event_ledger import emit as _le
            _le("ERROR", "cbo", "station.preflight.failed", f"Preflight: task budget dir not writable: {budget_dir}", data={"path": str(budget_dir), "reason": str(e)[:200]})
        except Exception:
            pass
        sys.exit(1)
    # WO_IDLE_ACTIVITY_GOVERNANCE_V3: Emit station.config.effective
    try:
        _hb_enabled = os.environ.get("CALYX_HEARTBEAT_PUSH_ENABLED", "").strip().lower() not in ("false", "0", "no", "off")
        _hb_interval = os.environ.get("CALYX_HEARTBEAT_PUSH_INTERVAL_MIN") or os.environ.get("DISCORD_HEARTBEAT_INTERVAL_MIN", "30")
        _hb_dest = (os.environ.get("CALYX_HEARTBEAT_PUSH_DESTINATION") or "DM").strip().upper()
        if _hb_dest not in ("DM", "CHANNEL", "OFF"):
            _hb_dest = "DM"
        _emit("station.config.effective", "Effective config (WO_IDLE_ACTIVITY_GOVERNANCE_V3)", level="INFO", data={
            "CALYX_HEARTBEAT_PUSH_ENABLED": _hb_enabled,
            "CALYX_HEARTBEAT_PUSH_INTERVAL_MIN": _hb_interval,
            "CALYX_HEARTBEAT_PUSH_DESTINATION": _hb_dest,
        })
    except Exception:
        pass
    try:
        from calyx.kernel.event_ledger import clear_system_phase
        clear_system_phase()
    except Exception:
        pass
    # WO_OPENCLAW_DECOMMISSION_GATING_V2: External emitter gate (fail-closed if OpenClaw detected)
    try:
        from calyx.kernel.external_emitter_gate import check_external_emitter_gate
        gate_ok, gate_reason, gate_evidence = check_external_emitter_gate(REPO_ROOT)
        if not gate_ok:
            for ev in gate_evidence:
                _emit("audit.external.emitter.detected", "OpenClaw detected", level="WARN", data={
                    "emitter": "openclaw",
                    "evidence_type": ev.get("evidence_type", ""),
                    "evidence_value": str(ev.get("evidence_value", ""))[:200],
                    "pid": ev.get("pid"),
                    "path": str(ev.get("path", ""))[:200] if ev.get("path") else None,
                })
            _emit("audit.runtime.singularity.breach", "External emitter gate: OpenClaw detected", level="WARN", data={"evidence_count": len(gate_evidence)})
            _emit("governance.assertion.failed", "OpenClaw detected; fail-closed", level="WARN", data={"reason": "external_emitter_detected"})
            for err in gate_evidence[:5]:
                print(f"[preflight] OpenClaw detected: {err.get('evidence_type')} {err.get('evidence_value')}", file=sys.stderr)
            print("[preflight] Stop OpenClaw (services, tasks, processes) and restart. See docs/operations/OPENCLAW_DECOMMISSION_PLAYBOOK.md", file=sys.stderr)
            try:
                from calyx.kernel.event_ledger import emit as _le
                _le("ERROR", "cbo", "station.preflight.failed", "OpenClaw detected; fail-closed", data={"evidence_count": len(gate_evidence), "reason": gate_reason})
            except Exception:
                pass
            sys.exit(1)
    except ImportError:
        pass
    except Exception as e:
        print(f"[preflight] External emitter gate error: {e}", file=sys.stderr)

    # WO_DOC_HYGIENE_DEPRECATION_GATES_V1: Operational doc integrity
    try:
        from calyx.kernel.doc_status import validate_ops_docs
        doc_errors = validate_ops_docs(REPO_ROOT)
        if doc_errors:
            for err in doc_errors:
                print(f"[preflight] Doc integrity: {err}", file=sys.stderr)
            try:
                from calyx.kernel.event_ledger import emit as _le
                _le("ERROR", "cbo", "docs.integrity.failed", "Operational doc integrity failed", data={"offending_paths": doc_errors[:20]})
            except Exception:
                pass
            sys.exit(1)
    except Exception as e:
        print(f"[preflight] Doc integrity check failed: {e}", file=sys.stderr)
        try:
            from calyx.kernel.event_ledger import emit as _le
            _le("ERROR", "cbo", "docs.integrity.failed", f"Doc integrity check error: {e}", data={"error": str(e)[:200]})
        except Exception:
            pass
        sys.exit(1)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        _run_sunrise_preflight()
        try:
            from calyx.kernel.event_ledger import set_system_phase, clear_system_phase
            set_system_phase("boot")
        except Exception:
            pass
        _emit("station.boot", "CBO Core started successfully", level="INFO")
        try:
            from calyx.kernel.event_ledger import emit as _le, get_ledger_dir
            _le("INFO", "cbo", "station.service.identity", "CBO Core identity", data={
                "service": "cbo_core",
                "pid": os.getpid(),
                "cwd": str(pathlib.Path.cwd()),
                "ledger_dir": str(get_ledger_dir()),
            })
        except Exception:
            pass
        try:
            from calyx.kernel.event_ledger import clear_system_phase
            clear_system_phase()
        except Exception:
            pass
        yield
    except Exception as e:
        _emit("station.boot.error", f"Boot failed: {e}", level="ERROR", data={"error": str(e)[:200]})
        raise
    finally:
        pass


app = FastAPI(title="CBO Core", version="0.1", lifespan=_lifespan)

# WO_NERVOUS_SYSTEM_PHASE1: request-scoped corr_id + station.smoke at boundary
try:
    from calyx.kernel.ledger_middleware import LedgerCorrIdMiddleware
    app.add_middleware(LedgerCorrIdMiddleware, service_name="cbo")
except Exception:
    pass


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    """Emit unhandled exceptions to ledger. No silent failures."""
    try:
        import traceback
        from calyx.kernel.event_ledger import emit
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)[-3:])
        emit(
            level="ERROR",
            component="cbo",
            event="exception",
            msg=str(exc)[:200],
            data={"path": str(request.url.path), "stack": tb[-500:] if tb else ""},
        )
    except Exception:
        pass
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(status_code=500, content={"detail": str(exc)[:200]})


@app.get("/state")
def get_state():
    """Return STATE.md contents for OpenClaw bridge and other consumers. Read-only."""
    _emit("cbo.state.request", "GET /state", level="INFO")
    return {"state_md": _load_state_md()}


@app.get("/sponsorship")
def get_sponsorship():
    """Return sponsorship status for BloomOS and stamping gates. Per CALYX_SIGN_CBO_SPONSORSHIP."""
    _emit("cbo.sponsorship.request", "GET /sponsorship", level="INFO")
    try:
        from .stamping import check_sponsorship
        res = check_sponsorship(repo_root=REPO_ROOT, verify_signature=True)
        if res.valid:
            _emit("cbo.sponsorship.valid", f"Sponsorship valid: {res.proposal_id}", level="INFO", data={"proposal_id": res.proposal_id or ""})
        else:
            _emit("cbo.sponsorship.invalid", f"Sponsorship invalid: {res.reason}", level="WARN", data={"reason": res.reason or "", "proposal_id": res.proposal_id or ""})
        return {"valid": res.valid, "reason": res.reason, "proposal_id": res.proposal_id}
    except Exception as e:
        _emit("cbo.sponsorship.invalid", f"Sponsorship check error: {e}", level="WARN", data={"reason": str(e)[:100], "proposal_id": "cbo_sponsorship_research_test_improve"})
        return {"valid": False, "reason": f"check_error:{str(e)[:100]}", "proposal_id": "cbo_sponsorship_research_test_improve"}


class ExecuteReq(BaseModel):
    """Spine execution request: Mail -> Intent -> Work Envelope -> Contract Gate -> Execution."""
    task_type: str = Field(default="doc_update", description="CALYX_CONTRACT allowed_tasks")
    scope: Optional[dict] = Field(default=None, description="Scope paths; default {'paths': ['**']}")
    constraints: Optional[dict] = Field(default=None, description="Timeout etc; default 300s")
    intent_summary: str = Field(default="", description="Human-readable intent for artifact")


@app.post("/execute")
async def execute_spine(req: ExecuteReq):
    """
    Route execution through spine: Mail Envelope -> Intent Artifact -> Work Envelope -> Contract Gate -> Execution.
    For Avatar Web, OpenClaw bridge, and other CBO Core callers. Deny-by-default.
    """
    _emit("cbo.execute.request", f"POST /execute task_type={req.task_type}", level="INFO", data={"task_type": req.task_type})
    integrity_err = _check_integrity_gate()
    if integrity_err:
        _emit("cbo.execute.integrity_fail", f"Integrity gate blocked: {integrity_err}", level="WARN", data={"reason": integrity_err[:200]})
        raise HTTPException(status_code=503, detail=integrity_err)
    try:
        from calyx.kernel.paths import resolve_runtime_dir
        from calyx.mail.router import deliver_to_cbo_ingest
        from calyx.cbo.intent_pipeline import ingest_mail_envelope, mint_work_envelope, mark_ready
        from calyx.execution.hub_runner import process_work_outbox
    except ImportError as e:
        _emit("cbo.execute.spine.fail", f"Spine unavailable: {e}", level="ERROR", data={"error": str(e)[:200]})
        raise HTTPException(status_code=501, detail=f"spine_unavailable:{e}")

    runtime_dir = resolve_runtime_dir(REPO_ROOT)
    envelope_id = f"cbo_core_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).isoformat()
    envelope = {
        "envelope_id": envelope_id,
        "msg_id": envelope_id,
        "ts_utc": ts,
        "source": "cbo_core",
        "task_type": req.task_type,
        "scope": req.scope or {"paths": ["**"]},
        "constraints": req.constraints or {"timeout_seconds": 300},
        "intent": req.intent_summary or f"Spine execution: {req.task_type}",
    }
    try:
        mail_path = deliver_to_cbo_ingest(envelope, runtime_dir, replay_ledger=True)
        if mail_path is None:
            _emit("cbo.execute.spine.fail", "Deliver failed: integrity or replay", level="ERROR", data={"envelope_id": envelope_id})
            raise HTTPException(status_code=503, detail="deliver_failed_integrity_or_replay")
        intent_id = ingest_mail_envelope(mail_path, runtime_dir)
        if not intent_id:
            _emit("cbo.execute.spine.fail", "Ingest failed", level="ERROR", data={"envelope_id": envelope_id})
            raise HTTPException(status_code=500, detail="ingest_failed")
        mark_ready(intent_id, runtime_dir)
        we = mint_work_envelope(intent_id, runtime_dir, repo_root=REPO_ROOT)
        if not we:
            _emit("cbo.execute.spine.fail", "Mint failed", level="ERROR", data={"envelope_id": envelope_id, "intent_id": intent_id})
            raise HTTPException(status_code=500, detail="mint_failed")
        counts = process_work_outbox(repo_root=REPO_ROOT)
        _emit("cbo.execute.spine.success", f"Spine completed envelope_id={envelope_id}", level="INFO", data={"envelope_id": envelope_id, "intent_id": intent_id, "processed": counts.get("processed", 0), "denied": counts.get("denied", 0)})
        return {
            "envelope_id": envelope_id,
            "intent_id": intent_id,
            "processed": counts.get("processed", 0),
            "denied": counts.get("denied", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        _emit("cbo.execute.spine.fail", f"Spine error: {e}", level="ERROR", data={"envelope_id": envelope_id, "error": str(e)[:200]})
        raise


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parse_tool_requests(text: str) -> list[dict]:
    """Extract tool_requests from model text. Returns list of {tool, params}; empty on any error.
    FE-2026-02-26-1: Also extract JSON from mixed text (markdown code blocks, leading/trailing content)."""
    if not text or not text.strip():
        return []
    raw = text.strip()
    candidates = [raw]
    # Strip markdown code blocks
    for prefix, suffix in [("```json", "```"), ("```", "```")]:
        if prefix in raw and suffix in raw:
            start = raw.find(prefix) + len(prefix)
            end = raw.find(suffix, start)
            if end > start:
                candidates.append(raw[start:end].strip())
    # Last line (model sometimes outputs only JSON on final line)
    candidates.append(raw.split("\n")[-1].strip())
    # Find tool_requests and extract balanced JSON object (may have leading text)
    idx = raw.find("tool_requests")
    if idx >= 0:
        start = raw.rfind("{", 0, idx + 1)
        if start >= 0:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "{":
                    depth += 1
                elif raw[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidates.append(raw[start : i + 1])
                        break
    for candidate in candidates:
        if not candidate or not candidate.strip().startswith("{"):
            continue
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        reqs = obj.get("tool_requests")
        if not isinstance(reqs, list):
            continue
        out = []
        for r in reqs:
            if not isinstance(r, dict):
                continue
            tool = r.get("tool")
            if not isinstance(tool, str):
                continue
            params = r.get("params")
            if params is not None and not isinstance(params, dict):
                continue
            out.append({"tool": tool.strip().lower(), "params": params or {}})
        if out:
            return out
    return []


def _write_receipt(obj: dict) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# WO_VERIFIED_CLAIMS_LEDGER_V1: track first request for governance assertion
_first_canonical_claim_verified: bool = False


def _append_fe_candidate(claim_type: str, corr_id: str, reason: str, artifact_path: str | None = None) -> None:
    """WO_VERIFIED_CLAIMS_LEDGER_V1: Auto-append FE candidate on claim.failed. Never throws."""
    try:
        from datetime import datetime, timezone
        fe_path = REPO_ROOT / "docs" / "operations" / "FAILURE_EVENT_LOG.md"
        if not fe_path.exists():
            return
        content = fe_path.read_text(encoding="utf-8", errors="replace")
        # Next FE ID: find max N for today (FE-YYYY-MM-DD-N)
        import re
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prefix = f"FE-{today.replace('-', '-')}"
        matches = list(re.finditer(r"FE-(\d{4})-(\d{2})-(\d{2})-(\d+)", content))
        max_n = 0
        for m in matches:
            if m.group(0).startswith(prefix):
                max_n = max(max_n, int(m.group(4)))
        parts = today.split("-")
        fe_id = f"FE-{parts[0]}-{parts[1]}-{parts[2]}-{max_n + 1}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d ~%H:%M UTC")
        entry = f"""

---

## {fe_id}: [Auto] claim.failed — {claim_type}

| Field | Content |
|-------|---------|
| **ID** | {fe_id} |
| **Timestamp** | {ts} |
| **Component** | CBO Core (`cbo_hub/cbo_core/app.py`) |
| **Goal** | Emit and verify canonical_hash receipt |
| **End Result** | claim.failed |
| **Root Cause** | {reason[:500]} |
| **Rectification** | Investigate artifact_path, verify preflight dirs exist |
| **Status** | open |
| **Detection Signal** | claim_failed_{claim_type}, corr_id={corr_id[:16]} |
"""
        if artifact_path:
            entry = entry.replace("Investigate artifact_path", f"Artifact: {artifact_path[:200]}. Investigate")
        # Insert before Changelog if present, else append
        changelog = "## Changelog"
        if changelog in content:
            idx = content.find(changelog)
            content = content[:idx] + entry + "\n" + content[idx:]
        else:
            content = content.rstrip() + entry + "\n"
        fe_path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def _emit_canonical_hash(
    request: Request,
    intent: str,
    entry_point: str,
    normalized_request: str,
    reply: str,
    evidence: list[dict],
    fastpath_used: bool,
    governance_required: bool = True,
    tooling_allowed: bool = True,
    auth_verified: bool | None = None,
    signer_fingerprint: str | None = None,
) -> dict:
    """WO_CANONICAL_RESPONSE_HASH_V1 + WO_VERIFIED_CLAIMS_LEDGER_V1: Build bundle, emit claim lifecycle.
    Returns dict for WO_GOVERNANCE_BUDGET_ACCOUNTING_V1: claim_* counts, hashes, canonical path."""
    global _first_canonical_claim_verified
    from calyx.kernel.verified_claims import emit_claim_attempted, emit_claim_failed, emit_claim_verified
    from calyx.kernel.canonical_hash import sha256_hex

    result: dict = {
        "claim_attempted": 0,
        "claim_verified": 0,
        "claim_failed": 0,
        "response_sha256": "",
        "equivalence_hash_sha256": "",
        "canonical_receipt_path": "",
        "canonical_receipt_written": False,
        "equivalence_hash_emitted": False,
    }

    if auth_verified is None:
        auth_verified = getattr(request.state, "auth_verified", True)
    if signer_fingerprint is None:
        signer_fingerprint = getattr(request.state, "signer_fingerprint", "") or ""

    corr_id = getattr(request.state, "corr_id", None) or ""
    try:
        from calyx.kernel.event_ledger import get_corr_id
        corr_id = corr_id or get_corr_id() or ""
    except Exception:
        pass

    result["claim_attempted"] += 1
    emit_claim_attempted("canonical_hash", corr_id=corr_id or None)

    try:
        from calyx.kernel.canonical_bundle import build_canonical_bundle
        node_id = os.getenv("CALYX_NODE_ID", "unknown")
        bundle = build_canonical_bundle(
            ts_utc=_now_iso(),
            corr_id=corr_id,
            request_id=corr_id,
            entry_point=entry_point,
            node_id=node_id,
            intent=intent,
            normalized_request=normalized_request,
            evidence=evidence,
            policy_flags={
                "governance_required": governance_required,
                "canonical_response_mode": True,
                "fastpath_used": fastpath_used,
                "tooling_allowed": tooling_allowed,
            },
            response_text=reply,
            repo_root=REPO_ROOT,
        )
        _emit(
            "response.canonical_hash",
            "Canonical response hash (receipt)",
            level="INFO",
            data={
                "receipt_hash": bundle["canonical_hash_sha256"],
                "canonical_hash_sha256": bundle["canonical_hash_sha256"],  # legacy
                "normalized_request_sha256": bundle["normalized_request_sha256"],
                "intent": intent,
                "entry_point": entry_point,
                "fastpath_used": fastpath_used,
                "evidence_count": len(evidence),
                "response_sha256": bundle["response_sha256"],
            },
        )
        # WO_CANONICAL_EQUIVALENCE_HASH_V2 + WO_CALYX_SIGN_INGRESS_AUTH_V4: parity uses auth_verified
        # (governed-by-gateway and governed-by-signature must produce identical equivalence_hash)
        from calyx.kernel.canonical_bundle import build_equivalence_bundle
        equiv_bundle = build_equivalence_bundle(
            intent=intent,
            normalized_request_sha256=bundle["normalized_request_sha256"],
            evidence=evidence,
            policy_flags={"governance_required": auth_verified, "canonical_response_mode": True, "fastpath_used": fastpath_used, "tooling_allowed": tooling_allowed},
            response_sha256=bundle["response_sha256"],
            node_id=node_id,
            auth_verified=auth_verified,
            signer_fingerprint=signer_fingerprint,
        )
        result["claim_attempted"] += 1
        result["response_sha256"] = bundle["response_sha256"]
        result["equivalence_hash_sha256"] = equiv_bundle["equivalence_hash_sha256"]
        result["equivalence_hash_emitted"] = True
        emit_claim_attempted("equivalence_hash", corr_id=corr_id or None)
        _emit(
            "response.equivalence_hash",
            "Equivalence hash (parity)",
            level="INFO",
            data={
                "equivalence_hash_sha256": equiv_bundle["equivalence_hash_sha256"],
                "normalized_request_sha256": bundle["normalized_request_sha256"],
                "intent": intent,
                "entry_point": entry_point,
                "fastpath_used": fastpath_used,
                "evidence_count": len(evidence),
                "response_sha256": bundle["response_sha256"],
            },
        )
        emit_claim_verified("equivalence_hash", sha256=equiv_bundle["equivalence_hash_sha256"], corr_id=corr_id or None)
        bundle["equivalence_hash_sha256"] = equiv_bundle["equivalence_hash_sha256"]

        # Receipt file: create dir, write (bundle includes both hashes), verify, then claim.verified
        canonical_dir = REPO_ROOT / "runtime" / "receipts" / "canonical"
        canonical_dir.mkdir(parents=True, exist_ok=True)
        if not canonical_dir.exists() or not canonical_dir.is_dir():
            reason = f"Directory not created: {canonical_dir}"
            result["claim_failed"] += 1
            emit_claim_failed("canonical_hash", reason, artifact_path=str(canonical_dir), corr_id=corr_id or None)
            _append_fe_candidate("canonical_hash", corr_id, reason, str(canonical_dir))
            if not _first_canonical_claim_verified:
                _first_canonical_claim_verified = True
                _emit("governance.assertion.failed", "First request: canonical_hash claim.failed", level="WARN", data={"claim_type": "canonical_hash", "corr_id": corr_id})
            return result

        ts_safe = _now_iso().replace(":", "-").replace(" ", "_")[:19]
        bundle_path = canonical_dir / f"canonical_bundle__{ts_safe}_{corr_id[:8] if corr_id else 'none'}.json"
        bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

        if not bundle_path.exists():
            reason = f"Receipt file not created: {bundle_path}"
            result["claim_failed"] += 1
            emit_claim_failed("canonical_hash", reason, artifact_path=str(bundle_path), corr_id=corr_id or None)
            _append_fe_candidate("canonical_hash", corr_id, reason, str(bundle_path))
            if not _first_canonical_claim_verified:
                _first_canonical_claim_verified = True
                _emit("governance.assertion.failed", "First request: canonical_hash claim.failed", level="WARN", data={"claim_type": "canonical_hash", "corr_id": corr_id})
            return result

        size = bundle_path.stat().st_size
        if size <= 0:
            reason = f"Receipt file empty: {bundle_path}"
            result["claim_failed"] += 1
            emit_claim_failed("canonical_hash", reason, artifact_path=str(bundle_path), corr_id=corr_id or None)
            _append_fe_candidate("canonical_hash", corr_id, reason, str(bundle_path))
            if not _first_canonical_claim_verified:
                _first_canonical_claim_verified = True
                _emit("governance.assertion.failed", "First request: canonical_hash claim.failed", level="WARN", data={"claim_type": "canonical_hash", "corr_id": corr_id})
            return result

        file_sha = sha256_hex(bundle_path.read_bytes())
        result["claim_verified"] += 2  # canonical_hash + equivalence_hash (already emitted)
        result["canonical_receipt_path"] = str(bundle_path)
        result["canonical_receipt_written"] = True
        emit_claim_verified("canonical_hash", artifact_path=str(bundle_path), sha256=file_sha, corr_id=corr_id or None)
        _first_canonical_claim_verified = True
        return result

    except Exception as e:
        reason = str(e)[:500]
        result["claim_failed"] += 1
        result["response_sha256"] = sha256_hex(reply) if reply else ""
        emit_claim_failed("canonical_hash", reason, corr_id=corr_id or None)
        _append_fe_candidate("canonical_hash", corr_id, reason)
        _emit("response.canonical_hash.failed", reason[:200], level="WARN", data={"intent": intent})
        if not _first_canonical_claim_verified:
            _first_canonical_claim_verified = True
            _emit("governance.assertion.failed", "First request: canonical_hash claim.failed", level="WARN", data={"claim_type": "canonical_hash", "corr_id": corr_id})
        return result


def _write_governance_budget(
    request: Request,
    receipt: dict,
    crh_result: dict,
    entry_point: str,
    intent: str,
    fastpath_used: bool,
    _start: float,
    reply: str = "",
) -> bool:
    """WO_GOVERNANCE_BUDGET_ACCOUNTING_V1/V2: Write one budget record at response.finalized.
    Returns True if written, False if failed. On failure emits governance.assertion.failed (budget_missing)."""
    try:
        from calyx.kernel.governance_budget import (
            _auth_mode_from_signer,
            _tool_calls_from_executed,
            write_budget_record,
        )
        corr_id = getattr(request.state, "corr_id", None) or ""
        try:
            from calyx.kernel.event_ledger import get_corr_id
            corr_id = corr_id or get_corr_id() or ""
        except Exception:
            pass
        signer_fp = getattr(request.state, "signer_fingerprint", "") or ""
        auth_verified = getattr(request.state, "auth_verified", True)
        executed = receipt.get("executed_tools") or []
        tool_calls = _tool_calls_from_executed(executed)
        wall_ms = receipt.get("request_latency_ms") or round((time.perf_counter() - _start) * 1000)
        path = write_budget_record(
            ts_utc=receipt.get("ts_utc", _now_iso()),
            corr_id=corr_id,
            request_id=corr_id,
            entry_point=entry_point,
            node_id=os.getenv("CALYX_NODE_ID", "unknown"),
            auth_mode=_auth_mode_from_signer(signer_fp),
            auth_verified=auth_verified,
            signer_fingerprint=signer_fp,
            intent=intent,
            fastpath_used=fastpath_used,
            wall_time_ms=wall_ms,
            tool_calls=tool_calls,
            tool_calls_total=sum(t.get("count", 1) for t in tool_calls),
            claims_attempted=crh_result.get("claim_attempted", 0),
            claims_verified=crh_result.get("claim_verified", 0),
            claims_failed=crh_result.get("claim_failed", 0),
            canonical_receipt_written=crh_result.get("canonical_receipt_written", False),
            canonical_receipt_path=crh_result.get("canonical_receipt_path", ""),
            equivalence_hash_emitted=crh_result.get("equivalence_hash_emitted", False),
            response_sha256=crh_result.get("response_sha256", "") or _sha256_text(reply or ""),
            equivalence_hash_sha256=crh_result.get("equivalence_hash_sha256", ""),
            receipt_hash_sha256=receipt.get("receipt_sha256", ""),
            _emit=_emit,
            _append_fe=_append_fe_candidate,
        )
        return path is not None
    except Exception as e:
        try:
            cid = getattr(request.state, "corr_id", None) or ""
            if not cid:
                try:
                    from calyx.kernel.event_ledger import get_corr_id
                    cid = get_corr_id() or ""
                except Exception:
                    pass
            _emit("governance.assertion.failed", "Budget record missing (exception)", level="WARN", data={"claim_type": "budget_missing", "corr_id": cid, "reason": str(e)[:200]})
            _append_fe_candidate("budget_missing", cid or "unknown", str(e)[:500], None)
        except Exception:
            pass
        return False


def _get_rate_per_million(provider: str, kind: str) -> Optional[float]:
    """Read optional $/million-tokens rate from env. kind is 'input' or 'output'. Returns None if unset."""
    key = f"{provider.upper()}_{kind.upper()}_PER_MILLION"
    val = os.getenv(key)
    if val is None or val.strip() == "":
        return None
    try:
        return float(val.strip())
    except ValueError:
        return None


def _estimate_cost_usd(provider: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """
    Estimate cost in USD from token counts using env-configured rates ($ per million tokens).
    Env: ANTHROPIC_INPUT_PER_MILLION, ANTHROPIC_OUTPUT_PER_MILLION, etc. Local always 0.
    Returns None if rates not configured for this provider.
    """
    if provider == "local":
        return 0.0
    r_in = _get_rate_per_million(provider, "input")
    r_out = _get_rate_per_million(provider, "output")
    if r_in is None and r_out is None:
        return None
    cost = 0.0
    if r_in is not None and input_tokens:
        cost += (input_tokens / 1_000_000.0) * r_in
    if r_out is not None and output_tokens:
        cost += (output_tokens / 1_000_000.0) * r_out
    return round(cost, 6)


def _normalize_usage(provider: str, raw: dict) -> dict:
    """Build a normalized usage entry for receipts: input_tokens, output_tokens, total_tokens (optional), latency_ms (optional)."""
    out: dict = {}
    if not raw:
        return out
    # Anthropic: input_tokens, output_tokens
    if provider == "anthropic":
        if "input_tokens" in raw:
            out["input_tokens"] = int(raw["input_tokens"])
        if "output_tokens" in raw:
            out["output_tokens"] = int(raw["output_tokens"])
        if out and "total_tokens" not in out:
            out["total_tokens"] = out.get("input_tokens", 0) + out.get("output_tokens", 0)
    # OpenAI / Kimi (OpenAI-compatible): prompt_tokens, completion_tokens, total_tokens
    elif provider in ("openai", "kimi"):
        if "prompt_tokens" in raw:
            out["input_tokens"] = int(raw["prompt_tokens"])
        if "completion_tokens" in raw:
            out["output_tokens"] = int(raw["completion_tokens"])
        if "total_tokens" in raw:
            out["total_tokens"] = int(raw["total_tokens"])
        elif out:
            out["total_tokens"] = out.get("input_tokens", 0) + out.get("output_tokens", 0)
    # Local (Ollama): prompt_eval_count, eval_count, eval_duration (ns)
    elif provider == "local":
        if "prompt_eval_count" in raw:
            out["input_tokens"] = int(raw["prompt_eval_count"])
        if "eval_count" in raw:
            out["output_tokens"] = int(raw["eval_count"])
        if out and "total_tokens" not in out:
            out["total_tokens"] = out.get("input_tokens", 0) + out.get("output_tokens", 0)
        if "eval_duration" in raw:
            out["eval_duration_ns"] = int(raw["eval_duration"])
            out["latency_ms"] = round(int(raw["eval_duration"]) / 1_000_000)
    return out


# WO_DOC_HYGIENE_DEPRECATION_GATES_V2/V3: Envelope primary; legacy token optional
_OVERRIDE_TOKEN = "include_deprecated_docs=true"


def _get_doc_override(req: Any, request: Request | None) -> tuple[bool, str | None]:
    """
    WO_GOVERNANCE_SINGULARITY_V3: Envelope doc_policy primary; legacy token optional.
    Returns (override, source). Cached per request in request.state.doc_override_result.
    """
    try:
        cached = getattr(getattr(request, "state", None), "doc_override_result", None)
        if cached is not None:
            return cached
    except Exception:
        pass

    result: tuple[bool, str | None] = (False, None)

    # 1. Envelope override (signed doc_policy)
    override_obj = getattr(getattr(request, "state", None), "doc_override", None) if request else None
    if isinstance(override_obj, dict) and override_obj.get("source") == "envelope":
        try:
            from calyx.kernel.event_ledger import get_corr_id
            _emit("audit.doc.override.requested", "Envelope doc_policy override", level="INFO", data={
                "source": "envelope",
                "envelope_id": override_obj.get("envelope_nonce", ""),
                "corr_id": get_corr_id() or "",
                "scope": override_obj.get("scope", "repo_search_only"),
                "reason": (override_obj.get("reason") or "")[:200],
            })
        except Exception:
            pass
        result = True, "envelope"
    else:
        # 2. Legacy token (migration window)
        user_text = getattr(req, "user_text", None) if req else None
        if user_text and _OVERRIDE_TOKEN in user_text.strip().lower():
            strict = os.environ.get("DOC_OVERRIDE_STRICT_MODE", "").strip().lower() in ("true", "1", "yes")
            if strict:
                _emit("governance.assertion.failed", "Legacy token override rejected (strict mode)", level="WARN", data={"reason": "DOC_OVERRIDE_STRICT_MODE"})
                _emit("audit.doc.override.rejected_legacy", "Legacy token rejected", level="WARN", data={"scope": "repo_search_only"})
                result = False, None
            else:
                _emit("audit.doc.override.legacy_token_used", "Legacy token override (migration)", level="WARN", data={"scope": "repo_search_only"})
                _emit("governance.assertion.degraded", "Legacy token used for doc override", level="WARN", data={"reason": "legacy_token"})
                _emit("audit.doc.override.requested", "Legacy token override", level="INFO", data={"source": "legacy_token", "scope": "repo_search_only"})
                result = True, "legacy_token"

    try:
        if request and hasattr(request, "state"):
            request.state.doc_override_result = result
    except Exception:
        pass
    return result


async def _call_dev_harness(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{DEV_HARNESS_BASE}{path}", json=payload)
        if r.status_code >= 400:
            raise HTTPException(r.status_code, f"Dev harness error: {r.text}")
        return r.json()


async def _call_anthropic(prompt: str, max_output_tokens: int = 800) -> tuple[str, dict]:
    """Returns (response_text, info_dict). info_dict has provider, model_id, usage (normalized)."""
    if not ANTHROPIC_API_KEY:
        return "[anthropic] ANTHROPIC_API_KEY missing.", {"provider": "anthropic", "model_id": None, "usage": None}
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_output_tokens,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        if r.status_code >= 400:
            return f"[anthropic] error {r.status_code}: {r.text[:500]}", {"provider": "anthropic", "model_id": model, "usage": None}
        data = r.json()
    parts = []
    for item in data.get("content", []):
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
    text = "".join(parts).strip()
    usage = _normalize_usage("anthropic", data.get("usage") or {})
    return text, {"provider": "anthropic", "model_id": model, "usage": usage if usage else None}


async def _call_openai(prompt: str, max_output_tokens: int = 800) -> tuple[str, dict]:
    """Returns (response_text, info_dict). info_dict has provider, model_id, usage (normalized if present)."""
    if not OPENAI_API_KEY:
        return "[openai] OPENAI_API_KEY missing.", {"provider": "openai", "model_id": None, "usage": None}

    model = os.getenv("OPENAI_MODEL", "gpt-5.1")  # adjust if your account uses a different id
    headers = {
        "authorization": f"Bearer {OPENAI_API_KEY}",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
        if r.status_code >= 400:
            return f"[openai] error {r.status_code}: {r.text[:500]}", {"provider": "openai", "model_id": model, "usage": None}
        data = r.json()
    out = []
    for item in data.get("output", []):
        for c in item.get("content", []):
            if c.get("type") == "output_text":
                out.append(c.get("text", ""))
    text = "".join(out).strip()
    # Responses API may expose usage at top level or under usage
    raw_usage = data.get("usage") or data.get("output_usage") or {}
    usage = _normalize_usage("openai", raw_usage)
    return text, {"provider": "openai", "model_id": model, "usage": usage if usage else None}


# Optional STATE.md cache to reduce disk I/O and CPU during heavy use (env: CBO_STATE_CACHE_SEC, 0=off)
_state_cache: tuple[str, float] = ("", 0.0)


def _extract_failure_event_format(fe_log: str) -> str:
    """WO_REQUEST_ORIENTATION_PROTOCOL_V2: Extract Event Log Format from FAILURE_EVENT_LOG.md."""
    if not fe_log or "Event Log Format" not in fe_log:
        return ""
    lines = fe_log.splitlines()
    out: list[str] = ["A Failure Event to Station Calyx uses the following format:\n"]
    in_table = False
    for line in lines:
        if "## Event Log Format" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("##") and "Event Log Format" not in line:
                break
            if "|" in line and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2 and parts[0].lower() != "field":
                    field = parts[0].replace("**", "").strip()
                    out.append(f"- **{field}**: {parts[1]}")
    return "\n".join(out) if len(out) > 1 else ""


def _load_failure_event_log() -> str:
    """Read docs/operations/FAILURE_EVENT_LOG.md. Read-only. WO_DOC_HYGIENE: emit audit.doc.read."""
    p = REPO_ROOT / "docs" / "operations" / "FAILURE_EVENT_LOG.md"
    if not p.exists() or not p.is_file():
        return ""
    try:
        content = p.read_text(encoding="utf-8", errors="replace").strip()
        try:
            from calyx.kernel.doc_status import get_doc_status
            st = get_doc_status(p, REPO_ROOT)
            _emit("audit.doc.read", "Doc read as evidence", level="DEBUG", data={"path": str(p.relative_to(REPO_ROOT)), "doc_status": st.get("status") or "unknown", "sha256": st.get("sha256", "")[:16], "override_deprecated": False, "override_source": None})
        except Exception:
            pass
        return content
    except Exception:
        return ""


def _extract_heartbeat_from_state(state_md: str) -> dict:
    """WO_REQUEST_ORIENTATION_PROTOCOL_V1: Extract heartbeat_ts, health, checks from STATE.md."""
    out: dict = {}
    for line in (state_md or "").splitlines():
        line = line.strip()
        if line.startswith("heartbeat_ts:"):
            out["heartbeat_ts"] = line.split(":", 1)[1].strip()
        elif line.startswith("health:"):
            out["health"] = line.split(":", 1)[1].strip()
        elif line.startswith("checks:"):
            out["checks"] = line.split(":", 1)[1].strip()
    return out


def _load_state_md() -> str:
    """Read STATE.md from repo root for context injection. Read-only. Uses short TTL cache if CBO_STATE_CACHE_SEC > 0."""
    global _state_cache
    cache_sec = 0
    try:
        cache_sec = int(os.getenv("CBO_STATE_CACHE_SEC", "30").strip() or "0")
    except ValueError:
        pass
    if cache_sec > 0:
        now = time.perf_counter()
        if _state_cache[0] and (now - _state_cache[1]) < cache_sec:
            return _state_cache[0]
    p = REPO_ROOT / "STATE.md"
    if not p.exists() or not p.is_file():
        return ""
    try:
        text = p.read_text(encoding="utf-8", errors="replace").strip()
        if cache_sec > 0:
            _state_cache = (text, time.perf_counter())
        return text
    except Exception:
        return ""


async def _call_kimi(prompt: str, max_output_tokens: int = 800) -> tuple[str, dict]:
    """Call Kimi (Moonshot) OpenAI-compatible API. Returns (response_text, receipt_info). No 500; errors as readable strings."""
    base_url = (os.getenv("KIMI_BASE_URL") or "https://api.moonshot.ai/v1").strip().rstrip("/")
    model_id = (os.getenv("KIMI_MODEL_ID") or os.getenv("KIMI_MODEL") or "").strip()
    api_key = KIMI_API_KEY
    receipt_info: dict = {
        "provider": "kimi",
        "base_url": base_url,
        "model_id": model_id or None,
        "http_status": None,
        "error_snippet": None,
        "request_id": None,
        "called": True,
    }
    if not api_key:
        receipt_info["called"] = False
        receipt_info["error_snippet"] = "KIMI_API_KEY or MOONSHOT_API_KEY not set."
        return "[kimi] KIMI_API_KEY (or MOONSHOT_API_KEY) missing.", receipt_info
    if not model_id:
        receipt_info["called"] = False
        receipt_info["error_snippet"] = "Set KIMI_MODEL_ID or KIMI_MODEL in env (e.g. kimi-k2.5)."
        return "[kimi] KIMI_MODEL_ID (or KIMI_MODEL) not set. Set it in env (e.g. KIMI_MODEL=kimi-k2.5).", receipt_info

    url = f"{base_url}/chat/completions"
    headers = {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_output_tokens,
        "temperature": 1,  # Kimi K2.5 only allows temperature=1
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            receipt_info["http_status"] = r.status_code
            if r.headers.get("x-request-id"):
                receipt_info["request_id"] = (r.headers.get("x-request-id") or "")[:200]
            if r.status_code >= 400:
                err_snippet = (r.text or "")[:500]
                receipt_info["error_snippet"] = err_snippet
                return f"[kimi] error {r.status_code}: {err_snippet}", receipt_info
            try:
                data = r.json()
            except Exception:
                receipt_info["error_snippet"] = "Response was not valid JSON."
                return "[kimi] Response was not valid JSON.", receipt_info
            choices = data.get("choices") if isinstance(data, dict) else None
            if not isinstance(choices, list) or not choices:
                receipt_info["error_snippet"] = "Unexpected response schema (no choices)."
                return "[kimi] Unexpected response schema (no choices).", receipt_info
            msg = choices[0].get("message") if isinstance(choices[0], dict) else {}
            text = (msg.get("content") or "").strip() if isinstance(msg, dict) else ""
            if data.get("id"):
                receipt_info["request_id"] = str(data.get("id"))[:200]
            raw_usage = data.get("usage") or {}
            usage = _normalize_usage("kimi", raw_usage)
            receipt_info["usage"] = usage if usage else None
            return text, receipt_info
    except Exception as e:
        receipt_info["error_snippet"] = str(e)[:500]
        return f"[kimi] request failed: {str(e)[:500]}", receipt_info


async def _call_local(prompt: str, max_output_tokens: int = 800) -> tuple[str, dict]:
    """Call local LLM (Ollama /api/generate). Returns (response_text, receipt_info). No 500; errors as readable strings."""
    base_url = (os.getenv("LOCAL_LLM_BASE_URL") or "http://127.0.0.1:11434").strip().rstrip("/")
    model_id = (os.getenv("LOCAL_LLM_MODEL_ID") or "").strip()
    receipt_info: dict = {
        "provider": "local",
        "base_url": base_url,
        "model_id": model_id or None,
        "http_status": None,
        "error_snippet": None,
        "request_id": None,
        "called": True,
    }
    if not model_id:
        receipt_info["called"] = False
        receipt_info["error_snippet"] = "Set LOCAL_LLM_MODEL_ID in env (e.g. llama3.2, qwen2.5-coder:7b)."
        return "[local] LOCAL_LLM_MODEL_ID not set. Set it in env (e.g. LOCAL_LLM_MODEL_ID=llama3.2).", receipt_info

    url = f"{base_url}/api/generate"
    payload = {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_output_tokens},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload)
            receipt_info["http_status"] = r.status_code
            if r.status_code >= 400:
                err_snippet = (r.text or "")[:500]
                receipt_info["error_snippet"] = err_snippet
                return f"[local] error {r.status_code}: {err_snippet}", receipt_info
            try:
                data = r.json()
            except Exception:
                receipt_info["error_snippet"] = "Response was not valid JSON."
                return "[local] Response was not valid JSON.", receipt_info
            if not isinstance(data, dict):
                receipt_info["error_snippet"] = "Unexpected response schema."
                return "[local] Unexpected response schema.", receipt_info
            text = (data.get("response") or "").strip()
            raw_usage = {k: data[k] for k in ("prompt_eval_count", "eval_count", "eval_duration") if k in data}
            usage = _normalize_usage("local", raw_usage)
            receipt_info["usage"] = usage if usage else None
            return text, receipt_info
    except Exception as e:
        receipt_info["error_snippet"] = str(e)[:500]
        return f"[local] request failed: {str(e)[:500]}", receipt_info


# ---------- API models ----------

class ChatReq(BaseModel):
    user_text: str = Field(..., min_length=1)
    session_id: str = Field(default="home")
    mode: str = Field(default="dev")  # dev | safe | observe
    allow_tools: bool = Field(default=True)
    model_role: str = Field(default="none")  # none | architect | workhorse | second | second_opinion | local
    allow_second_opinion: bool = Field(default=False)  # when true, second_opinion role may call Kimi (no silent spend)


class ChatResp(BaseModel):
    session_id: str
    reply_text: str
    receipt_sha256: str
    second_opinion_text: Optional[str] = None


# ---------- CBO behavior (stub v0) ----------
# This version proves:
# 1) CBO can talk
# 2) CBO can invoke dev harness tools in a controlled way
# Next phase replaces the scripted logic with LLM + tool-loop.

def _check_integrity_gate() -> Optional[str]:
    """Run spine integrity gate before chat. Returns None if pass, else error message."""
    try:
        from calyx.kernel.integrity_gate import gate_before_action
        from calyx.kernel.paths import resolve_repo_root, resolve_runtime_dir
        gate_before_action(
            runtime_dir=resolve_runtime_dir(REPO_ROOT),
            repo_root=REPO_ROOT,
            include_execution_path=False,
        )
        return None
    except ImportError:
        return None  # calyx not available; skip gate
    except Exception as e:
        failures = getattr(e, "failures", None)
        err = "; ".join(f"{f.component}:{f.reason}" for f in failures) if failures else str(e)
        return f"integrity_gate_failed:{err}"


# WO_EQUIVALENCE_SCOPE_V3: trusted gateways (governance attestation)
_TRUSTED_GOVERNANCE_SOURCES = frozenset({"openclaw", "calyx-discord-gateway", "openclaw_bridge"})


def _is_governed_channel(request: Request, req: ChatReq) -> tuple[bool, str]:
    """WO_OPENCLAW_UNIFIED_EXECUTOR: Detect OpenClaw or governed gateway traffic."""
    h = (request.headers.get("X-Calyx-Source") or "").strip().lower()
    if h in _TRUSTED_GOVERNANCE_SOURCES:
        return True, h or "openclaw"
    if "openclaw" in (req.session_id or "").lower():
        return True, "openclaw"
    return False, ""


def _governance_required_system() -> bool:
    """WO_EQUIVALENCE_SCOPE_V3: System config for governance. Env CALYX_GOVERNANCE_REQUIRED (default false for backward compat; set true to enforce)."""
    v = os.environ.get("CALYX_GOVERNANCE_REQUIRED", "false").strip().lower()
    return v in ("true", "1", "yes")


def _check_governance_auth(request: Request, req: ChatReq) -> tuple[bool, str, bool]:
    """
    WO_EQUIVALENCE_SCOPE_V3: Verify governance before intent. Returns (ok, signer_fingerprint, auth_verified).
    When CALYX_GOVERNANCE_REQUIRED=true: ungoverned requests rejected with 403.
    """
    governed, source = _is_governed_channel(request, req)
    sys_required = _governance_required_system()
    signer_fp = f"gateway:{source}" if governed and source else ""
    auth_verified = governed

    if not sys_required:
        return True, signer_fp or "ungoverned", auth_verified

    if governed:
        _emit("governance.auth.verified", "Governance auth verified via gateway", level="INFO", data={"source": source, "signer_fingerprint": signer_fp})
        return True, signer_fp, True

    # WO_CALYX_SIGN_INGRESS_AUTH_V4: Try signature path
    sig_b64 = (request.headers.get("X-Calyx-Signature") or "").strip()
    key_id = (request.headers.get("X-Calyx-Key-Id") or "").strip() or "architect"
    envelope_b64 = (request.headers.get("X-Calyx-Sign-Envelope") or "").strip()

    if not sig_b64 or not envelope_b64:
        _emit("governance.signature_missing", "Governance required but no signature or gateway", level="WARN", data={"entry_point": "direct"})
        _emit("governance.ungoverned_ingress_detected", "Ungoverned ingress rejected", level="WARN", data={"reason": "no_gateway_or_signature"})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": "direct_ingress_without_gateway"})
        return False, "", False

    try:
        import base64
        from calyx.kernel.canonical_hash import sha256_hex
        from calyx.kernel.nonce_ledger import nonce_seen
        from calyx.kernel.sign_request import (
            verify_envelope_schema,
            verify_signature,
            verify_timestamp,
        )

        envelope_bytes = base64.b64decode(envelope_b64, validate=True)
        envelope = json.loads(envelope_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        _emit("governance.signature_invalid", f"Envelope decode failed: {str(e)[:100]}", level="WARN", data={"entry_point": "direct"})
        _emit("governance.ungoverned_ingress_detected", "Ungoverned ingress rejected", level="WARN", data={"reason": "envelope_decode_failed"})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": "invalid_envelope"})
        return False, "", False

    err = verify_envelope_schema(envelope)
    if err:
        _emit("governance.signature_invalid", f"Envelope schema invalid: {err}", level="WARN", data={"entry_point": "direct", "error": err})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": err})
        return False, "", False

    err = verify_timestamp(envelope.get("ts_utc", ""))
    if err:
        _emit("governance.signature_invalid", f"Timestamp invalid: {err}", level="WARN", data={"entry_point": "direct"})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": err})
        return False, "", False

    nonce = envelope.get("nonce", "")
    if nonce_seen(nonce, key_id):
        _emit("governance.signature_replay_detected", "Nonce replay detected", level="WARN", data={"nonce_sha256": sha256_hex(nonce)[:16], "key_id": key_id})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": "replay"})
        return False, "", False

    norm_req = (req.user_text or "").strip()
    expected_sha = sha256_hex(norm_req)
    if envelope.get("normalized_request_sha256") != expected_sha:
        _emit("governance.signature_invalid", "normalized_request_sha256 mismatch", level="WARN", data={"entry_point": "direct"})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": "request_hash_mismatch"})
        return False, "", False

    ok, fp_or_err = verify_signature(envelope_bytes, sig_b64, key_id, REPO_ROOT)
    if not ok:
        _emit("governance.signature_invalid", fp_or_err, level="WARN", data={"entry_point": "direct", "key_id": key_id})
        _emit("governance.auth.required", "Governance auth required", level="WARN", data={"reason": "signature_verify_failed"})
        return False, "", False

    # WO_GOVERNANCE_SINGULARITY_V3: Extract doc_policy from envelope for deprecated-doc override
    try:
        dp = envelope.get("doc_policy")
        if isinstance(dp, dict) and dp.get("include_deprecated") is True:
            request.state.doc_override = {
                "source": "envelope",
                "scope": dp.get("scope") or "repo_search_only",
                "reason": dp.get("reason") or "",
                "envelope_nonce": envelope.get("nonce", "")[:16],
            }
        else:
            request.state.doc_override = None
    except Exception:
        request.state.doc_override = None

    _emit("governance.signature_verified", "Signature verified", level="INFO", data={"key_id": key_id, "auth_mode": "signature"})
    _emit("governance.auth.verified", "Governance auth verified via signature", level="INFO", data={"auth_mode": "signature", "signer_fingerprint": fp_or_err, "key_id": key_id})
    return True, fp_or_err, True


def _is_simple_confirmation_request(user_text: str) -> bool:
    """Detect requests that only need a brief confirmation. Bypass LLM to avoid hallucination."""
    t = (user_text or "").strip().lower()
    if not t or len(t) > 200:
        return False
    patterns = (
        "confirm receipt",
        "confirm receipt of",
        "acknowledge",
        "acknowledged",
        "no further action",
        "no action necessary",
        "got it",
        "received",
        "test message",
    )
    for p in patterns:
        if p in t:
            return True
    if t in ("cbo?", "cbo", "hello", "hi", "ping", "test"):
        return True
    return False


@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq, request: Request):
    _start = time.perf_counter()
    try:
        request.state.doc_override = None
    except Exception:
        pass
    governed, source = _is_governed_channel(request, req)
    entry_point = source or ("browser" if (req.session_id or "").lower() == "home" else "api")
    _emit("human.request.received", "Human ingress", level="INFO", data={"entry_point": entry_point, "session_id": (req.session_id or "home")[:32]})
    gov_ok, signer_fingerprint, auth_verified = _check_governance_auth(request, req)
    if not gov_ok:
        raise HTTPException(status_code=403, detail="governance.auth.required")
    try:
        request.state.auth_verified = auth_verified
        request.state.signer_fingerprint = signer_fingerprint
    except Exception:
        pass
    try:
        from calyx.kernel.event_ledger import set_human_auth_context
        am = "gateway" if governed else "signature"
        set_human_auth_context(auth_mode=am, auth_verified=auth_verified, signer_fingerprint=signer_fingerprint,
                              request_id=getattr(request.state, "corr_id", None))
    except Exception:
        pass
    if governed:
        _emit("openclaw.channel.inbound", f"Governed channel inbound source={source}", level="INFO", data={"source": source, "session_id": (req.session_id or "home")[:32]})
    _emit("cbo.chat.request", "POST /chat", level="INFO", data={"session_id": req.session_id or "home", "model_role": req.model_role or "none", "governed": governed})
    integrity_err = _check_integrity_gate()
    if integrity_err:
        if governed:
            _emit("openclaw.channel.rejected", f"Integrity gate blocked: {integrity_err}", level="WARN", data={"reason": integrity_err[:200], "source": source})
        _emit("cbo.chat.integrity_fail", f"Integrity gate blocked: {integrity_err}", level="WARN", data={"reason": integrity_err[:200]})
        raise HTTPException(status_code=503, detail=integrity_err)

    # WO_REQUEST_ORIENTATION_PROTOCOL_V1: Deterministic intent classification before any LLM/tool
    intent = classify_intent(req.user_text)
    _emit("intent.classified", "Intent classified", level="INFO", data={"intent": intent, "entry_point": entry_point})

    # Fast path: INTENT_HEARTBEAT — STATE.md only, no repo_search, no LLM
    if intent == "INTENT_HEARTBEAT":
        state_md = _load_state_md()
        hb = _extract_heartbeat_from_state(state_md)
        reply = json.dumps(hb) if hb else '{"error": "STATE.md empty or no heartbeat fields"}'
        _emit("fastpath.used", "Heartbeat fast path", level="INFO", data={"intent": "INTENT_HEARTBEAT", "deterministic_path_used": True})
        _emit("heartbeat.fastpath", "Heartbeat returned from STATE", level="INFO", data={"heartbeat_ts": hb.get("heartbeat_ts", "")})
        receipt = {
            "ts_utc": _now_iso(),
            "endpoint": "/chat",
            "session_id": req.session_id,
            "mode": req.mode,
            "allow_tools": req.allow_tools,
            "user_text_sha256": _sha256_text(req.user_text),
            "reply_text_sha256": _sha256_text(reply),
            "tool_calls": [],
            "executed_tools": [],
            "providers_called": [],
            "second_opinion_enabled": req.allow_second_opinion,
        }
        receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
        receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
        receipt["receipt_sha256"] = receipt_sha
        _write_receipt(receipt)
        crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, [evidence_state("STATE.md", REPO_ROOT)], True, governed, req.allow_tools)
        _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
        _emit("response.finalized", "Response sent (heartbeat fast path)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
        _emit("cbo.chat.complete", "Chat response sent (heartbeat fast path)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
        if governed:
            _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
        return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)

    # Fast path: INTENT_FAILURE_EVENT_QUERY — read FAILURE_EVENT_LOG.md, no repo_search, no synthesis (V2)
    if intent == "INTENT_FAILURE_EVENT_QUERY":
        fe_log = _load_failure_event_log()
        if not fe_log:
            reply = "Failure Event log not found."
            _emit("intent.source_violation", "FAILURE_EVENT_LOG.md missing", level="WARN", data={"intent": "INTENT_FAILURE_EVENT_QUERY"})
        else:
            reply = _extract_failure_event_format(fe_log) or "Failure Event format could not be extracted."
            _emit("failure_event.query.bound", "Failure event format from FAILURE_EVENT_LOG", level="INFO", data={"source": "docs/operations/FAILURE_EVENT_LOG.md"})
        _emit("fastpath.used", "Failure event query fast path", level="INFO", data={"intent": "INTENT_FAILURE_EVENT_QUERY", "deterministic_path_used": True})
        receipt = {
            "ts_utc": _now_iso(),
            "endpoint": "/chat",
            "session_id": req.session_id,
            "mode": req.mode,
            "allow_tools": req.allow_tools,
            "user_text_sha256": _sha256_text(req.user_text),
            "reply_text_sha256": _sha256_text(reply),
            "tool_calls": [],
            "executed_tools": [],
            "providers_called": [],
            "second_opinion_enabled": req.allow_second_opinion,
        }
        receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
        receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
        receipt["receipt_sha256"] = receipt_sha
        _write_receipt(receipt)
        crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, [evidence_file("docs/operations/FAILURE_EVENT_LOG.md", REPO_ROOT)], True, governed, req.allow_tools)
        _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
        _emit("response.finalized", "Response sent (failure event fast path)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
        _emit("cbo.chat.complete", "Chat response sent (failure event fast path)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
        if governed:
            _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
        return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)

    # Fast path: INTENT_COMPOUND_QUERY — search for X + which file defines Y, X != Y (V2)
    if intent == "INTENT_COMPOUND_QUERY" and req.allow_tools:
        x_target, y_target = parse_compound_targets(req.user_text)
        _emit("intent.compound.detected", "Compound query parsed", level="INFO", data={"x": x_target or "", "y": y_target or "", "entry_point": entry_point})
        reply_parts: list[str] = []
        tool_receipts_compound: list[dict] = []
        executed_compound: list[str] = []
        top_x: Optional[str] = None
        y_path: Optional[str] = None
        try:
            search_x = (x_target or "").strip()
            if search_x:
                ov, src = _get_doc_override(req, request)
                payload_x: dict = {"query": search_x, "max_hits": 5, "override_include_deprecated": ov, "override_source": src}
                if "failure" in search_x.lower():
                    payload_x["override_ignore_globs"] = True
                    payload_x["glob"] = "**/FAILURE_EVENT_LOG.md"
                result_x = await _call_dev_harness("/repo/search", payload_x)
                hits_x = result_x.get("hits", [])
                top_x: Optional[str] = None
                for h in hits_x:
                    if isinstance(h, str):
                        p = extract_file_path_from_hit(h)
                        if p:
                            if "failure" in search_x.lower() and ("FAILURE_EVENT_LOG" in p or "failure_event" in p.lower()):
                                top_x = p
                                break
                            if not top_x:
                                top_x = p
                if not top_x and hits_x and isinstance(hits_x[0], str):
                    top_x = extract_file_path_from_hit(hits_x[0])
                reply_parts.append(f"**Search Target ({x_target}):**\n- Top hit: {top_x or 'No matching file found.'}")
                tool_receipts_compound.append({"tool": "repo_search", "result_sha256": result_x.get("sha256")})
                executed_compound.append("repo_search")
            if y_target:
                yl = (y_target or "").lower()
                ov, src = _get_doc_override(req, request)
                payload_y: dict = {"query": "event_ledger" if ("emit" in yl or "event_ledger" in yl) else y_target, "max_hits": 10, "override_include_deprecated": ov, "override_source": src}
                if "emit" in yl or "event_ledger" in yl:
                    payload_y["glob"] = "**/event_ledger.py"
                result_y = await _call_dev_harness("/repo/search", payload_y)
                hits_y = result_y.get("hits", [])
                for h in hits_y:
                    if isinstance(h, str):
                        p = extract_file_path_from_hit(h)
                        if p and ".py" in p:
                            y_path = p
                            break
                if not y_path and hits_y and isinstance(hits_y[0], str):
                    y_path = extract_file_path_from_hit(hits_y[0])
                reply_parts.append(f"\n**File Definition Target ({y_target}):**\n- Defined in: {y_path or 'No matching file found.'}")
                tool_receipts_compound.append({"tool": "repo_search", "result_sha256": result_y.get("sha256")})
                if "repo_search" not in executed_compound:
                    executed_compound.append("repo_search")
            reply = "\n".join(reply_parts) if reply_parts else "Could not parse compound query."
            ev_compound: list[dict] = []
            if top_x:
                ev_compound.append(evidence_repo_hit(top_x, REPO_ROOT))
            if y_path:
                ev_compound.append(evidence_repo_hit(y_path, REPO_ROOT))
            _emit("fastpath.used", "Compound query deterministic path", level="INFO", data={"intent": "INTENT_COMPOUND_QUERY", "deterministic_path_used": True, "x": x_target, "y": y_target})
            receipt = {
                "ts_utc": _now_iso(),
                "endpoint": "/chat",
                "session_id": req.session_id,
                "mode": req.mode,
                "allow_tools": req.allow_tools,
                "user_text_sha256": _sha256_text(req.user_text),
                "reply_text_sha256": _sha256_text(reply),
                "tool_calls": tool_receipts_compound,
                "executed_tools": executed_compound,
                "providers_called": [],
                "second_opinion_enabled": req.allow_second_opinion,
            }
            receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
            receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
            receipt["receipt_sha256"] = receipt_sha
            _write_receipt(receipt)
            crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, ev_compound, True, governed, req.allow_tools)
            _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
            _emit("response.finalized", "Response sent (compound fast path)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
            _emit("cbo.chat.complete", "Chat response sent (compound fast path)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
            if governed:
                _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
            return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)
        except Exception as e:
            _emit("intent.source_violation", f"Compound query failed: {e}", level="WARN", data={"x": x_target, "y": y_target})
            reply = f"Compound query failed: {str(e)[:200]}"
            receipt = {
                "ts_utc": _now_iso(),
                "endpoint": "/chat",
                "session_id": req.session_id,
                "mode": req.mode,
                "allow_tools": req.allow_tools,
                "user_text_sha256": _sha256_text(req.user_text),
                "reply_text_sha256": _sha256_text(reply),
                "tool_calls": [],
                "executed_tools": [],
                "providers_called": [],
                "second_opinion_enabled": req.allow_second_opinion,
            }
            receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
            receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
            receipt["receipt_sha256"] = receipt_sha
            _write_receipt(receipt)
            crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, [], False, governed, req.allow_tools)
            _write_governance_budget(request, receipt, crh_result, entry_point, intent, False, _start, reply)
            _emit("response.finalized", "Response sent (compound fallback)", level="INFO", data={"intent": intent, "deterministic_path_used": False})
            _emit("cbo.chat.complete", "Chat response sent (compound fallback)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
            if governed:
                _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
            return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)

    # Fast path: INTENT_FILE_LOCATION — deterministic repo_search, top hit only, no synthesis invention
    if intent == "INTENT_FILE_LOCATION" and req.allow_tools:
        lower_text = (req.user_text or "").lower()
        query = "event_ledger" if "event_ledger" in lower_text else "def emit"
        ov, src = _get_doc_override(req, request)
        payload: dict = {"query": query, "max_hits": 10, "override_include_deprecated": ov, "override_source": src}
        if "event_ledger" in lower_text:
            payload["glob"] = "**/event_ledger.py"
        try:
            result = await _call_dev_harness("/repo/search", payload)
            hits = result.get("hits", [])
            top_path: Optional[str] = None
            prefer_event_ledger = "event_ledger" in lower_text
            for h in hits:
                if isinstance(h, str):
                    p = extract_file_path_from_hit(h)
                    if p and ".py" in p:
                        if prefer_event_ledger and "event_ledger" in p:
                            top_path = p
                            break
                        if not top_path:
                            top_path = p
            if not top_path and hits and isinstance(hits[0], str):
                top_path = extract_file_path_from_hit(hits[0])
            reply = top_path if top_path else "No matching file found."
            _emit("fastpath.used", "File location deterministic path", level="INFO", data={"intent": "INTENT_FILE_LOCATION", "deterministic_path_used": True, "path": top_path or ""})
            _emit("file_location.deterministic" if top_path else "file_location.none", "File location result", level="INFO", data={"path": top_path or "", "query": query})
            receipt = {
                "ts_utc": _now_iso(),
                "endpoint": "/chat",
                "session_id": req.session_id,
                "mode": req.mode,
                "allow_tools": req.allow_tools,
                "user_text_sha256": _sha256_text(req.user_text),
                "reply_text_sha256": _sha256_text(reply),
                "tool_calls": [{"tool": "repo_search", "result_sha256": result.get("sha256")}],
                "executed_tools": ["repo_search"],
                "providers_called": [],
                "second_opinion_enabled": req.allow_second_opinion,
            }
            receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
            receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
            receipt["receipt_sha256"] = receipt_sha
            _write_receipt(receipt)
            ev_file = [evidence_repo_hit(top_path, REPO_ROOT)] if top_path else []
            crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, ev_file, True, governed, req.allow_tools)
            _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
            _emit("response.finalized", "Response sent (file location fast path)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
            _emit("cbo.chat.complete", "Chat response sent (file location fast path)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
            if governed:
                _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
            return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)
        except Exception as e:
            _emit("file_location.none", "File location search failed", level="WARN", data={"error": str(e)[:200]})
            reply = "No matching file found."
            receipt = {
                "ts_utc": _now_iso(),
                "endpoint": "/chat",
                "session_id": req.session_id,
                "mode": req.mode,
                "allow_tools": req.allow_tools,
                "user_text_sha256": _sha256_text(req.user_text),
                "reply_text_sha256": _sha256_text(reply),
                "tool_calls": [],
                "executed_tools": [],
                "providers_called": [],
                "second_opinion_enabled": req.allow_second_opinion,
            }
            receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
            receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
            receipt["receipt_sha256"] = receipt_sha
            _write_receipt(receipt)
            crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, [], True, governed, req.allow_tools)
            _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
            _emit("response.finalized", "Response sent (file location fallback)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
            _emit("cbo.chat.complete", "Chat response sent (file location fallback)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
            if governed:
                _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
            return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)

    # Fast path: INTENT_CONFIRMATION — bypass LLM to avoid hallucination (TinyLlama, etc.)
    if intent == "INTENT_CONFIRMATION" or _is_simple_confirmation_request(req.user_text):
        reply = "Message received."
        receipt = {
            "ts_utc": _now_iso(),
            "endpoint": "/chat",
            "session_id": req.session_id,
            "mode": req.mode,
            "allow_tools": req.allow_tools,
            "user_text_sha256": _sha256_text(req.user_text),
            "reply_text_sha256": _sha256_text(reply),
            "tool_calls": [],
            "executed_tools": [],
            "providers_called": [],
            "second_opinion_enabled": req.allow_second_opinion,
        }
        receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
        receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
        receipt["receipt_sha256"] = receipt_sha
        _write_receipt(receipt)
        crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, [], True, governed, req.allow_tools)
        _write_governance_budget(request, receipt, crh_result, entry_point, intent, True, _start, reply)
        _emit("response.finalized", "Response sent (simple confirmation)", level="INFO", data={"intent": intent, "deterministic_path_used": True})
        _emit("cbo.chat.complete", "Chat response sent (simple confirmation)", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": []})
        if governed:
            _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
        return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=None)

    model_text = ""
    model_role = (req.model_role or "none").strip().lower()
    if model_role == "second":
        model_role = "second_opinion"
    kimi_receipt: Optional[dict] = None
    local_receipt: Optional[dict] = None
    architect_info: Optional[dict] = None
    openai_info: Optional[dict] = None
    state_injected = False

    if model_role and model_role != "none":
        prompt = (
            "You are CBO, orchestrator of Station Calyx.\n"
            "Be concise. If you suggest any tool actions, list them as bullet points but do not execute them.\n"
            "If the user only asks you to confirm receipt (or to confirm via a specific API), reply briefly with a confirmation and do not use tools.\n\n"
            f"User: {req.user_text}"
        )
        if model_role == "second_opinion":
            state_md = _load_state_md()
            if state_md:
                prompt = f"<STATE>\n{state_md}\n</STATE>\n\n{prompt}"
                state_injected = True
            if req.allow_tools:
                prompt += (
                    "\n\nIf you need repo info, you may respond with a JSON object containing key \"tool_requests\" "
                    "(array of objects with \"tool\" and optional \"params\"). Allowed tools only: repo_list (params: path, max_entries), "
                    "repo_search (params: query, glob, max_hits). Example: {\"tool_requests\": [{\"tool\": \"repo_search\", \"params\": {\"query\": \"Calyx\", \"max_hits\": 5}}]}."
                )
        elif model_role == "local":
            state_md = _load_state_md()
            if state_md:
                prompt = f"<STATE>\n{state_md}\n</STATE>\n\n{prompt}"
                state_injected = True
            if req.allow_tools:
                prompt += (
                    "\n\nIf you need repo info, you may respond with a JSON object containing key \"tool_requests\" "
                    "(array of objects with \"tool\" and optional \"params\"). Allowed tools only: repo_list (params: path, max_entries), "
                    "repo_search (params: query, glob, max_hits). Example: {\"tool_requests\": [{\"tool\": \"repo_search\", \"params\": {\"query\": \"Calyx\", \"max_hits\": 5}}]}."
                )
        elif model_role == "architect" and req.allow_tools:
            prompt += (
                "\n\nIf you need repo info, you may respond with a JSON object containing key \"tool_requests\" "
                "(array of objects with \"tool\" and optional \"params\"). Allowed tools only: repo_list (params: path, max_entries), "
                "repo_search (params: query, glob, max_hits). Example: {\"tool_requests\": [{\"tool\": \"repo_search\", \"params\": {\"query\": \"Calyx\", \"max_hits\": 5}}]}."
            )
        if model_role == "workhorse" and req.allow_tools:
            prompt += (
                "\n\nIf you need repo info, you may respond with a JSON object containing key \"tool_requests\" "
                "(array of objects with \"tool\" and optional \"params\"). Allowed tools only: repo_list (params: path, max_entries), "
                "repo_search (params: query, glob, max_hits). Example: {\"tool_requests\": [{\"tool\": \"repo_search\", \"params\": {\"query\": \"Calyx\", \"max_hits\": 5}}]}."
            )

        try:
            if model_role == "architect":
                model_text, architect_info = await _call_anthropic(prompt, max_output_tokens=900)
            elif model_role == "workhorse":
                model_text, openai_info = await _call_openai(prompt, max_output_tokens=900)
            elif model_role == "second_opinion":
                if not req.allow_second_opinion:
                    model_text = "[second_opinion] disabled. Set allow_second_opinion=true to enable."
                    kimi_receipt = {"provider": "kimi", "called": False, "base_url": None, "model_id": None, "http_status": None, "error_snippet": "Not called (allow_second_opinion=false).", "request_id": None}
                else:
                    model_text, kimi_receipt = await _call_kimi(prompt, max_output_tokens=900)
            elif model_role == "local":
                try:
                    from calyx.kernel.ollama_gate import check as ollama_gate_check, release as ollama_gate_release, record_failure as ollama_gate_record_failure, record_success as ollama_gate_record_success
                    gate = ollama_gate_check(
                        caller_key=req.session_id or "home",
                        request_metadata={"model": "local", "prompt_len": len(prompt), "service_name": "cbo_core", "endpoint": "/chat"},
                    )
                    if not gate.get("allowed"):
                        _emit("cbo.chat.ollama_denied", f"Ollama gate denied: {gate.get('reason', 'denied')}", level="WARN", data={"reason": gate.get("reason", "denied")[:100], "retry_after_ms": gate.get("retry_after_ms")})
                        model_text = f"[local] Ollama gate: {gate.get('reason', 'denied')}. Retry after {gate.get('retry_after_ms', 0)}ms."
                        local_receipt = {"provider": "local", "called": False, "base_url": None, "model_id": None, "http_status": None, "error_snippet": model_text, "request_id": None}
                    else:
                        try:
                            model_text, local_receipt = await _call_local(prompt, max_output_tokens=900)
                            if local_receipt.get("http_status", 0) >= 400 or local_receipt.get("error_snippet"):
                                ollama_gate_record_failure(req.session_id or "home")
                            else:
                                ollama_gate_record_success(req.session_id or "home")
                        finally:
                            ollama_gate_release(req.session_id or "home")
                except ImportError:
                    model_text, local_receipt = await _call_local(prompt, max_output_tokens=900)
            else:
                model_text = f"[cbo] Unknown model_role '{req.model_role}'"
        except Exception as e:
            model_text = f"[cbo] model error: {str(e)}"
            if model_role == "second_opinion":
                kimi_receipt = kimi_receipt or {"provider": "kimi", "called": True, "base_url": None, "model_id": None, "http_status": None, "error_snippet": str(e)[:500], "request_id": None}
            elif model_role == "local":
                local_receipt = local_receipt or {"provider": "local", "called": True, "base_url": None, "model_id": None, "http_status": None, "error_snippet": str(e)[:500], "request_id": None}

    tool_notes = ""
    tool_receipts = []
    executed_tools: list[str] = []

    # Read-only tool loop: up to CBO_TOOL_LOOP_MAX (default 3) to reduce CPU load during major operations.
    _tool_loop_max = 3
    try:
        _tool_loop_max = max(1, min(5, int(os.getenv("CBO_TOOL_LOOP_MAX", "3").strip() or "3")))
    except ValueError:
        pass
    if model_role in ("architect", "workhorse", "second_opinion", "local") and req.allow_tools and model_text:
        parsed = _parse_tool_requests(model_text)
        for item in parsed[:_tool_loop_max]:
            tool_name = item.get("tool")
            if tool_name not in ("repo_list", "repo_search"):
                continue
            params = item.get("params") or {}
            try:
                if tool_name == "repo_list":
                    payload = {"path": params.get("path", ""), "max_entries": min(int(params.get("max_entries", 200)), 500)}
                    result = await _call_dev_harness("/repo/list", payload)
                    tool_notes += "\n[tool] repo_list(path=%r, max_entries=%s)\n" % (payload["path"], payload["max_entries"])
                    tool_notes += "\n".join(result.get("entries", [])[:50])
                    tool_receipts.append({"tool": "repo_list", "result_sha256": result.get("sha256")})
                    executed_tools.append("repo_list")
                elif tool_name == "repo_search":
                    q = params.get("query") or "Calyx"
                    if not isinstance(q, str) or not q.strip():
                        continue
                    ov, src = _get_doc_override(req, request)
                    payload = {"query": q.strip(), "max_hits": min(int(params.get("max_hits", 200)), 200), "override_include_deprecated": ov, "override_source": src}
                    if params.get("glob"):
                        payload["glob"] = str(params["glob"])
                    result = await _call_dev_harness("/repo/search", payload)
                    tool_notes += "\n[tool] repo_search(query=%r, max_hits=%s)\n" % (payload["query"], payload["max_hits"])
                    tool_notes += "\n".join(result.get("hits", [])[:30])
                    tool_receipts.append({"tool": "repo_search", "result_sha256": result.get("sha256")})
                    executed_tools.append("repo_search")
            except Exception as e:
                tool_notes += f"\n[tool] {tool_name} failed: {str(e)}\n"

    # FE-2026-02-26-1: Only run deterministic search when model did NOT request repo_search.
    # Otherwise model's tool_requests (e.g. query="event_ledger") would be overridden by query="Calyx".
    if (
        req.allow_tools
        and "search" in req.user_text.lower()
        and len(executed_tools) < _tool_loop_max
        and "repo_search" not in executed_tools
    ):
        try:
            ov, src = _get_doc_override(req, request)
            result = await _call_dev_harness("/repo/search", {"query": "Calyx", "max_hits": 5, "override_include_deprecated": ov, "override_source": src})
            tool_notes += "\n[tool] repo_search(query='Calyx', max_hits=5)\n"
            tool_notes += "\n".join(result.get("hits", [])[:5])
            tool_receipts.append({"tool": "repo_search", "result_sha256": result.get("sha256")})
            executed_tools.append("repo_search")
        except Exception as e:
            tool_notes += f"\n[tool] repo_search failed: {str(e)}"

    # Local availability authentication: when tools are on, always verify CBO is locally available via Dev Harness.
    # Ensures we never report "Tools used: none" without having attested local availability; one successful tool call = attestation.
    local_available: Optional[bool] = None  # None = tools off (unverified), True = verified, False = harness unreachable
    if req.allow_tools:
        if not executed_tools:
            try:
                result = await _call_dev_harness("/repo/list", {"path": "", "max_entries": 1})
                tool_notes += "\n[local availability] Dev Harness OK\n"
                tool_receipts.append({"tool": "repo_list", "result_sha256": result.get("sha256")})
                executed_tools.append("repo_list")
                local_available = True
            except Exception as e:
                tool_notes += f"\n[local availability] Dev Harness unreachable: {str(e)}\n"
                local_available = False
        else:
            local_available = True
    else:
        local_available = None

    if executed_tools:
        # WO_IDLE_ACTIVITY_GOVERNANCE_V3: Idle compute protection — tool execution must have corr_id or task_corr_id
        # WO_CAUSAL_ENVELOPE_AUDIT_CLARITY_V1: audit.context.invalid_system_action if tools during preflight/boot
        try:
            from calyx.kernel.event_ledger import get_corr_id, get_system_phase
            from calyx.kernel.governance_budget import append_fe_candidate
            if get_system_phase():
                _emit("audit.context.invalid_system_action", "Tool execution attempted during system phase", level="WARN", data={"phase": get_system_phase(), "tools": executed_tools})
            cid = get_corr_id()
            if not cid:
                _emit("budget.violation", "ungoverned_compute", level="WARN", data={"reason": "tool execution without corr_id or task_corr_id"})
                _emit("governance.assertion.failed", "ungoverned_compute", level="WARN", data={"reason": "tool execution without corr_id or task_corr_id"})
                append_fe_candidate("ungoverned_compute", "cbo", "Tool execution without corr_id or task_corr_id", component="cbo_core")
        except Exception:
            pass
        _emit("tool.used", "Tools executed", level="INFO", data={"tools": executed_tools})
    tools_used = "Tools used: " + (", ".join(executed_tools) if executed_tools else "none")
    if req.allow_tools and not executed_tools:
        tools_used = "Tools used: none (local availability check failed)"
    footer = tools_used
    if state_injected:
        footer += "\nContext: STATE.md injected."
    # Attestation: CBO locally available (same as human auth — we attest this response is from local CBO).
    if local_available is True:
        attestation = "CBO locally available: yes (Dev Harness verified)"
    elif local_available is False:
        attestation = "CBO locally available: no (Dev Harness unreachable)"
    else:
        attestation = "CBO locally available: unverified (tools off)"
    # FE-2026-02-26-4, FE-5: Suppress raw tool_requests JSON when we executed tools from it (confusing UX).
    display_model_text = model_text or ""
    if executed_tools and model_text and "tool_requests" in model_text:
        import re
        # Remove ```json ... ``` or ``` ... ``` blocks containing tool_requests
        display_model_text = re.sub(r"```(?:json)?\s*[\s\S]*?\"tool_requests\"[\s\S]*?```", "", model_text)
        # FE-5: Also remove standalone {...} JSON (model may output raw JSON without code block)
        idx = display_model_text.find("tool_requests")
        while idx >= 0:
            start = display_model_text.rfind("{", 0, idx + 1)
            if start >= 0:
                depth, end = 1, start + 1
                while end < len(display_model_text) and depth > 0:
                    if display_model_text[end] == "{":
                        depth += 1
                    elif display_model_text[end] == "}":
                        depth -= 1
                    end += 1
                if depth == 0:
                    before = display_model_text[:start].rstrip()
                    after = display_model_text[end:].lstrip()
                    display_model_text = (before + "\n" + after).strip()
                    break
            idx = -1
        display_model_text = display_model_text.strip()
        # FE-8 fallback: if tool_requests still present (edge case), clear to force synthesis
        if executed_tools and "tool_requests" in display_model_text:
            display_model_text = ""

    # FE-6: When tools ran but model output was suppressed (only JSON), synthesize a reply from tool results.
    # FE-9 + WO_REQUEST_ORIENTATION_PROTOCOL_V1: Synthesis must cite ONLY files/paths from the tool results.
    allowed_paths: list[str] = []
    if "repo_search" in executed_tools and tool_notes:
        for line in tool_notes.splitlines():
            if line.strip() and not line.strip().startswith("[tool]"):
                p = extract_file_path_from_hit(line)
                if p and p not in allowed_paths:
                    allowed_paths.append(p)
    if executed_tools and (not display_model_text or len(display_model_text.strip()) < 40):
        synth_prompt = (
            f"The user asked: {req.user_text}\n\n"
            f"Tool results (cite ONLY these — do not invent filenames):\n{tool_notes}\n\n"
            "Provide a concise one-sentence answer. Use ONLY file paths from the tool results above. If unsure, say 'No matching file found.'"
        )
        try:
            if model_role == "local":
                synth_text, _ = await _call_local(synth_prompt, max_output_tokens=150)
                if synth_text and len(synth_text.strip()) > 5:
                    display_model_text = synth_text.strip()
                    _emit("synthesis.invoked", "Synthesis pass ran", level="DEBUG", data={"intent": intent})
        except Exception:
            pass
    # WO_REQUEST_ORIENTATION_PROTOCOL_V1 Phase 4: Synthesis grounding guardrail
    if allowed_paths and display_model_text:
        synth_contains_path = any(
            p in display_model_text or p.replace("/", "\\") in display_model_text
            for p in allowed_paths
        )
        if not synth_contains_path and any(
            ext in display_model_text for ext in (".py", ".js", ".ts", ".cpp", ".c", ".vue")
        ):
            _emit("synthesis.violation", "Synthesis cited path not in tool results", level="WARN", data={"allowed_paths": allowed_paths[:5], "synthesis_snippet": display_model_text[:200]})
            _emit("synthesis.hallucination_detected", "Synthesis path hallucination", level="WARN", data={"top_hit": allowed_paths[0] if allowed_paths else ""})
            display_model_text = f"The file is {allowed_paths[0]}." if allowed_paths else "No matching file found."

    reply = (
        f"[CBO online] session={req.session_id} mode={req.mode} allow_tools={req.allow_tools}\n"
        f"{attestation}\n"
        f"You said: {req.user_text}\n"
        f"Dev harness: {DEV_HARNESS_BASE}\n"
        f"{tool_notes}\n"
        + (f"{display_model_text}\n" if display_model_text else "")
        + footer
    ).strip()

    providers_called: list[str] = []
    if model_role == "architect":
        providers_called.append("anthropic")
    elif model_role == "workhorse":
        providers_called.append("openai")
    elif model_role == "second_opinion" and kimi_receipt and kimi_receipt.get("called"):
        providers_called.append("kimi")
    elif model_role == "local" and local_receipt and local_receipt.get("called"):
        providers_called.append("local")

    usage_summary: dict = {}
    if architect_info and architect_info.get("usage"):
        usage_summary["anthropic"] = dict(architect_info["usage"])
    if openai_info and openai_info.get("usage"):
        usage_summary["openai"] = dict(openai_info["usage"])
    if kimi_receipt and kimi_receipt.get("usage"):
        usage_summary["kimi"] = dict(kimi_receipt["usage"])
    if local_receipt and local_receipt.get("usage"):
        usage_summary["local"] = dict(local_receipt["usage"])

    total_cost_estimate_usd: Optional[float] = None
    for prov, u in usage_summary.items():
        inp = u.get("input_tokens") or 0
        out = u.get("output_tokens") or 0
        cost = _estimate_cost_usd(prov, inp, out)
        if cost is not None:
            u["cost_estimate_usd"] = cost
            if total_cost_estimate_usd is None:
                total_cost_estimate_usd = 0.0
            total_cost_estimate_usd += cost

    receipt = {
        "ts_utc": _now_iso(),
        "endpoint": "/chat",
        "session_id": req.session_id,
        "mode": req.mode,
        "allow_tools": req.allow_tools,
        "user_text_sha256": _sha256_text(req.user_text),
        "reply_text_sha256": _sha256_text(reply),
        "tool_calls": tool_receipts,
        "executed_tools": executed_tools,
        "providers_called": providers_called,
        "second_opinion_enabled": req.allow_second_opinion,
    }
    if usage_summary:
        receipt["usage"] = usage_summary
    if total_cost_estimate_usd is not None:
        receipt["cost_estimate_usd"] = round(total_cost_estimate_usd, 6)
    receipt["request_latency_ms"] = round((time.perf_counter() - _start) * 1000)
    if kimi_receipt is not None:
        receipt["second_opinion_receipt"] = kimi_receipt
    if local_receipt is not None:
        receipt["local_receipt"] = local_receipt
    receipt_sha = _sha256_bytes(json.dumps(receipt, sort_keys=True).encode("utf-8"))
    receipt["receipt_sha256"] = receipt_sha
    _write_receipt(receipt)
    ev_llm = [evidence_repo_hit(p, REPO_ROOT) for p in (allowed_paths or [])[:3]]
    crh_result = _emit_canonical_hash(request, intent, entry_point, (req.user_text or "").strip(), reply, ev_llm, False, governed, req.allow_tools)
    _write_governance_budget(request, receipt, crh_result, entry_point, intent, False, _start, reply)
    _emit("response.finalized", "Response sent (LLM path)", level="INFO", data={"intent": intent, "deterministic_path_used": False})
    _emit("cbo.chat.complete", "Chat response sent", level="INFO", data={"session_id": req.session_id or "home", "latency_ms": receipt["request_latency_ms"], "providers": providers_called})
    if governed:
        _emit("openclaw.channel.outbound", "Governed channel outbound", level="INFO", data={"source": source, "latency_ms": receipt["request_latency_ms"]})
    second_opinion_text: Optional[str] = model_text if model_role == "second_opinion" and model_text else None
    return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=second_opinion_text)
