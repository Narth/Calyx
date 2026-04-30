"""Deterministic cleanup for ephemeral benchmark tmp artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _is_ephemeral_benchmark_tmp(path: Path, runtime_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(runtime_root.resolve())
    except ValueError:
        return False
    if rel.suffix != ".tmp":
        return False
    rel_text = rel.as_posix()
    return rel_text.startswith("benchmarks/results/") or rel_text.startswith("benchmarks/autonomous/")


def collect_ephemeral_tmp_files(runtime_root: Path) -> list[Path]:
    """Return sorted ephemeral benchmark tmp files under runtime_root."""
    runtime_root = Path(runtime_root)
    found = [p for p in runtime_root.rglob("*.tmp") if p.is_file() and _is_ephemeral_benchmark_tmp(p, runtime_root)]
    return sorted(found)


def cleanup_ephemeral_tmp_files(runtime_root: Path) -> dict[str, Any]:
    """Delete ephemeral benchmark tmp files and append an audit log entry."""
    runtime_root = Path(runtime_root)
    tmp_files = collect_ephemeral_tmp_files(runtime_root)
    removed: list[str] = []
    for path in tmp_files:
        path.unlink(missing_ok=True)
        removed.append(str(path))
    log_path = runtime_root / "benchmarks" / "tmp_hygiene.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "action": "cleanup_ephemeral_tmp_files",
        "removed_count": len(removed),
        "removed_files": removed,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"removed_count": len(removed), "removed_files": removed, "log_path": str(log_path)}


def is_excluded_from_verification(path: Path, runtime_root: Path) -> bool:
    """True if the tmp path is an acknowledged ephemeral benchmark artifact."""
    return _is_ephemeral_benchmark_tmp(path, runtime_root)
