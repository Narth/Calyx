"""
Local LLM runtime: subprocess to ollama or similar.
No network. Fixed command; prompt passed via stdin only.
Implements single retry on parse failure with stricter JSON-only instruction.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from ..llm_adapter import LLMResponse, RETRY_REPAIR_PREFIX, parse_tool_calls_from_json


class LocalRuntime:
    """
    Subprocess-based local LLM. Command fixed; prompt passed via stdin.
    Never constructs command from prompt content.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.model_id = config.get("model_id") or "llama2"
        self.command = config.get("command") or ["ollama", "run", self.model_id]
        self.timeout = int(config.get("timeout", 60))

    def generate(self, prompt: str, *, seed: int | None = None) -> LLMResponse:
        # Fixed command; prompt via stdin only. Never prompt in argv.
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

        tool_calls, parse_errors = parse_tool_calls_from_json(raw_text)
        if parse_errors:
            repair_prompt = RETRY_REPAIR_PREFIX + prompt
            try:
                proc2 = subprocess.run(
                    cmd,
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
                    llm_runtime="subprocess",
                    llm_attempt_count=2,
                    llm_retry_used=True,
                    llm_retry_parse_ok=False,
                    llm_retry_parse_error="; ".join(parse_errors2),
                    llm_retry_response_hash=retry_hash,
                )
            return LLMResponse(
                raw_text=raw_text2,
                tool_calls=tool_calls2,
                parse_errors=[],
                model_id=self.model_id,
                backend="local",
                llm_runtime="subprocess",
                llm_attempt_count=2,
                llm_retry_used=True,
                llm_retry_parse_ok=True,
                llm_retry_response_hash=retry_hash,
            )
        return LLMResponse(
            raw_text=raw_text,
            tool_calls=tool_calls,
            parse_errors=parse_errors,
            model_id=self.model_id,
            backend="local",
            llm_runtime="subprocess",
        )
