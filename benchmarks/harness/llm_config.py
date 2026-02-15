"""
LLM config loader. Reads from runtime/llm_config.json (git-ignored).
User must copy benchmarks/llm_config.example.json to runtime/llm_config.json.
"""
from __future__ import annotations

import json
from pathlib import Path

# Default config when no file exists
_DEFAULT = {
    "backend": "local",
    "model_id": "llama2",
    "command": ["ollama", "run", "llama2"],
    "temperature": 0.0,
    "top_p": 1.0,
    "timeout": 60,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(runtime_dir: str | Path | None = None) -> dict:
    """
    Load LLM config from runtime/llm_config.json.
    Falls back to default if file missing or invalid.
    """
    root = _repo_root()
    rt = Path(runtime_dir) if runtime_dir else root / "runtime"
    path = rt / "llm_config.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                out = _DEFAULT.copy()
                out.update(cfg)
                return out
        except (json.JSONDecodeError, OSError):
            pass
    return _DEFAULT.copy()
