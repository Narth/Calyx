"""
Local LLM runtime: subprocess to ollama or similar.
No network. Fixed command; prompt passed via stdin only.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..llm_adapter import LLMResponse, parse_tool_calls_from_json


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
        return LLMResponse(
            raw_text=raw_text,
            tool_calls=tool_calls,
            parse_errors=parse_errors,
            model_id=self.model_id,
            backend="local",
            llm_runtime="subprocess",
        )
