"""
Mock LLM runtime for tests and dry runs.
No real LLM; deterministic output from prompt CALL_TOOL markers.
"""
from __future__ import annotations

import json
import re

from ..llm_adapter import LLMResponse, parse_tool_calls_from_json


def _find_calls_in_prompt(prompt: str) -> list[dict]:
    """Parse CALL_TOOL:... from prompt (same as stub agent). Simulates LLM output."""
    out = []
    for m in re.finditer(r"CALL_TOOL:\s*(\{.*?\}|[\w_]+)", prompt, re.DOTALL):
        raw = m.group(1).strip()
        if raw.startswith("{"):
            try:
                obj = json.loads(raw)
                out.append({"name": obj.get("name", ""), "args": obj.get("args", {})})
            except json.JSONDecodeError:
                continue
        else:
            out.append({"name": raw, "args": {}})
    return out


class MockRuntime:
    """Deterministic mock: returns tool calls parsed from prompt. No network."""

    def generate(self, prompt: str, *, seed: int | None = None) -> LLMResponse:
        tool_calls = _find_calls_in_prompt(prompt)
        raw_text = json.dumps({"tool_calls": tool_calls}, ensure_ascii=False)
        parsed, errors = parse_tool_calls_from_json(raw_text)
        return LLMResponse(
            raw_text=raw_text,
            tool_calls=parsed,
            parse_errors=errors,
            model_id="mock",
            backend="local",
            llm_runtime="mock",
        )
