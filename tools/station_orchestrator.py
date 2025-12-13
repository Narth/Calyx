"""Station Orchestrator (reflection-only, manual triggers).

Exposes helpers to:
- run Station Routine v0.2 (basic/extended, intent, health probe)
- perform gated read-only CTL log reads
- perform gated scoped writes (summaries, cache, drift evidence)

No schedulers or background loops are introduced.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from tools.controlled_writes import (
    write_cache_file,
    write_drift_evidence,
    write_summary_file,
    WriteDenied,
)
from tools.log_read_helper import read_ctl_log, LogReadDenied
from tools.station_routine import run_station_routine


def orchestrate_station_routine(
    *,
    mode: str = "extended",
    hours: int = 4,
    intent_text: Optional[str] = None,
    run_health_probe: bool = False,
    include_os_metrics: bool = True,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run Station Routine v0.2 with provided options."""
    return run_station_routine(
        mode=mode,
        hours=hours,
        intent_text=intent_text,
        run_health_probe=run_health_probe,
        include_os_metrics=include_os_metrics,
        request_id=request_id,
        session_id=session_id,
    )


def orchestrate_log_read(
    path: str,
    *,
    bytes_length: Optional[int] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read a CTL log via gated read helper."""
    try:
        return read_ctl_log(
            target_path=path,
            bytes_length=bytes_length,
            request_id=request_id,
            session_id=session_id,
        )
    except LogReadDenied as err:
        return {"error": str(err)}


def orchestrate_write_summary(
    filename: str,
    content: str,
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Dict[str, Any]:
    """Write summary via gated summary helper."""
    try:
        path = write_summary_file(
            filename,
            content,
            request_id=request_id,
            session_id=session_id,
            timebox_hours=timebox_hours,
        )
        return {"path": str(path)}
    except WriteDenied as err:
        return {"error": str(err)}


def orchestrate_write_cache(
    relative_path: str,
    content: str,
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Dict[str, Any]:
    """Write cache via gated cache helper."""
    try:
        path = write_cache_file(
            relative_path,
            content,
            request_id=request_id,
            session_id=session_id,
            timebox_hours=timebox_hours,
        )
        return {"path": str(path)}
    except WriteDenied as err:
        return {"error": str(err)}


def orchestrate_write_drift_evidence(
    evidence: Dict[str, Any],
    *,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    timebox_hours: Optional[int] = 2,
) -> Dict[str, Any]:
    """Write drift evidence via gated helper."""
    try:
        path = write_drift_evidence(
            evidence,
            request_id=request_id,
            session_id=session_id,
            timebox_hours=timebox_hours,
        )
        return {"path": str(path)}
    except WriteDenied as err:
        return {"error": str(err)}


__all__ = [
    "orchestrate_station_routine",
    "orchestrate_log_read",
    "orchestrate_write_summary",
    "orchestrate_write_cache",
    "orchestrate_write_drift_evidence",
]
