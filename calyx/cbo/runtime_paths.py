"""CBO runtime state paths. All CBO JSONL and runtime state live under {CALYX_RUNTIME_DIR}/cbo/."""

from __future__ import annotations

import os
from pathlib import Path


def get_repo_root() -> Path:
    """Repository root (parent of calyx/)."""
    return Path(__file__).resolve().parents[2]


def get_cbo_runtime_dir(root: Path | None = None) -> Path:
    """
    Return the CBO runtime directory: {root}/{CALYX_RUNTIME_DIR}/cbo/.
    CALYX_RUNTIME_DIR defaults to "runtime". Directory is created if missing.
    """
    if root is None:
        root = get_repo_root()
    runtime_dir = os.environ.get("CALYX_RUNTIME_DIR", "runtime")
    cbo_dir = root / runtime_dir / "cbo"
    cbo_dir.mkdir(parents=True, exist_ok=True)
    return cbo_dir


def get_objectives_path(root: Path | None = None) -> Path:
    return get_cbo_runtime_dir(root) / "objectives.jsonl"


def get_objectives_history_path(root: Path | None = None) -> Path:
    return get_cbo_runtime_dir(root) / "objectives_history.jsonl"


def get_sysint_acknowledged_path(root: Path | None = None) -> Path:
    return get_cbo_runtime_dir(root) / "sysint_acknowledged.jsonl"


def get_task_queue_path(root: Path | None = None) -> Path:
    return get_cbo_runtime_dir(root) / "task_queue.jsonl"


def get_task_status_path(root: Path | None = None) -> Path:
    return get_cbo_runtime_dir(root) / "task_status.jsonl"


def get_memory_db_path(root: Path | None = None) -> Path:
    """CBO memory.sqlite path (runtime state)."""
    return get_cbo_runtime_dir(root) / "memory.sqlite"


def runtime_state_resolves_outside_code_tree(root: Path | None = None) -> bool:
    """
    Self-check: CBO runtime dir should be under the runtime root, not under calyx/ or source.
    Returns True if runtime dir is not inside calyx/cbo/ (i.e. state is relocated).
    """
    if root is None:
        root = get_repo_root()
    cbo_runtime = get_cbo_runtime_dir(root)
    try:
        cbo_runtime.resolve().relative_to(root)
    except ValueError:
        return False
    # Resolved path must not be under repo/calyx/cbo (code tree)
    calyx_cbo = (root / "calyx" / "cbo").resolve()
    try:
        cbo_runtime.resolve().relative_to(calyx_cbo)
        return False  # runtime is under calyx/cbo - not relocated
    except ValueError:
        pass
    return True
