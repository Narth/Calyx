"""Controlled write helpers for scoped, approved exceptions (reflection-safe defaults).

These helpers still rely on Execution Gate decisions; they enforce path/size limits
before performing any write.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from tools.bloomos_execution_gate import build_action_request, request_action
from tools.calyx_telemetry_logger import new_request_id, new_session_id


class WriteDenied(Exception):
    pass


SUMMARY_MAX_BYTES = 1_000_000  # 1 MB
CACHE_FILE_MAX_BYTES = 1_000_000  # 1 MB per file
CACHE_TOTAL_MAX_BYTES = 20_000_000  # 20 MB total
DRIFT_EVIDENCE_MAX_BYTES = 64_000  # 64 KB
CONTROLLED_WRITES_ENABLED = True  # Set to False to disable all scoped writes quickly.


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_summary_file(
    filename: str,
    content: str,
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Path:
    """Append-only write to outgoing/CBO/summaries/."""
    if not CONTROLLED_WRITES_ENABLED:
        raise WriteDenied("Controlled writes disabled")
    data = content.encode("utf-8")
    if len(data) > SUMMARY_MAX_BYTES:
        raise ValueError("Summary content exceeds 1MB limit.")
    target = Path("outgoing") / "CBO" / "summaries" / filename
    request_id = request_id or new_request_id("summary_write")
    session_id = session_id or new_session_id("summary_write")
    action_req = build_action_request(
        request_id=request_id,
        session_id=session_id,
        node_id="CBO",
        node_role="summarizer",
        capability="filesystem_write",
        action="append_file",
        target={"path": str(target)},
        parameters={"data_size_bytes": len(data)},
        intent="write_summary",
        justification="Persist human-facing summaries in whitelisted path.",
        timestamp=None,
    )
    action_req["allow_summary"] = True
    action_req["timebox_hours"] = timebox_hours

    decision = request_action(action_req)
    if not decision.get("allowed"):
        raise WriteDenied(decision)

    _ensure_dir(target)
    with target.open("ab") as handle:
        handle.write(data)
    return target


def _cache_total_bytes(cache_dir: Path) -> int:
    total = 0
    if cache_dir.exists():
        for p in cache_dir.glob("**/*"):
            if p.is_file():
                total += p.stat().st_size
    return total


def write_cache_file(
    relative_path: str,
    content: str,
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Path:
    """Write/replace a cache file under logs/calyx/cache/ with size limits."""
    if not CONTROLLED_WRITES_ENABLED:
        raise WriteDenied("Controlled writes disabled")
    data = content.encode("utf-8")
    if len(data) > CACHE_FILE_MAX_BYTES:
        raise ValueError("Cache content exceeds per-file 1MB limit.")
    cache_dir = Path("logs") / "calyx" / "cache"
    target = cache_dir / relative_path
    if not str(target).startswith(str(cache_dir)):
        raise ValueError("Cache path must stay under logs/calyx/cache/")

    total_after = _cache_total_bytes(cache_dir) - (target.stat().st_size if target.exists() else 0) + len(data)
    if total_after > CACHE_TOTAL_MAX_BYTES:
        raise ValueError("Cache total size limit exceeded.")

    request_id = request_id or new_request_id("cache_write")
    session_id = session_id or new_session_id("cache_write")
    action_req = build_action_request(
        request_id=request_id,
        session_id=session_id,
        node_id="CBO",
        node_role="summarizer",
        capability="filesystem_write",
        action="replace_file",
        target={"path": str(target)},
        parameters={"data_size_bytes": len(data)},
        intent="write_cache",
        justification="Bounded cache write under logs/calyx/cache/",
        timestamp=None,
    )
    action_req["allow_cache"] = True
    action_req["timebox_hours"] = timebox_hours

    decision = request_action(action_req)
    if not decision.get("allowed"):
        raise WriteDenied(decision)

    _ensure_dir(target)
    with target.open("wb") as handle:
        handle.write(data)
    return target


def write_drift_evidence(
    evidence: Dict[str, Any],
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Path:
    """Append-only drift evidence JSON under logs/calyx/drift_evidence/."""
    if not CONTROLLED_WRITES_ENABLED:
        raise WriteDenied("Controlled writes disabled")
    data = json.dumps(evidence, ensure_ascii=False, indent=2).encode("utf-8")
    if len(data) > DRIFT_EVIDENCE_MAX_BYTES:
        raise ValueError("Drift evidence exceeds 64KB limit.")
    evidence_dir = Path("logs") / "calyx" / "drift_evidence"
    filename = f"drift_evidence_{uuid.uuid4().hex}.json"
    target = evidence_dir / filename
    request_id = request_id or new_request_id("drift_evidence_write")
    session_id = session_id or new_session_id("drift_evidence_write")
    action_req = build_action_request(
        request_id=request_id,
        session_id=session_id,
        node_id="CBO",
        node_role="summarizer",
        capability="filesystem_write",
        action="append_file",
        target={"path": str(target)},
        parameters={"data_size_bytes": len(data)},
        intent="write_drift_evidence",
        justification="Store drift evidence references append-only.",
        timestamp=None,
    )
    action_req["allow_drift_evidence"] = True
    action_req["timebox_hours"] = timebox_hours

    decision = request_action(action_req)
    if not decision.get("allowed"):
        raise WriteDenied(decision)

    _ensure_dir(target)
    with target.open("ab") as handle:
        handle.write(data)
    return target


__all__ = [
    "write_summary_file",
    "write_cache_file",
    "write_drift_evidence",
    "WriteDenied",
]
