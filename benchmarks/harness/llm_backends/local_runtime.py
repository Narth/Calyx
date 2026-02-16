"""
Local LLM runtime: Ollama API (with num_predict) or subprocess.
Uses Ollama HTTP API when command is ollama/run so full response is collected
(no token-cap truncation). Fallback: subprocess with prompt via stdin only.
Implements single retry on parse failure with stricter JSON-only instruction.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from ..llm_adapter import LLMResponse, RETRY_REPAIR_PREFIX, parse_tool_calls_from_json


def _use_ollama_api(command: list) -> bool:
    """True if command is ollama run <model> so we can use API with num_predict."""
    if not command or len(command) < 3:
        return False
    c0 = (command[0] or "").lower()
    c1 = (command[1] or "").lower()
    return "ollama" in c0 and c1 == "run"


class LocalRuntime:
    """
    Local LLM: Ollama API (preferred, with num_predict) or subprocess.
    Never constructs command from prompt content.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.model_id = config.get("model_id") or "llama2"
        self.command = config.get("command") or ["ollama", "run", self.model_id]
        self.timeout = int(config.get("timeout", 60))
        self.num_predict = int(config.get("num_predict") or config.get("max_output_tokens") or 512)
        self.ollama_host = (config.get("ollama_host") or "http://127.0.0.1:11434").rstrip("/")
        self._use_api = _use_ollama_api(list(self.command))

    def _generate_via_api(self, prompt: str) -> str:
        """Call Ollama /api/generate with stream=false and num_predict. Returns raw response text."""
        try:
            import urllib.request
            import json as _json
            url = f"{self.ollama_host}/api/generate"
            body = _json.dumps({
                "model": self.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": self.num_predict},
            }).encode("utf-8")
            req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
        except Exception:
            return ""

    def generate(self, prompt: str, *, seed: int | None = None) -> LLMResponse:
        if self._use_api:
            raw_text = self._generate_via_api(prompt)
            if raw_text == "" and "timeout" not in str(raw_text):
                try:
                    import urllib.request
                    urllib.request.urlopen(f"{self.ollama_host}/api/tags", timeout=2)
                except Exception:
                    return LLMResponse(
                        raw_text="",
                        tool_calls=[],
                        parse_errors=["ollama_unreachable"],
                        model_id=self.model_id,
                        backend="local",
                        llm_runtime="ollama_api",
                    )
        else:
            cmd = list(self.command)
            try:
                proc = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.timeout,
                    cwd=Path(__file__).resolve().parents[3],
                )
                raw_text = (proc.stdout or "").strip()
            except subprocess.TimeoutExpired:
                return LLMResponse(
                    raw_text="",
                    tool_calls=[],
                    parse_errors=["timeout"],
                    model_id=self.model_id,
                    backend="local",
                    llm_runtime="subprocess",
                )
            except FileNotFoundError:
                return LLMResponse(
                    raw_text="",
                    tool_calls=[],
                    parse_errors=["command_not_found"],
                    model_id=self.model_id,
                    backend="local",
                    llm_runtime="subprocess",
                )
            except Exception as e:
                return LLMResponse(
                    raw_text="",
                    tool_calls=[],
                    parse_errors=[str(e)],
                    model_id=self.model_id,
                    backend="local",
                    llm_runtime="subprocess",
                )

        if self._use_api and raw_text == "":
            return LLMResponse(
                raw_text="",
                tool_calls=[],
                parse_errors=["empty_response"],
                model_id=self.model_id,
                backend="local",
                llm_runtime="ollama_api",
            )

        tool_calls, parse_errors = parse_tool_calls_from_json(raw_text)
        if parse_errors:
            repair_prompt = RETRY_REPAIR_PREFIX + prompt
            if self._use_api:
                raw_text2 = self._generate_via_api(repair_prompt)
            else:
                try:
                    proc2 = subprocess.run(
                        list(self.command),
                        input=repair_prompt,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=self.timeout,
                        cwd=Path(__file__).resolve().parents[3],
                    )
                    raw_text2 = (proc2.stdout or "").strip()
                except Exception:
                    raw_text2 = ""
            tool_calls2, parse_errors2 = parse_tool_calls_from_json(raw_text2)
            retry_hash = hashlib.sha256(raw_text2.encode("utf-8")).hexdigest() if raw_text2 else None
            if parse_errors2:
                return LLMResponse(
                    raw_text=raw_text,
                    tool_calls=tool_calls,
                    parse_errors=parse_errors,
                    model_id=self.model_id,
                    backend="local",
                    llm_runtime="ollama_api" if self._use_api else "subprocess",
                    llm_attempt_count=2,
                    llm_retry_used=True,
                    llm_retry_parse_ok=False,
                    llm_retry_parse_error="; ".join(parse_errors2),
                    llm_retry_response_hash=retry_hash,
                    raw_retry_text=raw_text2 or None,
                )
            return LLMResponse(
                raw_text=raw_text2,
                tool_calls=tool_calls2,
                parse_errors=[],
                model_id=self.model_id,
                backend="local",
                llm_runtime="ollama_api" if self._use_api else "subprocess",
                llm_attempt_count=2,
                llm_retry_used=True,
                llm_retry_parse_ok=True,
                llm_retry_response_hash=retry_hash,
                raw_retry_text=raw_text2 or None,
            )
        return LLMResponse(
            raw_text=raw_text,
            tool_calls=tool_calls,
            parse_errors=parse_errors,
            model_id=self.model_id,
            backend="local",
            llm_runtime="ollama_api" if self._use_api else "subprocess",
        )
