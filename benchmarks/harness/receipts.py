"""
JSONL receipt writer for benchmark runs.
Writes to runtime/benchmarks/results/<suite>/<run_id>.jsonl (or provided path).
No network; filesystem only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone


def prompt_hash(prompt: str) -> str:
    """Stable SHA256 hex of prompt for receipt identity."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def get_git_commit() -> str:
    """Current HEAD commit (short). Empty if not a git repo or error."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parents[2],
        )
        return (out.stdout or "").strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def write_receipt(
    path: Path,
    suite_id: str,
    case_id: str,
    prompt: str,
    system_variant: str,
    tool_calls_attempted: list[dict],
    tool_calls_executed: list[dict],
    decision: str,
    policy_reason: str,
    expected_outcome: str,
    actual_outcome: str,
    pass_fail: bool,
    seed: int,
    run_id: str,
    ts_utc: str | None = None,
    *,
    llm_backend: str | None = None,
    llm_model_id: str | None = None,
    llm_response_hash: str | None = None,
    llm_parse_ok: bool | None = None,
    llm_parse_error: str | None = None,
) -> None:
    """
    Append one JSON receipt line to path. Creates parent dirs if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = ts_utc or datetime.now(timezone.utc).isoformat()
    git_commit = get_git_commit()
    receipt = {
        "schema_version": "1.0",
        "suite_id": suite_id,
        "case_id": case_id,
        "prompt_hash": prompt_hash(prompt),
        "system_variant": system_variant,
        "tool_calls_attempted": tool_calls_attempted,
        "tool_calls_executed": tool_calls_executed,
        "decision": decision,
        "policy_reason": policy_reason,
        "expected_outcome": expected_outcome,
        "actual_outcome": actual_outcome,
        "pass": pass_fail,
        "seed": seed,
        "run_id": run_id,
        "git_commit": git_commit,
        "ts_utc": ts,
    }
    if llm_backend is not None:
        receipt["llm_backend"] = llm_backend
    if llm_model_id is not None:
        receipt["llm_model_id"] = llm_model_id
    if llm_response_hash is not None:
        receipt["llm_response_hash"] = llm_response_hash
    if llm_parse_ok is not None:
        receipt["llm_parse_ok"] = llm_parse_ok
    if llm_parse_error is not None:
        receipt["llm_parse_error"] = llm_parse_error
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, ensure_ascii=False) + "\n")
