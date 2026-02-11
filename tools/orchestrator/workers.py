from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def noop_diff(task_id: str) -> str:
    return f"# {task_id}\n# no-op\n"


def run_test_task(
    task: Dict[str, Any],
    stdout_path: Path,
    stderr_path: Path,
    exit_code: int,
    outcome: str,
    duration_seconds: float,
) -> Dict[str, Any]:
    evidence = {
        "task_id": task["task_id"],
        "role": task["role"],
        "operation": "test",
        "exec": task.get("exec"),
        "args": task.get("args"),
        "outcome": outcome,
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
    }
    write_json(stdout_path.with_suffix(".json"), evidence)
    return {
        "tests": {
            "exec": task.get("exec"),
            "args": task.get("args"),
            "outcome": outcome,
            "exit_code": exit_code,
        },
        "artifacts": [str(stdout_path), str(stderr_path), str(stdout_path.with_suffix(".json"))],
        "files_touched": 0,
    }


def run_noop_task(task: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    diff_path = output_dir / "noop.diff"
    evidence_path = output_dir / "task_result.json"
    write_text(diff_path, noop_diff(task["task_id"]))
    write_json(
        evidence_path,
        {
            "task_id": task["task_id"],
            "role": task["role"],
            "operation": "noop",
            "notes": task.get("notes", ""),
        },
    )
    return {
        "tests": {
            "command": None,
            "outcome": "skipped",
            "reason": "no-op task",
        },
        "artifacts": [str(diff_path), str(evidence_path)],
        "files_touched": 0,
    }


def select_worker(task: Dict[str, Any]) -> str:
    role = task.get("role")
    if role == "test_steward":
        return "test"
    if role in {"refactor_steward", "schema_steward", "docs_steward"}:
        return "noop"
    return "noop"


def ensure_allowed(task: Dict[str, Any], operation: str) -> Optional[str]:
    allowed = set(task.get("allowed_operations", []))
    if operation not in allowed:
        return f"operation '{operation}' not allowed"
    return None


def dispatch_task(
    task: Dict[str, Any],
    output_dir: Path,
    command_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    worker = select_worker(task)
    if worker == "test":
        if ensure_allowed(task, "test"):
            return run_noop_task(task, output_dir)
        if command_result is None:
            return run_noop_task(task, output_dir)
        return run_test_task(
            task,
            Path(command_result["stdout_path"]),
            Path(command_result["stderr_path"]),
            command_result["exit_code"],
            command_result["outcome"],
            command_result["duration_seconds"],
        )
    if ensure_allowed(task, "report") is None or ensure_allowed(task, "read") is None:
        return run_noop_task(task, output_dir)
    return run_noop_task(task, output_dir)
