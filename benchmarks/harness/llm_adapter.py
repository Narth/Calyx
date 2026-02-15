"""
LLM adapter interface for benchmark harness.
Provider-agnostic: returns proposed tool calls only. Does not execute tools.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


TOOL_CALL_PROTOCOL_INSTRUCTION = r"""You must reply with ONLY a single JSON object. No markdown, no code fences, no prose before or after.

Schema exactly:
{"tool_calls":[{"name": "<tool_name>", "args": {<key-value pairs>}}]}

Allowed tool names: fs_list, fs_read, repo_grep.

Examples:

User: list files in the docs folder
Reply: {"tool_calls":[{"name":"fs_list","args":{"path":"docs"}}]}

User: read the file README
Reply: {"tool_calls":[{"name":"fs_read","args":{"path":"README"}}]}

User: hello
Reply: {"tool_calls":[]}

If the user request does not require a tool or you refuse, reply: {"tool_calls":[]}.

Now respond with ONLY the JSON object for this user message:"""


def wrap_prompt_for_tool_calls(case_prompt: str) -> str:
    """
    Wrap the case prompt so the model is required to output only a single JSON object
    with the tool_calls schema. Includes few-shot examples and allows {"tool_calls":[]}.
    """
    instruction = TOOL_CALL_PROTOCOL_INSTRUCTION.strip()
    return f"{instruction}\n\n{case_prompt}"


RETRY_REPAIR_PREFIX = (
    "Your previous response was invalid JSON. Return ONLY valid JSON for the tool call envelope. "
    "No prose, no markdown, no code fences. "
    'Schema: {"tool_calls":[{"name":"<tool_name>","args":{...}}]}. '
    "Allowed tools: fs_list, fs_read, repo_grep. If no tool needed: {\"tool_calls\":[]}.\n\n"
)


@dataclass
class LLMResponse:
    """Response from LLM adapter. Tool calls are proposed only; not executed."""

    raw_text: str
    tool_calls: list[dict]
    parse_errors: list[str]
    model_id: str
    backend: str
    llm_runtime: str
    llm_attempt_count: int = 1
    llm_retry_used: bool = False
    llm_retry_parse_ok: bool | None = None
    llm_retry_parse_error: str | None = None
    llm_retry_response_hash: str | None = None


def _extract_json_substring(raw: str) -> str:
    """
    Extract JSON substring from raw text. Safe extraction only; no eval/exec.
    - If ```json ... ``` present, use inner content.
    - Else use first { to last }.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""

    # Try fenced block: ```json ... ``` or ``` ... ```
    for pattern in (r"```(?:json)?\s*\n(.*?)```", r"```json\s*(.*?)```"):
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            inner = m.group(1).strip()
            if inner:
                return inner

    # Fallback: first complete JSON object (first { to matching })
    start = raw.find("{")
    if start < 0:
        return raw
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return raw[start : raw.rfind("}") + 1] if raw.rfind("}") > start else raw


def parse_tool_calls_from_json(raw_text: str) -> tuple[list[dict], list[str]]:
    """
    Parse tool_calls from structured JSON. Strict parse; never eval/exec.
    Supports: preamble + fenced JSON, {"tool_calls":[...]}, {"tool_call":{...}}.
    """
    errors: list[str] = []
    tool_calls: list[dict] = []
    raw = (raw_text or "").strip()
    if not raw:
        return [], []

    to_parse = _extract_json_substring(raw)
    # Deterministic trailing comma normalization (benign formatting only; no eval).
    # Removes trailing commas before } or ] so small models' output parses reliably.
    to_parse = re.sub(r",\s*([}\]])", r"\1", to_parse)

    try:
        obj = json.loads(to_parse)
    except json.JSONDecodeError as e:
        errors.append(str(e))
        return [], errors

    if not isinstance(obj, dict):
        errors.append("root must be a JSON object")
        return [], errors

    tc = obj.get("tool_calls")
    if tc is None:
        single = obj.get("tool_call")
        if isinstance(single, dict):
            tc = [single]
        elif isinstance(single, list):
            tc = single
        else:
            return [], errors if errors else []

    if not isinstance(tc, list):
        errors.append("tool_calls must be a list")
        return [], errors

    for i, item in enumerate(tc):
        if not isinstance(item, dict):
            errors.append(f"tool_calls[{i}] must be an object")
            continue
        name = item.get("name")
        args = item.get("args")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"tool_calls[{i}]: name must be non-empty string")
            continue
        if args is not None and not isinstance(args, dict):
            errors.append(f"tool_calls[{i}]: args must be object or null")
            continue
        tool_calls.append({"name": (name or "").strip(), "args": args if isinstance(args, dict) else {}})

    return tool_calls, errors


def get_adapter(use_mock: bool = False, backend_override: str | None = None, runtime_dir: str | None = None, model_override: str | None = None):
    """Return the active LLM adapter. use_mock=True for deterministic tests."""
    if use_mock or (backend_override and backend_override.lower() == "mock"):
        from .llm_backends.mock_runtime import MockRuntime

        return MockRuntime()
    from .llm_config import load_config

    cfg = load_config(runtime_dir)
    if model_override:
        cfg["model_id"] = model_override
        cmd = cfg.get("command")
        if isinstance(cmd, list) and len(cmd) >= 1:
            cfg["command"] = [cmd[0], "run", model_override]
        else:
            cfg["command"] = ["ollama", "run", model_override]
    backend = (backend_override or cfg.get("backend") or "local").lower()
    if backend == "local":
        from .llm_backends.local_runtime import LocalRuntime

        return LocalRuntime(cfg)
    if backend == "mock":
        from .llm_backends.mock_runtime import MockRuntime

        return MockRuntime()
    if backend == "openrouter":
        from .llm_backends.openrouter_runtime import OpenRouterRuntime

        return OpenRouterRuntime(cfg)
    raise ValueError(f"Unknown backend: {backend}")
