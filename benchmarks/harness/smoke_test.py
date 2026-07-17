"""
Smoke test for LLM adapter (OpenRouter or local).
SMOKE TEST ONLY: one corrective retry on parse failure. Not used for full benchmark cases.
"""
from __future__ import annotations

from .llm_adapter import (
    TOOL_CALL_PROTOCOL_INSTRUCTION,
    wrap_prompt_for_tool_calls,
)

POLICY_BLOCKED_MESSAGE = (
    "OpenRouter privacy policy blocks all endpoints. "
    "Adjust at openrouter.ai/settings/privacy and retry."
)
RATE_LIMIT_MESSAGE = "Recommended wait: 5-10 minutes."


def run_smoke_test(adapter, *, seed: int = 1337, prompt: str = "List files in the current directory."):
    """
    Run wrapper-driven smoke test. One corrective retry if response received but JSON parse fails.
    Returns dict: status (pass|fail|rate-limited|policy-blocked), excerpt (<=200 chars), error (str or list).
    Does not retry on 429 or policy_blocked.
    """
    wrapped = wrap_prompt_for_tool_calls(prompt)
    resp = adapter.generate(wrapped, seed=seed)

    errors = resp.parse_errors or []
    err_str = " ".join(str(e) for e in errors)

    if "429" in err_str or "http_429" in err_str:
        print(RATE_LIMIT_MESSAGE)
        return {
            "status": "rate-limited",
            "excerpt": (resp.raw_text or "")[:200],
            "error": err_str or "http_429",
        }

    if "policy_blocked" in err_str:
        print(POLICY_BLOCKED_MESSAGE)
        return {
            "status": "policy-blocked",
            "excerpt": (resp.raw_text or "")[:200],
            "error": "policy_blocked",
        }

    if not errors and resp.raw_text and (resp.tool_calls is not None):
        return {
            "status": "pass",
            "excerpt": (resp.raw_text or "")[:200],
            "error": "",
        }

    if resp.raw_text and errors:
        corrective = (
            "Your previous response failed to parse as JSON.\n"
            f"Parse error: {errors[0] if errors else 'unknown'}\n\n"
            f"Required schema:\n{TOOL_CALL_PROTOCOL_INSTRUCTION.strip()}\n\n"
            "Output ONLY the JSON object, no prose, no markdown.\n\n"
            f"User request: {prompt}"
        )
        resp2 = adapter.generate(corrective, seed=seed)
        errs2 = resp2.parse_errors or []
        if not errs2 and resp2.raw_text:
            return {
                "status": "pass",
                "excerpt": (resp2.raw_text or "")[:200],
                "error": "",
            }
        return {
            "status": "fail",
            "excerpt": (resp2.raw_text or resp.raw_text or "")[:200],
            "error": " ".join(str(e) for e in errs2) or err_str,
        }

    return {
        "status": "fail",
        "excerpt": (resp.raw_text or "")[:200],
        "error": err_str or "empty_response",
    }
