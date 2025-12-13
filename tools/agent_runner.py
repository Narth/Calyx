"""Local agent scaffold for Calyx Terminal.

This script:
- loads the configured local LLM from `tools/models/MODEL_MANIFEST.json`
- generates a multi-step plan for the provided goal
- optionally asks the model to draft patch suggestions (kept as files, not applied)
- optionally runs configured test commands
- writes an auditable bundle under `outgoing/agent_run_<timestamp>/`

Nothing is applied to the working tree automatically.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import textwrap
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
import importlib
import re
import threading
try:
    # Optional: keep SVF comms active for shared outputs/notes
    from tools.svf_util import ensure_svf_running  # type: ignore
except Exception:
    def ensure_svf_running(*args, **kwargs):  # type: ignore
        return False

from agent_policy import assert_allowed, get_model_entry
try:
    # Optional: used when --publish-bus is enabled
    from tools.agent_bus import publish_message as _bus_publish  # type: ignore
except Exception:  # pragma: no cover - optional import
    _bus_publish = None

try:
    from calyx_core.intercept import (
        ActionType,
        InterceptContext,
        ResourceSnapshot,
        StationInterceptor,
    )
except Exception:  # pragma: no cover - optional import
    ActionType = None  # type: ignore
    InterceptContext = None  # type: ignore
    ResourceSnapshot = None  # type: ignore
    StationInterceptor = None  # type: ignore


LLM_IMPORT_ERROR: Optional[Exception] = None
_LLAMA_CLASS: Optional[type] = None
LLM_CALLS: List[Dict[str, Any]] = []

PLAN_MAX_TOKENS = int(os.environ.get("CALYX_LLM_PLAN_MAX_TOKENS", "448"))
PLAN_RETRY_MAX_TOKENS = int(os.environ.get("CALYX_LLM_PLAN_RETRY_TOKENS", str(max(PLAN_MAX_TOKENS, 640))))
STATUS_MAX_TOKENS = int(os.environ.get("CALYX_LLM_STATUS_MAX_TOKENS", "40"))
PATCH_MAX_TOKENS = int(os.environ.get("CALYX_LLM_PATCH_MAX_TOKENS", "896"))
FULL_FILE_MAX_TOKENS = int(os.environ.get("CALYX_LLM_FULL_MAX_TOKENS", "1152"))


PLAN_SCHEMA_VERSION = "2.0-min"
PLAN_SCHEMA_ALLOWED_RISK = {"low", "medium", "high"}
PLAN_BEAMS = max(1, int(os.environ.get("CALYX_LLM_PLAN_BEAMS", "3")))
CRITIC_ACCEPT_THRESHOLD = int(os.environ.get("CALYX_PLAN_CRITIC_THRESHOLD", "70"))
MINIMAL_FALLBACK_PLAN = {
    "schema_version": PLAN_SCHEMA_VERSION,
    "task_id": "t-fallback",
    "objective": "Perform read-only health scan",
    "prechecks": [{"name": "heartbeat_fresh", "cmd": "check_heartbeat"}],
    "steps": [
        {
            "id": "s1",
            "action": "collect_metrics",
            "target": "",
            "args": {"scope": "read_only"},
        }
    ],
    "verification": [
        {"metric": "Harmony", "method": "read_metric", "expect": ">=0"}
    ],
    "safety": {"risk_level": "low", "write_scope": ["logs/*"]},
}


def robust_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    frag = match.group(0)
    frag = re.sub(r",(\s*[}\]])", r"\1", frag)
    frag = (
        frag.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("`", '"')
    )
    frag = re.sub(r'(\s)([A-Za-z0-9_]+)\s*:', r'\1"\2":', frag)
    try:
        return json.loads(frag)
    except Exception:
        return None


def _decode_pointer_segment(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _apply_json_pointer_edit(doc: Any, pointer: str, value: Any) -> bool:
    if not pointer or pointer == "/":
        if isinstance(value, dict):
            if isinstance(doc, dict):
                doc.clear()
                doc.update(value)
                return True
        return False
    if pointer[0] != "/":
        return False
    parts = [_decode_pointer_segment(p) for p in pointer.strip("/").split("/")]
    target = doc
    for idx, part in enumerate(parts[:-1]):
        if isinstance(target, list):
            try:
                part_idx = int(part)
            except ValueError:
                return False
            if part_idx >= len(target):
                return False
            target = target[part_idx]
        elif isinstance(target, dict):
            if part not in target:
                if isinstance(parts[idx + 1], str):
                    target[part] = {}
                else:
                    target[part] = []
            target = target[part]
        else:
            return False
    last = parts[-1]
    if isinstance(target, list):
        try:
            last_idx = int(last)
        except ValueError:
            return False
        if last_idx == len(target):
            target.append(value)
            return True
        if 0 <= last_idx < len(target):
            target[last_idx] = value
            return True
        return False
    if isinstance(target, dict):
        target[last] = value
        return True
    return False


def _ensure_list_of_strings(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    result = []
    for item in values:
        if isinstance(item, str):
            result.append(item.strip())
        else:
            result.append(str(item))
    return result


def _ensure_dict(obj: Any) -> Dict[str, Any]:
    return obj if isinstance(obj, dict) else {}


def _validate_plan_schema(plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(plan, dict):
        return False, ["Plan response was not a JSON object"]

    plan.setdefault("schema_version", PLAN_SCHEMA_VERSION)
    plan["schema_version"] = str(plan.get("schema_version", PLAN_SCHEMA_VERSION))

    task_id = plan.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        plan["task_id"] = uuid.uuid4().hex

    objective = plan.get("objective")
    plan["objective"] = str(objective) if objective is not None else ""

    prechecks_raw = plan.get("prechecks")
    if not isinstance(prechecks_raw, list):
        prechecks_raw = []
    prechecks_clean: List[Dict[str, str]] = []
    for item in prechecks_raw:
        entry = _ensure_dict(item)
        name = entry.get("name")
        cmd = entry.get("cmd")
        if not name or not cmd:
            continue
        prechecks_clean.append({"name": str(name), "cmd": str(cmd)})
    plan["prechecks"] = prechecks_clean

    steps_raw = plan.get("steps")
    if not isinstance(steps_raw, list):
        steps_raw = []
    steps_clean: List[Dict[str, Any]] = []
    for idx, step in enumerate(steps_raw, start=1):
        entry = _ensure_dict(step)
        action = entry.get("action")
        if not action:
            continue
        steps_clean.append(
            {
                "id": str(entry.get("id") or f"s{idx}"),
                "action": str(action),
                "target": str(entry.get("target", "")),
                "args": entry.get("args") if isinstance(entry.get("args"), dict) else {},
            }
        )
    if not steps_clean:
        errors.append("Plan did not include any actionable steps")
    plan["steps"] = steps_clean

    verification_raw = plan.get("verification")
    if not isinstance(verification_raw, list):
        verification_raw = []
    verification_clean: List[Dict[str, str]] = []
    for item in verification_raw:
        entry = _ensure_dict(item)
        metric = entry.get("metric")
        method = entry.get("method")
        expect = entry.get("expect")
        if not metric or not method:
            continue
        verification_clean.append(
            {
                "metric": str(metric),
                "method": str(method),
                "expect": str(expect) if expect is not None else "",
            }
        )
    plan["verification"] = verification_clean

    safety_raw = _ensure_dict(plan.get("safety"))
    risk = str(safety_raw.get("risk_level", "medium")).lower()
    if risk not in PLAN_SCHEMA_ALLOWED_RISK:
        risk = "medium"
    write_scope = _ensure_list_of_strings(safety_raw.get("write_scope", []))
    plan["safety"] = {"risk_level": risk, "write_scope": write_scope}

    return (len(errors) == 0), errors


def _extract_plan_dict(response_text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}")
        if start == -1 or end == -1:
            return None
        snippet = response_text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None


def _critique_plan(llm: "ChatModel", plan: Dict[str, Any], *, call_suffix: str = "") -> Optional[Dict[str, Any]]:
    plan_text = json.dumps(plan, ensure_ascii=False, indent=2)
    system_prompt = "You are Station Calyx Plan Critic."
    user_prompt = (
        "Score the following plan JSON for schema validity, completeness, feasibility, and safety. "
        "Return JSON in the form {\"score\": int, \"edits\": [{\"json_pointer\": str, \"proposed_value\": any}], \"reasons\": [str]}."
        "\nPlan JSON:\n"
        f"{plan_text}"
    )
    response = _call_chat(
        llm,
        system_prompt,
        user_prompt,
        max_tokens=256,
        latency_sensitive=False,
        call_context=f"plan_critic{call_suffix}",
    )
    critic_data = _extract_plan_dict(response)
    if critic_data is None:
        return None
    try:
        critic_data["score"] = int(critic_data.get("score", 0))
    except Exception:
        critic_data["score"] = 0
    edits = critic_data.get("edits", [])
    if not isinstance(edits, list):
        critic_data["edits"] = []
    return critic_data


def _apply_critic_edits(plan: Dict[str, Any], edits: List[Dict[str, Any]]) -> bool:
    applied = False
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        pointer = edit.get("json_pointer") or edit.get("path")
        if not pointer:
            continue
        value = edit.get("proposed_value", edit.get("value"))
        if _apply_json_pointer_edit(plan, pointer, value):
            applied = True
    return applied


def _plan_dict_to_agent_steps(plan: Dict[str, Any]) -> List[AgentStep]:
    result: List[AgentStep] = []
    for step in plan.get("steps", []):
        action = step.get("action", "")
        target = step.get("target", "")
        description = step.get("rationale") or " ".join(part for part in [action, target] if part).strip()
        if not description:
            description = action or "Execute step"
        files = _ensure_list_of_strings(step.get("files", []))
        if not files and target:
            files = [target]
        result.append(
            AgentStep(
                description=description or step.get("action", "Untitled step"),
                files=files,
                rationale=step.get("rationale", ""),
            )
        )
    return result


class _LLMTokenController:
    """Adaptive token budgeting to keep local calls within latency targets."""

    def __init__(self) -> None:
        self._latency_target = float(os.environ.get("CALYX_LLM_TARGET_LATENCY", "20"))
        self._plan_floor = max(96, int(os.environ.get("CALYX_LLM_PLAN_FLOOR", "176")))
        self._plan_ceiling = max(self._plan_floor, PLAN_MAX_TOKENS)
        start_default = int(os.environ.get("CALYX_LLM_PLAN_START", "384"))
        self._plan_budget = min(self._plan_ceiling, max(self._plan_floor, start_default))
        self._gen_floor = max(128, int(os.environ.get("CALYX_LLM_GENERATION_FLOOR", "256")))
        self._gen_ceiling = max(self._gen_floor, int(os.environ.get("CALYX_LLM_GENERATION_CEILING", str(max(PATCH_MAX_TOKENS, FULL_FILE_MAX_TOKENS)))))
        self._ema_duration: Optional[float] = None

    def request(self, desired: int, latency_sensitive: bool = True) -> int:
        desired = max(0, int(desired))
        if desired == 0:
            return 0
        if latency_sensitive:
            if desired <= self._plan_floor:
                return desired
            return min(desired, self._plan_budget)
        if desired <= self._gen_floor:
            return desired
        return min(desired, self._gen_ceiling)

    def observe(self, duration: float, latency_sensitive: bool = True) -> None:
        if not latency_sensitive:
            return
        alpha = 0.3
        if self._ema_duration is None:
            self._ema_duration = duration
        else:
            self._ema_duration = (1 - alpha) * self._ema_duration + alpha * duration
        target = max(1.0, self._latency_target)
        if self._ema_duration > target and self._plan_budget > self._plan_floor:
            self._plan_budget = max(self._plan_floor, int(self._plan_budget * 0.75))
        elif self._ema_duration < target * 0.6 and self._plan_budget < self._plan_ceiling:
            self._plan_budget = min(self._plan_ceiling, max(self._plan_budget + 16, int(self._plan_budget * 1.1)))

    def snapshot(self) -> Dict[str, float]:
        return {
            "latency_target": self._latency_target,
            "plan_budget": self._plan_budget,
            "plan_floor": self._plan_floor,
            "plan_ceiling": self._plan_ceiling,
        }


_TOKEN_CONTROLLER = _LLMTokenController()


@runtime_checkable
class ChatModel(Protocol):
    """Minimal protocol for chat-capable models."""

    def create_chat_completion(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - protocol stub
        ...


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "outgoing"
LLM_TOKEN_DIR = DEFAULT_OUTPUT_DIR  # token files live under outgoing/
INTERCEPT_PHASE_TAG = os.environ.get("CALYX_PHASE_TAG", "phaseA")
_INTERCEPTOR = StationInterceptor() if StationInterceptor else None
_INTERCEPT_AGENT_NAME: Optional[str] = None
_INTERCEPT_RUN_DIR: Optional[Path] = None
_HEARTBEAT_INTERCEPTED = False
MAILBOX_ROOT = ROOT / "outgoing" / "User1"


# ----------------------------- data structures -----------------------------


@dataclass
class AgentStep:
    description: str
    files: List[str]
    rationale: str


@dataclass
class AgentRun:
    goal: str
    plan: List[AgentStep]
    patches: Dict[str, str]
    tests: List[Dict[str, str]]
    success: bool
    model_id: str
    model_path: str
    backend: str


def _set_intercept_context(agent_name: str, run_dir: Optional[Path] = None) -> None:
    """Cache agent metadata for later intercept events."""
    global _INTERCEPT_AGENT_NAME, _INTERCEPT_RUN_DIR
    _INTERCEPT_AGENT_NAME = agent_name
    if run_dir is not None:
        _INTERCEPT_RUN_DIR = run_dir


def _is_mailbox_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        return MAILBOX_ROOT in resolved.parents or resolved == MAILBOX_ROOT
    except Exception:
        return False


def _intercept_event(
    action_type: "ActionType",
    description: str,
    *,
    surface: str,
    tool_name: Optional[str] = None,
    payload_meta: Optional[Dict[str, Any]] = None,
    tes: Optional[float] = None,
    agii: Optional[float] = None,
    resources: Optional["ResourceSnapshot"] = None,
    dry_run: bool = False,
) -> Optional[Any]:
    """Lightweight wrapper to emit intercept records in record-only mode."""
    if not _INTERCEPTOR or not InterceptContext or not ActionType:
        return None
    meta = dict(payload_meta or {})
    meta.setdefault("phase", INTERCEPT_PHASE_TAG)
    meta.setdefault("surface", surface)
    if _INTERCEPT_RUN_DIR:
        meta.setdefault("run_dir", str(_INTERCEPT_RUN_DIR))
    ctx = InterceptContext(
        agent_name=_INTERCEPT_AGENT_NAME or "agent",
        action_type=action_type,
        description=description,
        tool_name=tool_name,
        payload_meta=meta,
        tes=tes,
        agii=agii,
        resources=resources,
        dry_run=dry_run,
    )
    try:
        return _INTERCEPTOR.check(ctx)
    except Exception:
        return None


# ----------------------------- helpers ------------------------------------


def _ensure_llm(model_path: str, n_ctx: int = 4096) -> "ChatModel":
    global _LLAMA_CLASS, LLM_IMPORT_ERROR

    if _LLAMA_CLASS is None:
        try:
            module = importlib.import_module("llama_cpp")
            _LLAMA_CLASS = getattr(module, "Llama")
        except Exception as exc:  # pragma: no cover - import guard
            LLM_IMPORT_ERROR = exc
            raise RuntimeError(
                "llama-cpp-python is not available in this environment. "
                "Install it (e.g. inside WSL) before running agent_runner."
            ) from exc

    return _LLAMA_CLASS(model_path=model_path, n_ctx=n_ctx, temperature=0.2)


def _acquire_llm_token(token_name: Optional[str], wait_sec: int = 60) -> Optional[Path]:
    """Acquire a simple cooperative lock for LLM usage.

    Creates outgoing/<token_name>.lock with owner pid and timestamp.
    If token_name is None, returns None immediately.
    """
    if not token_name:
        return None
    token_path = LLM_TOKEN_DIR / f"{token_name}.lock"
    deadline = time.time() + max(0, int(wait_sec))
    while True:
        try:
            if not token_path.exists():
                token_path.write_text(json.dumps({
                    "owner_pid": os.getpid(),
                    "ts": time.time(),
                    "token": token_name,
                }, indent=2), encoding="utf-8")
                return token_path
            else:
                # Consider stale if older than 10 minutes
                try:
                    age = time.time() - token_path.stat().st_mtime
                    if age > 600:
                        token_path.unlink(missing_ok=True)  # pyright: ignore[reportGeneralTypeIssues]
                        continue
                except Exception:
                    pass
        except Exception:
            pass
        if time.time() >= deadline:
            return None
        time.sleep(1.0)


def _release_llm_token(path: Optional[Path]) -> None:
    if not path:
        return
    try:
        path.unlink(missing_ok=True)  # pyright: ignore[reportGeneralTypeIssues]
    except Exception:
        pass


def _call_chat(
    llm: "ChatModel",
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 768,
    latency_sensitive: bool = True,
    call_context: Optional[str] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Call the LLM using chat completion and return the text response."""
    granted_tokens = _TOKEN_CONTROLLER.request(max_tokens, latency_sensitive=latency_sensitive)
    start = time.time()
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=granted_tokens,
        temperature=0.2,
        stop=["<|im_end|>", "</s>"]
    )
    duration = time.time() - start
    text = response["choices"][0]["message"]["content"].strip()
    _TOKEN_CONTROLLER.observe(duration, latency_sensitive=latency_sensitive)
    controller_state = _TOKEN_CONTROLLER.snapshot()
    # Record telemetry for adaptability
    meta: Dict[str, Any] = {
        "system_len": len(system_prompt),
        "user_len": len(user_prompt),
        "requested_tokens": max_tokens,
        "granted_tokens": granted_tokens,
        "max_tokens": granted_tokens,
        "duration_s": round(duration, 3),
        "output_len": len(text),
        "latency_sensitive": latency_sensitive,
        "plan_budget": controller_state.get("plan_budget"),
    }
    if call_context:
        meta["context"] = call_context
    if extra_meta:
        meta.update(extra_meta)
    LLM_CALLS.append(meta)
    if ActionType:
        try:
            model_hint = getattr(llm, "model_path", None) or getattr(llm, "model_id", None) or "llm_chat"
            _intercept_event(
                action_type=ActionType.TOOL_CALL,
                description="LLM chat completion",
                surface="tool_call",
                tool_name=str(model_hint),
                payload_meta={
                    "call_context": call_context,
                    "granted_tokens": granted_tokens,
                    "output_len": len(text),
                    "duration_s": round(duration, 3),
                    "latency_sensitive": latency_sensitive,
                },
            )
        except Exception:
            pass
    return text


def _parse_plan(text: str) -> List[AgentStep]:
    """Expect a JSON object with `steps` array."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("LLM response is not valid JSON")
        snippet = text[start : end + 1]
        try:
            data = json.loads(snippet)
        except json.JSONDecodeError:
            try:
                import ast

                candidate = ast.literal_eval(snippet)
                if isinstance(candidate, dict):
                    data = candidate
                else:
                    raise ValueError
            except Exception as exc:
                raise ValueError("LLM response is not valid JSON") from exc

    if isinstance(data, list):
        data = {"steps": data}
    elif not isinstance(data, dict):
        raise ValueError("LLM response is not valid JSON")

    steps = []
    for item in data.get("steps", []):
        steps.append(
            AgentStep(
                description=item.get("description", ""),
                files=item.get("files", []),
                rationale=item.get("rationale", ""),
            )
        )
    if not steps:
        raise ValueError("No steps returned by the model")
    return steps


def _repo_summary(max_entries: int = 8) -> str:
    entries = []
    for path in sorted(ROOT.iterdir()):
        if path.name.startswith("."):
            continue
        if path.is_dir():
            entries.append(f"dir: {path.name}/")
        else:
            entries.append(f"file: {path.name}")
        if len(entries) >= max_entries:
            break
    return "\n".join(entries)


def _start_memory_sampler(run_dir: Path, interval: int = 30) -> tuple[threading.Event, threading.Thread]:
    """Start a background thread that samples this process memory and writes
    JSON lines to run_dir/memory_samples.jsonl. Returns (stop_event, thread).

    Lightweight: tries to use psutil if available, falls back to querying
    process memory via the OS if not.
    """
    stop_event = threading.Event()
    out_path = run_dir / "memory_samples.jsonl"

    def _sample_loop():
        try:
            try:
                import psutil
                psutil_available = True
            except Exception:
                psutil_available = False

            pid = os.getpid()
            while not stop_event.is_set():
                ts = time.time()
                sample = {"ts": ts}
                try:
                    if psutil_available:
                        p = psutil.Process(pid)
                        mi = p.memory_info()
                        vm = psutil.virtual_memory()
                        sample.update({
                            "pid": pid,
                            "rss": getattr(mi, "rss", None),
                            "vms": getattr(mi, "vms", None),
                            "shared": getattr(mi, "shared", None),
                            "system_mem_percent": getattr(vm, "percent", None),
                            "system_mem_total": getattr(vm, "total", None),
                            "system_mem_available": getattr(vm, "available", None),
                        })
                        # Also sample direct children (if any) to capture spawned workers
                        children = []
                        try:
                            for c in p.children(recursive=False):
                                try:
                                    cmi = c.memory_info()
                                    children.append({
                                        "pid": c.pid,
                                        "rss": getattr(cmi, "rss", None),
                                        "vms": getattr(cmi, "vms", None),
                                    })
                                except Exception:
                                    pass
                        except Exception:
                            children = []
                        if children:
                            sample["children"] = children
                    else:
                        # Fallback: use tasklist on Windows or ps on *nix
                        if sys.platform.startswith("win"):
                            # tasklist returns kB values under /FO CSV
                            out = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"], stderr=subprocess.DEVNULL)
                            try:
                                text = out.decode("utf-8", errors="ignore").splitlines()
                                if len(text) >= 2:
                                    import csv
                                    row = list(csv.reader([text[1]]))[0]
                                    mem_str = row[-2]
                                    # e.g. "12,345 K"
                                    mem_num = int(re.sub(r"[^0-9]", "", mem_str)) * 1024
                                    sample.update({"pid": pid, "rss": mem_num})
                            except Exception:
                                pass
                        else:
                            out = subprocess.check_output(["ps", "-p", str(pid), "-o", "rss="], stderr=subprocess.DEVNULL)
                            try:
                                rss_kb = int(out.strip() or 0)
                                sample.update({"pid": pid, "rss": rss_kb * 1024})
                            except Exception:
                                pass
                except Exception:
                    # sampling must not crash the run
                    pass

                try:
                    with open(out_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(sample) + "\n")
                except Exception:
                    pass

                # Wait with early exit possibility
                stop_event.wait(interval)
        except Exception:
            return

    th = threading.Thread(target=_sample_loop, daemon=True, name="agent_memory_sampler")
    th.start()
    return stop_event, th


def _current_file_snapshot(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return "(File does not exist yet.)"
    content = path.read_text(encoding="utf-8", errors="ignore")
    if len(content) > max_chars:
        return content[:max_chars] + "\n... (truncated)"
    return content


def _generate_plan(
    llm: "ChatModel", goal: str, max_steps: int
) -> Tuple[List[AgentStep], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    system_prompt = (
        "You are a senior Python engineer and release manager. "
        "Respond ONLY with compact JSON."
    )
    summary = _repo_summary()
    schema_prompt = textwrap.dedent(
        """
        schema_version: "2.0-min"
        task_id: "<uuid>"
        objective: "<single sentence objective>"
        prechecks: [
          {"name":"heartbeat_fresh","cmd":"check_heartbeat"}
        ]
        steps: [
          {
            "id":"s1",
            "action":"restart_service",
            "target":"agent_scheduler",
            "args":{}
          }
        ]
        verification: [
          {"metric":"Harmony","method":"read_metric","expect":">=60"}
        ]
        safety: {
          "risk_level":"low|medium|high",
          "write_scope":["logs/*","cache/*"]
        }
        """
    ).strip()

    base_user_prompt = textwrap.dedent(
        f"""
        Goal: {goal}
        Repository snapshot:
        {summary}

        Produce a maintenance plan with at most {max_steps} steps that strictly follows the schema below.
        Fill in every field with concrete, station-specific details.
        Output ONLY JSON (no prose, no code fences, no comments).
        Replace placeholders with real values; if a list is empty, emit [].

        Schema template:
        {schema_prompt}
        """
    ).strip()

    attempts = [
        {
            "prompt": base_user_prompt,
            "tokens": PLAN_MAX_TOKENS,
            "latency_sensitive": True,
            "context": "plan_primary",
        },
        {
            "prompt": base_user_prompt
            + "\n\nIf you are uncertain, prefer diagnostic steps (log review, heartbeat check, compile tests) but still return a complete JSON plan that fits the schema.",
            "tokens": PLAN_RETRY_MAX_TOKENS,
            "latency_sensitive": False,
            "context": "plan_retry",
        },
        {
            "prompt": base_user_prompt
            + "\n\nFINAL CHANCE: Output JSON EXACTLY matching the schema; do not invent new keys, omit required fields, or add prose. Escape double quotes inside string values.",
            "tokens": PLAN_RETRY_MAX_TOKENS,
            "latency_sensitive": False,
            "context": "plan_retry_strict",
        },
    ]
    attempt_records: List[Dict[str, Any]] = []
    last_error: Optional[str] = None
    best_plan: Optional[Dict[str, Any]] = None
    best_score: int = -1
    best_metadata: Optional[Dict[str, Any]] = None

    for attempt in attempts:
        beam_count = PLAN_BEAMS if attempt["context"] == "plan_primary" else 1
        for beam_idx in range(beam_count):
            context_label = attempt["context"]
            if beam_count > 1:
                context_label = f"{context_label}_b{beam_idx + 1}"
            record: Dict[str, Any] = {"context": context_label}
            response = _call_chat(
                llm,
                system_prompt,
                attempt["prompt"],
                max_tokens=attempt["tokens"],
                latency_sensitive=attempt["latency_sensitive"],
                call_context=context_label,
            )
            record["raw"] = response
            call_meta = LLM_CALLS[-1] if LLM_CALLS else None

            plan_dict_raw = robust_parse_json(response)
            if plan_dict_raw is None:
                last_error = "plan_json_parse_failed"
                record["valid_json"] = False
                record["error"] = last_error
                if call_meta is not None:
                    call_meta["plan_valid"] = False
                    call_meta["plan_error"] = last_error
                attempt_records.append(record)
                continue

            record["valid_json"] = True
            record["repaired"] = plan_dict_raw
            plan_dict = copy.deepcopy(plan_dict_raw)

            valid, validation_errors = _validate_plan_schema(plan_dict)
            record["plan_valid"] = valid
            if validation_errors:
                record["validation_errors"] = validation_errors
            if call_meta is not None:
                call_meta["plan_valid"] = valid
                if validation_errors:
                    call_meta["plan_validation_errors"] = validation_errors
            if not valid:
                last_error = "plan_schema_invalid"
                attempt_records.append(record)
                continue

            critic_suffix = f"_{context_label}"
            critic = _critique_plan(llm, plan_dict, call_suffix=critic_suffix)
            if critic is None:
                last_error = "critic_parse_failed"
                record["critic_error"] = last_error
                if call_meta is not None:
                    call_meta["critic_error"] = last_error
                attempt_records.append(record)
                continue

            score = int(critic.get("score", 0))
            record["critic_score"] = score
            if call_meta is not None:
                call_meta["critic_score"] = score

            candidate = copy.deepcopy(plan_dict)
            if score < CRITIC_ACCEPT_THRESHOLD and critic.get("edits"):
                candidate = copy.deepcopy(plan_dict)
                if _apply_critic_edits(candidate, critic["edits"]):
                    valid_after, validation_errors_after = _validate_plan_schema(candidate)
                    if valid_after:
                        critic_retry = _critique_plan(llm, candidate, call_suffix=f"{critic_suffix}_retry")
                        if critic_retry is not None:
                            score = int(critic_retry.get("score", score))
                            record["critic_score_retry"] = score
                            if call_meta is not None:
                                call_meta["critic_score_retry"] = score
                        else:
                            candidate = copy.deepcopy(plan_dict)
                    else:
                        candidate = copy.deepcopy(plan_dict)
                        record["critic_validation_errors"] = validation_errors_after
                        if call_meta is not None and validation_errors_after:
                            call_meta["critic_validation_errors"] = validation_errors_after

            if score > best_score:
                best_score = score
                best_plan = candidate
                best_metadata = call_meta

            selected = score >= CRITIC_ACCEPT_THRESHOLD
            record["selected"] = selected
            record["final_score"] = score
            record["schema_version"] = candidate.get("schema_version")
            attempt_records.append(record)

            if selected:
                best_plan = candidate
                best_score = score
                best_metadata = call_meta
                break
        if best_plan and best_score >= CRITIC_ACCEPT_THRESHOLD:
            break

    if best_plan:
        agent_steps = _plan_dict_to_agent_steps(best_plan)
        if agent_steps:
            if best_metadata is not None:
                best_metadata["plan_selected"] = True
                best_metadata["plan_selected_score"] = best_score
            return agent_steps, copy.deepcopy(best_plan), attempt_records
        last_error = "plan_steps_empty"

    attempt_records.append(
        {
            "context": "plan_fallback",
            "error": last_error or "unknown",
        }
    )
    fallback_dict = copy.deepcopy(MINIMAL_FALLBACK_PLAN)
    agent_steps = _plan_dict_to_agent_steps(fallback_dict)
    if not agent_steps:
        agent_steps = [
            AgentStep(
                description="Perform read-only health scan",
                files=[],
                rationale="Fallback plan to keep cadence.",
            )
        ]
    LLM_CALLS.append({
        "context": "plan_fallback",
        "duration_s": 0.0,
        "requested_tokens": 0,
        "granted_tokens": 0,
        "max_tokens": 0,
        "output_len": 0,
        "latency_sensitive": True,
        "plan_budget": _TOKEN_CONTROLLER.snapshot().get("plan_budget"),
        "note": "LLM plan fallback invoked",
        "prior_error": last_error,
    })
    return agent_steps, fallback_dict, attempt_records


def _generate_status_message(llm: Optional["ChatModel"], goal: str, plan: List[AgentStep], applied: bool = False, failed: bool = False) -> str:
    """Ask the model for a short, friendly status line or fall back to a default.

    The message is intended for a tiny status bar: keep it brief and human.
    """
    if failed:
        return "Run completed with errors — see artifacts"
    if llm is None:
        return "Plan prepared" if not applied else "Changes prepared (fastpath)"
    try:
        system = (
            "You produce a SINGLE short status line <= 80 chars for a status bar. "
            "Friendly, human, no quotes, no trailing period."
        )
        steps_txt = ", ".join(s.description for s in plan[:3])
        user = (
            f"Goal: {goal}\n"
            f"Key steps: {steps_txt if steps_txt else 'n/a'}\n"
            f"Outcome: {'applied' if applied else 'planned'}\n"
            "Status line:"
        )
        msg = _call_chat(llm, system, user, max_tokens=STATUS_MAX_TOKENS).strip()
        # Safety: keep it one line and trim hard length
        msg = msg.splitlines()[0][:80]
        return msg or ("Ready" if not applied else "Changes ready")
    except Exception:
        return "Ready"


def _extract_explicit_paths(goal: str) -> List[Path]:
    """Extract file paths mentioned in the goal that exist in this repo.

    Uses a regex to find tokens like README.md, foo/bar.py, config.yaml, etc.,
    including those appearing inside brackets like files: [README.md].
    """
    pattern = re.compile(r"([A-Za-z0-9_./\\-]+\.(?:py|md|yaml|yml))")
    matches = pattern.findall(goal)
    candidates: List[Path] = []
    for m in matches:
        tok = m.replace("\\", "/").strip()
        p = Path(tok)
        if p.is_absolute():
            try:
                p = p.relative_to(ROOT)
            except Exception:
                continue
        if (ROOT / p).exists():
            candidates.append(p)
    # Deduplicate preserving order
    seen: set[Path] = set()
    out: List[Path] = []
    for p in candidates:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _generate_patch(llm: "ChatModel", goal: str, step: AgentStep, path: Path) -> str:
    system_prompt = (
        "You propose minimal patches using the calyx repo's apply_patch format."
    )
    snapshot = _current_file_snapshot(path)
    user_prompt = textwrap.dedent(
        f"""
        Goal: {goal}
        Step description: {step.description}
        Target file: {path.as_posix()}

        Current file content:
        ```
        {snapshot}
        ```

        Produce a patch in apply_patch format. If no change needed, respond with an
        empty string. Do not add explanations, only the patch text.
        """
    ).strip()
    patch = _call_chat(llm, system_prompt, user_prompt, max_tokens=PATCH_MAX_TOKENS, latency_sensitive=False)
    return patch.strip()


def _run_tests(commands: List[str], cwd: Path) -> List[Dict[str, str]]:
    results = []
    for cmd in commands:
        start = time.time()
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": cmd,
                "returncode": str(proc.returncode),
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "duration_s": f"{time.time() - start:.2f}",
            }
        )
    return results


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if _is_mailbox_path(path) and ActionType:
            try:
                rel = path.relative_to(ROOT)
            except Exception:
                rel = path
            _intercept_event(
                action_type=ActionType.MAILBOX_WRITE,
                description=f"Mailbox write -> {rel}",
                surface="mailbox_write",
                payload_meta={"path": str(rel)},
            )
    except Exception:
        pass
    path.write_text(content, encoding="utf-8")


def _write_heartbeat(path: Path, payload: Dict[str, Any]) -> None:
    """Best-effort write of a small JSON heartbeat for GUI/status tools.

    The payload should be a JSON-serializable dict. Errors are swallowed to avoid
    impacting the main agent flow.
    """
    global _HEARTBEAT_INTERCEPTED
    try:
        payload = dict(payload)
        payload["ts"] = time.time()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if ActionType and not _HEARTBEAT_INTERCEPTED:
            try:
                rel = str(path.relative_to(ROOT)) if hasattr(path, "is_relative_to") and path.is_relative_to(ROOT) else str(path)
            except Exception:
                rel = str(path)
            _intercept_event(
                action_type=ActionType.STATE_WRITE,
                description="Heartbeat write",
                surface="state_write",
                payload_meta={"path": rel},
            )
            _HEARTBEAT_INTERCEPTED = True
    except Exception:
        # non-fatal
        pass


# ----------------------------- patch apply helpers ------------------------


DEFAULT_ALLOW_DIRS = [
    "asr",
    "Scripts",
    "tools",
    ".vscode",
    "samples",
]
DEFAULT_ALLOW_FILES = {
    "README.md",
    "OPERATIONS.md",
    "ARCHITECTURE.md",
    "config.yaml",
}


def _is_text(content: bytes) -> bool:
    # Heuristic: reject if NUL bytes present
    return b"\x00" not in content


def _within_whitelist(rel: Path, allow_dirs: List[str], allow_files: List[str]) -> bool:
    if rel.is_absolute():
        try:
            rel = rel.relative_to(ROOT)
        except Exception:
            return False
    parts = rel.parts
    if len(parts) == 1 and parts[0] in allow_files:
        return True
    if parts and parts[0] in allow_dirs:
        return True
    return False


def _read_text_safely(path: Path) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if not _is_text(data):
        raise ValueError(f"Refusing to operate on non-text file: {path}")
    return data.decode("utf-8", errors="ignore")


def _make_unified_diff(old: str, new: str, rel: Path) -> str:
    import difflib

    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel.as_posix()}",
        tofile=f"b/{rel.as_posix()}",
        n=3,
    )
    return "".join(diff)


def _propose_full_file(llm: "ChatModel", goal: str, step: AgentStep, target: Path) -> str:
    """Ask the LLM for the full new content of the target file.

    Returns empty string if no change should be made.
    """
    system_prompt = "You output ONLY raw file content (no fences, no explanations)."
    current = _current_file_snapshot(target, max_chars=12000)
    user_prompt = textwrap.dedent(
        f"""
        Goal: {goal}
        Step: {step.description}
        Target file: {target.as_posix()}

        Current content (may be truncated):
        ```
        {current}
        ```

        Provide the COMPLETE updated file contents. If no change needed, reply with an empty string.
        Do not include backticks or any explanations.
        """
    ).strip()
    proposal = _call_chat(llm, system_prompt, user_prompt, max_tokens=FULL_FILE_MAX_TOKENS, latency_sensitive=False)
    # strip optional code fences if the model ignored instructions
    if proposal.startswith("```"):
        proposal = proposal.strip().strip("`")
        # drop potential language hint on first line
        if "\n" in proposal:
            first, rest = proposal.split("\n", 1)
            if len(first) < 16:  # likely a language hint
                proposal = rest
    return proposal


# ----------------------------- targeted fast-paths ------------------------

TRY_IT_PATTERN = re.compile(r"^##\s*Try it\s*$", re.IGNORECASE | re.MULTILINE)


def _extract_try_it_snippet(goal: str) -> Optional[str]:
    """Extract a fenced powershell block from the goal if present.

    Returns the inner code (without fences) if it matches the expected form.
    """
    # Look for a fenced block labeled powershell
    fence = re.search(r"```powershell\s*\n([\s\S]*?)\n```", goal, re.IGNORECASE)
    if not fence:
        return None
    code = fence.group(1).strip()
    # Minimal sanity: must be a single line "python -u .\\Scripts\\listener_plus.py"
    expected = r"python\s+-u\s+\.\\Scripts\\listener_plus\.py"
    if re.fullmatch(expected, code):
        return code
    return None


def _apply_try_it_fastpath(goal: str, abs_path: Path) -> Optional[str]:
    """If the goal requests updating README.md Try it section, produce new content.

    - Adds a '## Try it' section near the top if missing
    - Replaces existing Try it section with the exact snippet
    - Only operates on README.md; returns None if not applicable
    """
    if abs_path.name.lower() != "readme.md":
        return None

    snippet = _extract_try_it_snippet(goal)
    if snippet is None:
        return None

    try:
        text = abs_path.read_text(encoding="utf-8") if abs_path.exists() else ""
    except Exception:
        return None

    try_it_block = f"## Try it\n\n```powershell\n{snippet}\n```\n"

    # If a Try it section exists, replace the entire section up to the next heading or end
    if TRY_IT_PATTERN.search(text):
        # Replace from the Try it heading through to the next heading or EOF.
        pattern = re.compile(r"^##\s*Try it\s*$[\s\S]*?(?=^##\s|\Z)", re.IGNORECASE | re.MULTILINE)
        replaced = pattern.sub(lambda m: try_it_block, text)
        return replaced
    else:
        # Insert near the top: after the first paragraph or after H1
        # Try to find first blank line after H1
        m = re.match(r"^(# .*$)([\s\S]*)", text)
        if m:
            header = m.group(1)
            rest = m.group(2).lstrip("\n")
            new_text = f"{header}\n\n{try_it_block}\n{rest}"
            return new_text
        else:
            # Fallback: just prepend
            return f"{try_it_block}\n{text}"

    return None


# ----------------------------- main workflow ------------------------------


def run_agent(
    goal: str,
    max_steps: int,
    output_dir: Path,
    generate_patches: bool,
    test_cmds: List[str],
    run_tests: bool,
    model_id: Optional[str],
    apply_changes: bool = False,
    dry_run: bool = False,
    allow_dirs: Optional[List[str]] = None,
    allow_files: Optional[List[str]] = None,
    agent_id: int = 1,
    heartbeat_name: Optional[str] = None,
    publish_bus: bool = False,
    llm_token: Optional[str] = None,
    llm_wait_sec: int = 60,
    llm_optional: bool = False,
) -> AgentRun:
    start_time = time.time()
    entry = get_model_entry(model_id)
    assert_allowed("inference", entry.get("id"))

    # If the goal explicitly targets README Try it and provides an exact snippet,
    # build a minimal deterministic plan and avoid loading the LLM entirely.
    explicit_files = _extract_explicit_paths(goal)
    wants_readme = any(Path(f).name.lower() == "readme.md" for f in explicit_files)
    try_it_snip = _extract_try_it_snippet(goal)

    # Prepare heartbeat writer (multi-agent capable)
    hb_file = heartbeat_name or f"agent{int(agent_id)}.lock"
    hb_path = output_dir / hb_file
    agent_name = f"agent{int(agent_id)}"
    goal_preview = re.sub(r"\s+", " ", (goal or "").strip())[:140]
    run_dir: Optional[Path] = None
    final_status = "error"
    success_flag = False
    global _HEARTBEAT_INTERCEPTED
    _HEARTBEAT_INTERCEPTED = False
    _set_intercept_context(agent_name)
    def hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
        data = {
            "name": agent_name,
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "goal_preview": goal_preview,
        }
        if extra:
            data.update(extra)
        _write_heartbeat(hb_path, data)

    hb("planning", status="running")

    llm: Optional[ChatModel] = None
    token_path: Optional[Path] = None
    plan_raw: Optional[Dict[str, Any]] = None
    plan_attempts: List[Dict[str, Any]] = []
    if wants_readme and try_it_snip is not None and max_steps == 1:
        plan = [
            AgentStep(
                description="Apply requested updates to explicit files from goal",
                files=["README.md"],
                rationale="Deterministic Try it update; no LLM needed.",
            )
        ]
    else:
        # Acquire shared LLM token (optional)
        token_path = _acquire_llm_token(llm_token, wait_sec=int(llm_wait_sec))
        try:
            llm = _ensure_llm(entry["filename"])
            plan, plan_raw, plan_attempts = _generate_plan(llm, goal, max_steps)
        except Exception as exc:
            if not llm_optional:
                raise
            # Fallback: minimal plan without LLM
            llm = None
            plan_raw = copy.deepcopy(MINIMAL_FALLBACK_PLAN)
            plan = _plan_dict_to_agent_steps(plan_raw)
            if not plan:
                plan = [
                    AgentStep(
                        description="Perform read-only health scan",
                        files=[],
                        rationale="Fallback plan to keep cadence.",
                    )
                ]
            plan_attempts = [
                {"context": "llm_unavailable", "error": str(exc) or "llm_unavailable"}
            ]

    # Ensure files explicitly mentioned in the goal are present in plan steps
    goal_files = _extract_explicit_paths(goal)
    injected_files: List[str] = []
    if goal_files:
        wanted = {str(p.as_posix()) for p in goal_files}
        present = set()
        for step in plan:
            present.update(step.files)
        missing = [f for f in wanted if f not in present]
        if missing:
            plan.insert(
                0,
                AgentStep(
                    description="Apply requested updates to explicit files from goal",
                    files=list(missing),
                    rationale="Goal listed exact targets; prioritizing them ensures determinism.",
                ),
            )
            injected_files = list(missing)
            if plan_raw and isinstance(plan_raw.get("steps"), list):
                plan_raw["steps"].insert(
                    0,
                    {
                        "id": "s0_goal_files",
                        "action": "update_files",
                        "target": "",
                        "args": {"files": list(missing)},
                        "rollback": {},
                        "rationale": "Ensure files explicitly mentioned in the goal are handled first.",
                        "files": list(missing),
                    },
                )

    timestamp = int(time.time())
    run_dir = output_dir / f"agent_run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    _set_intercept_context(agent_name, run_dir)
    if ActionType:
        _intercept_event(
            action_type=ActionType.AGENT_SPAWN,
            description=f"Agent spawn (goal='{goal_preview}')",
            surface="agent_spawn",
            payload_meta={
                "heartbeat_file": hb_file,
                "run_dir": str(run_dir.relative_to(ROOT)),
            },
            dry_run=dry_run,
        )

    hb("planning_done", extra={"run_dir": str(run_dir.relative_to(ROOT))})

    # Start per-run memory sampler (writes run_dir/memory_samples.jsonl)
    try:
        sample_interval = int(os.environ.get("CALYX_AGENT_MEM_SAMPLE_SEC", "10"))
    except Exception:
        sample_interval = 30
    try:
        _sampler_stop_event, _sampler_thread = _start_memory_sampler(run_dir, interval=sample_interval)
    except Exception:
        _sampler_stop_event, _sampler_thread = (None, None)

    if plan_attempts:
        attempts_path = run_dir / "planner_attempts.json"
        _write_text(attempts_path, json.dumps(plan_attempts, indent=2))
        for idx, record in enumerate(plan_attempts, start=1):
            raw_text = record.get("raw")
            if raw_text:
                _write_text(run_dir / f"planner_raw_{idx}.txt", raw_text)
            repaired = record.get("repaired")
            if repaired:
                _write_text(
                    run_dir / f"planner_repaired_{idx}.json",
                    json.dumps(repaired, indent=2),
                )

    plan_path = run_dir / "plan.json"
    plan_payload: Dict[str, Any] = {
        "goal": goal,
        "steps": [
            {
                "description": step.description,
                "files": step.files,
                "rationale": step.rationale,
            }
            for step in plan
        ],
    }
    plan_payload["schema_version"] = (
        plan_raw.get("schema_version", PLAN_SCHEMA_VERSION) if plan_raw else PLAN_SCHEMA_VERSION
    )
    if plan_raw:
        plan_payload["plan_raw"] = plan_raw
    _write_text(plan_path, json.dumps(plan_payload, indent=2))

    patches = {}
    # When applying changes, skip separate patch-draft generation to avoid extra LLM round trips
    if generate_patches and not apply_changes and llm is not None:
        for idx, step in enumerate(plan, start=1):
            for file_path in step.files:
                rel = Path(file_path)
                patch_text = _generate_patch(llm, goal, step, ROOT / rel)
                if patch_text:
                    patch_file = run_dir / f"patch_step{idx}_{rel.as_posix().replace('/', '_')}.diff"
                    _write_text(patch_file, patch_text + "\n")
                    patches[str(patch_file.relative_to(run_dir))] = patch_text

    # Apply flow (full-file proposals with backup, diff, test, rollback)
    changed: List[Tuple[Path, str, str]] = []  # (rel_path, old_text, new_text)
    diffs_dir = run_dir / "diffs"
    backup_dir = run_dir / "backup"
    allow_dirs = allow_dirs or DEFAULT_ALLOW_DIRS
    allow_files = allow_files or list(DEFAULT_ALLOW_FILES)

    if apply_changes:
        hb("apply", extra={"run_dir": str(run_dir.relative_to(ROOT))})
        for step in plan:
            for file_path in step.files:
                rel = Path(file_path)
                if rel.is_absolute():
                    try:
                        rel = rel.relative_to(ROOT)
                    except Exception:
                        # skip paths outside repo
                        continue
                if not _within_whitelist(rel, allow_dirs, allow_files):
                    continue
                abs_path = ROOT / rel
                try:
                    old_text = _read_text_safely(abs_path)
                except ValueError:
                    # non-text file, skip
                    continue

                # Fast-path: handle README Try it snippet deterministically without LLM
                proposed = _apply_try_it_fastpath(goal, abs_path)
                if proposed is None and llm is not None:
                    proposed = _propose_full_file(llm, goal, step, abs_path).rstrip("\n")
                if not proposed:
                    continue
                if proposed == old_text.rstrip("\n"):
                    continue
                # record diff
                diff_text = _make_unified_diff(old_text, proposed, rel)
                diffs_dir.mkdir(parents=True, exist_ok=True)
                _write_text(diffs_dir / f"{rel.as_posix().replace('/', '_')}.patch", diff_text)
                # backup
                if not dry_run:
                    backup_target = backup_dir / rel
                    backup_target.parent.mkdir(parents=True, exist_ok=True)
                    if abs_path.exists():
                        _write_text(backup_target, old_text)
                    else:
                        # mark as new file with empty backup
                        _write_text(backup_target, "")
                    # write new content
                    (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
                    _write_text(abs_path, proposed)
                changed.append((rel, old_text, proposed))

    # Compile check + tests if requested
    test_results = []
    failure = False
    if run_tests and test_cmds:
        hb("testing", extra={"run_dir": str(run_dir.relative_to(ROOT))})
        # quick compile check first (narrow scope for speed)
        # Compiling the entire repo can be slow due to non-code folders; focus on code dirs.
        compile_targets = "asr Scripts tools"
        compile_out = _run_tests([f"python -m compileall -q {compile_targets}"], ROOT)
        test_results.extend(compile_out)
        if any(int(r.get("returncode", "1")) != 0 for r in compile_out):
            failure = True
        if not failure:
            more = _run_tests(test_cmds, ROOT)
            test_results.extend(more)
            if any(int(r.get("returncode", "1")) != 0 for r in more):
                failure = True
        tests_path = run_dir / "test_results.json"
        _write_text(tests_path, json.dumps(test_results, indent=2))

    # Rollback if any failure and we actually applied writes
    if apply_changes and not dry_run and (failure):
        for rel, old_text, _ in changed:
            abs_path = ROOT / rel
            if old_text == "" and not (backup_dir / rel).exists():
                # new file: remove it
                try:
                    if abs_path.exists():
                        abs_path.unlink()
                except Exception:
                    pass
            else:
                _write_text(abs_path, old_text)
        _write_text(run_dir / "rollback_report.json", json.dumps({
            "reason": "compile_or_tests_failed",
            "changed_files": [str(c[0]) for c in changed],
        }, indent=2))

    audit = {
        "goal": goal,
        "plan_file": str(plan_path.relative_to(run_dir)),
        "patches": list(patches.keys()),
        "tests": test_results,
        "timestamp": timestamp,
        "model_id": entry.get("id"),
        "model_path": entry.get("filename"),
    "backend": "llama_cpp" if llm is not None else "fastpath",
        "notes": (
            "Applied changes" if (apply_changes and not dry_run and not failure and changed)
            else "Patches are suggestions only; user must review/apply manually."
        ),
        "applied": bool(apply_changes and not dry_run and not failure and changed),
        "dry_run": bool(dry_run),
        "changed_files": [str(c[0]) for c in changed],
        "llm_calls": LLM_CALLS,
        "goal_file_injection": injected_files,
    }
    _write_text(run_dir / "audit.json", json.dumps(audit, indent=2))

    # Final heartbeat
    final_status = "done"
    if apply_changes and not dry_run and failure:
        final_status = "error"
    success_flag = final_status != "error"

    # Generate a status message for the watcher
    try:
        status_message = _generate_status_message(
            llm,
            goal,
            plan,
            applied=bool(apply_changes and not dry_run and not failure and changed),
            failed=bool(failure),
        )
    except Exception:
        status_message = ""

    hb("done", status=final_status, extra={
        "run_dir": str(run_dir.relative_to(ROOT)),
        "applied": audit.get("applied"),
        "changed_files": audit.get("changed_files", []),
        "status_message": status_message,
    })

    # Optional: publish a bus message for digestors (e.g., agent2-4)
    if publish_bus and _bus_publish is not None:
        try:
            _bus_publish(
                producer=agent_name,
                run_dir_rel=str(run_dir.relative_to(ROOT)),
                status=final_status,
                summary={
                    "applied": audit.get("applied"),
                    "changed_files": audit.get("changed_files", []),
                    "status_message": status_message,
                    "goal": goal,
                },
            )
        except Exception:
            pass

    # Metrics: compute and log Tool Efficacy Score (TES) for this run (best-effort)
    # Stop sampler (best-effort) before final metrics collection
    try:
        if isinstance(locals().get("_sampler_stop_event"), threading.Event):
            locals().get("_sampler_stop_event").set()
        if isinstance(locals().get("_sampler_thread"), threading.Thread):
            try:
                locals().get("_sampler_thread").join(timeout=2)
            except Exception:
                pass
    except Exception:
        pass

    try:  # optional; must not fail the run
        sys.path.append(str((ROOT / "tools").resolve()))
        import agent_metrics  # type: ignore
        # Derive autonomy mode
        autonomy_mode = (
            "apply_tests" if (apply_changes and run_tests) else
            "apply" if apply_changes else
            "tests" if run_tests else
            "safe"
        )
        changed_files_count = len(audit.get("changed_files", []))
        duration_s = max(0.0, time.time() - start_time)
        ctx = agent_metrics.RunContext(
            ts=time.time(),
            run_dir=str(run_dir.relative_to(ROOT)),
            duration_s=duration_s,
            status=final_status,
            applied=bool(audit.get("applied")),
            changed_files_count=changed_files_count,
            run_tests=bool(run_tests),
            failure=bool(failure),
            model_id=entry.get("id"),
            autonomy_mode=autonomy_mode,
            agent_id=int(args.agent_id),
        )
        agent_metrics.log_run_metrics(ctx)
    except Exception:
        pass

    # Release LLM token (if held)
    try:
        _release_llm_token(token_path)
    except Exception:
        pass

    if ActionType:
        try:
            _intercept_event(
                action_type=ActionType.AGENT_TERMINATE,
                description="Agent run complete",
                surface="agent_terminate",
                payload_meta={
                    "status": final_status,
                    "run_dir": str(run_dir.relative_to(ROOT)) if isinstance(run_dir, Path) else None,
                    "failure": bool(failure),
                },
                dry_run=dry_run,
            )
        except Exception:
            pass

    return AgentRun(
        goal=goal,
        plan=plan,
        patches=patches,
        tests=test_results,
        success=bool(success_flag),
        model_id=entry.get("id"),
        model_path=entry.get("filename"),
        backend="llama_cpp",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate plan/patch suggestions using local LLM")
    parser.add_argument("--goal", required=False, help="Primary objective for this run")
    parser.add_argument(
        "--goal-file",
        required=False,
        help="Path to a text file whose full contents will be used as the goal (avoids shell quoting issues)",
    )
    parser.add_argument("--max-steps", type=int, default=3, help="Maximum steps in the plan")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for audit bundle")
    parser.add_argument("--skip-patches", action="store_true", help="Do not ask the model for patch drafts")
    parser.add_argument("--run-tests", action="store_true", help="Execute test commands after planning")
    parser.add_argument(
        "--test-cmd",
        action="append",
        default=[],
        help="Shell command to run as part of verification (can be used multiple times)",
    )
    parser.add_argument("--model-id", default=None, help="Override model id from manifest")
    parser.add_argument("--apply", action="store_true", help="Apply proposed changes to allowed files")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files; only generate diffs and reports")
    parser.add_argument("--agent-id", type=int, default=1, help="Agent numeric id for heartbeats (default 1)")
    parser.add_argument("--heartbeat-name", default=None, help="Override heartbeat file base name (e.g., agent1a)")
    parser.add_argument("--publish-bus", action="store_true", help="Publish a message to outgoing/bus for digestors")
    parser.add_argument("--llm-token", default=None, help="Shared LLM token name to serialize LLM usage across agents")
    parser.add_argument("--llm-wait-sec", type=int, default=60, help="Max seconds to wait for LLM token (default 60)")
    parser.add_argument("--llm-optional", action="store_true", help="Proceed without llama-cpp using a minimal fastpath plan")
    parser.add_argument(
        "--allow-dirs",
        action="append",
        default=None,
        help="Additional top-level directories allowed to be modified (can be given multiple times)",
    )
    parser.add_argument(
        "--allow-file",
        action="append",
        default=None,
        help="Additional top-level files allowed to be modified (can be given multiple times)",
    )

    args = parser.parse_args(argv)
    # Ensure Shared Voice channel is active for any joint communications
    try:
        ensure_svf_running(grace_sec=15.0, interval=5.0)
    except Exception:
        pass

    # Allow reading goal from a file to avoid complex shell quoting/escaping
    goal_text = args.goal or ""
    if args.goal_file:
        try:
            goal_text = Path(args.goal_file).read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Failed to read --goal-file '{args.goal_file}': {exc}", file=sys.stderr)
            return 2
    if not goal_text:
        print("Error: a --goal or --goal-file must be provided", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    run = run_agent(
        goal=goal_text,
        max_steps=args.max_steps,
        output_dir=output_dir,
        generate_patches=not args.skip_patches,
        test_cmds=args.test_cmd or ["python tools/test_kws.py"],
        run_tests=args.run_tests,
        model_id=args.model_id,
        apply_changes=args.apply,
        dry_run=args.dry_run,
        allow_dirs=(DEFAULT_ALLOW_DIRS + (args.allow_dirs or [])) if args.allow_dirs is not None else None,
        allow_files=(list(DEFAULT_ALLOW_FILES) + (args.allow_file or [])) if args.allow_file is not None else None,
        agent_id=int(args.agent_id),
        heartbeat_name=args.heartbeat_name,
        publish_bus=bool(args.publish_bus),
        llm_token=args.llm_token,
        llm_wait_sec=int(args.llm_wait_sec),
        llm_optional=bool(args.llm_optional),
    )

    print("Agent run complete.")
    print("Goal:", run.goal)
    print("Plan steps:")
    for idx, step in enumerate(run.plan, start=1):
        print(f"  {idx}. {step.description} -> {', '.join(step.files) if step.files else 'n/a'}")
    print("Output directory:", output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
