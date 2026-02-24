from __future__ import annotations

import json
import os
import time
import hashlib
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
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


app = FastAPI(title="CBO Core", version="0.1")


@app.get("/state")
def get_state():
    """Return STATE.md contents for OpenClaw bridge and other consumers. Read-only."""
    return {"state_md": _load_state_md()}


@app.get("/sponsorship")
def get_sponsorship():
    """Return sponsorship status for BloomOS and stamping gates. Per CALYX_SIGN_CBO_SPONSORSHIP."""
    try:
        from .stamping import check_sponsorship
        res = check_sponsorship(repo_root=REPO_ROOT, verify_signature=True)
        return {"valid": res.valid, "reason": res.reason, "proposal_id": res.proposal_id}
    except Exception as e:
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
    integrity_err = _check_integrity_gate()
    if integrity_err:
        raise HTTPException(status_code=503, detail=integrity_err)
    try:
        from calyx.kernel.paths import resolve_runtime_dir
        from calyx.mail.router import deliver_to_cbo_ingest
        from calyx.cbo.intent_pipeline import ingest_mail_envelope, mint_work_envelope, mark_ready
        from calyx.execution.hub_runner import process_work_outbox
    except ImportError as e:
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
    mail_path = deliver_to_cbo_ingest(envelope, runtime_dir, replay_ledger=True)
    if mail_path is None:
        raise HTTPException(status_code=503, detail="deliver_failed_integrity_or_replay")
    intent_id = ingest_mail_envelope(mail_path, runtime_dir)
    if not intent_id:
        raise HTTPException(status_code=500, detail="ingest_failed")
    mark_ready(intent_id, runtime_dir)
    we = mint_work_envelope(intent_id, runtime_dir, repo_root=REPO_ROOT)
    if not we:
        raise HTTPException(status_code=500, detail="mint_failed")
    counts = process_work_outbox(repo_root=REPO_ROOT)
    return {
        "envelope_id": envelope_id,
        "intent_id": intent_id,
        "processed": counts.get("processed", 0),
        "denied": counts.get("denied", 0),
    }


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parse_tool_requests(text: str) -> list[dict]:
    """Extract tool_requests from model text. Returns list of {tool, params}; empty on any error."""
    if not text or not text.strip():
        return []
    raw = text.strip()
    # Try full string as JSON first
    for candidate in (raw, raw.split("\n")[-1].strip()):
        if not candidate.startswith("{"):
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
        return out
    return []


def _write_receipt(obj: dict) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with open(RECEIPTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


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


@app.post("/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    _start = time.perf_counter()
    integrity_err = _check_integrity_gate()
    if integrity_err:
        raise HTTPException(status_code=503, detail=integrity_err)
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
                    payload = {"query": q.strip(), "max_hits": min(int(params.get("max_hits", 200)), 200)}
                    if params.get("glob"):
                        payload["glob"] = str(params["glob"])
                    result = await _call_dev_harness("/repo/search", payload)
                    tool_notes += "\n[tool] repo_search(query=%r, max_hits=%s)\n" % (payload["query"], payload["max_hits"])
                    tool_notes += "\n".join(result.get("hits", [])[:30])
                    tool_receipts.append({"tool": "repo_search", "result_sha256": result.get("sha256")})
                    executed_tools.append("repo_search")
            except Exception as e:
                tool_notes += f"\n[tool] {tool_name} failed: {str(e)}\n"

    # Simple deterministic behavior: if user asks for "search", do repo_search (skip if already at tool cap to reduce load).
    if req.allow_tools and "search" in req.user_text.lower() and len(executed_tools) < _tool_loop_max:
        try:
            result = await _call_dev_harness("/repo/search", {"query": "Calyx", "max_hits": 5})
            tool_notes += "\n[tool] repo_search(query='Calyx', max_hits=5)\n"
            tool_notes += "\n".join(result.get("hits", [])[:5])
            tool_receipts.append({"tool": "repo_search", "result_sha256": result.get("sha256")})
            if "repo_search" not in executed_tools:
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
    reply = (
        f"[CBO online] session={req.session_id} mode={req.mode} allow_tools={req.allow_tools}\n"
        f"{attestation}\n"
        f"You said: {req.user_text}\n"
        f"Dev harness: {DEV_HARNESS_BASE}\n"
        f"{tool_notes}\n"
        + (f"{model_text}\n" if model_text else "")
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

    second_opinion_text: Optional[str] = model_text if model_role == "second_opinion" and model_text else None
    return ChatResp(session_id=req.session_id, reply_text=reply, receipt_sha256=receipt_sha, second_opinion_text=second_opinion_text)
