"""
OpenRouter LLM runtime: HTTPS-only, API key from env.
No eval/exec. Raw model text returned to adapter for strict JSON parsing.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

from ..llm_adapter import LLMResponse, parse_tool_calls_from_json

API_BASE = "https://openrouter.ai/api/v1"


class OpenRouterRuntime:
    """
    OpenRouter chat completions API. HTTPS only.
    API key from OPENROUTER_API_KEY env var. Never logged or written to receipts.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.model_id = config.get("model_id") or "meta-llama/llama-3.3-70b-instruct:free"
        self.api_base = (config.get("api_base") or API_BASE).rstrip("/")
        self.temperature = float(config.get("temperature", 0))
        self.top_p = float(config.get("top_p", 1))
        self.max_output_tokens = int(config.get("max_output_tokens", 1024))
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required for OpenRouter backend. "
                "Set it before running. Never store the key in config files."
            )
        self._api_key = api_key

    def generate(self, prompt: str, *, seed: int | None = None) -> LLMResponse:
        url = f"{self.api_base}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_output_tokens,
        }
        if seed is not None:
            payload["seed"] = seed

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=self.timeout_seconds, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = ""
            if e.code == 404 and ("data policy" in err_body.lower() or "settings/privacy" in err_body.lower()):
                return LLMResponse(
                    raw_text="",
                    tool_calls=[],
                    parse_errors=["policy_blocked"],
                    model_id=self.model_id,
                    backend="openrouter",
                    llm_runtime="openrouter",
                )
            try:
                err_obj = json.loads(err_body) if err_body.strip().startswith("{") else {}
                err_msg = err_obj.get("error", {}).get("message", str(e)) or str(e)
            except Exception:
                err_msg = str(e)
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=[f"http_{e.code}: {err_msg}"],
                model_id=self.model_id,
                backend="openrouter",
                llm_runtime="openrouter",
            )
        except urllib.error.URLError as e:
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=[f"url_error: {e.reason}"],
                model_id=self.model_id,
                backend="openrouter",
                llm_runtime="openrouter",
            )
        except TimeoutError:
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=["timeout"],
                model_id=self.model_id,
                backend="openrouter",
                llm_runtime="openrouter",
            )
        except Exception as e:
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=[str(e)],
                model_id=self.model_id,
                backend="openrouter",
                llm_runtime="openrouter",
            )

        raw_text = ""
        if isinstance(data, dict):
            choices = data.get("choices") or []
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message") or choices[0].get("delta", {})
                raw_text = (msg.get("content") or "").strip()
        if not raw_text:
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=["empty_response"],
                model_id=self.model_id,
                backend="openrouter",
                llm_runtime="openrouter",
            )

        tool_calls, parse_errors = parse_tool_calls_from_json(raw_text)
        return LLMResponse(
            raw_text=raw_text,
            tool_calls=tool_calls,
            parse_errors=parse_errors,
            model_id=self.model_id,
            backend="openrouter",
            llm_runtime="openrouter",
        )
