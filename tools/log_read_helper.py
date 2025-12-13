"""Read-only CTL log helper using Execution Gate test allow for filesystem_read_logs.

Issues a gated request with allow_test=True and, if allowed, performs a read under strict path checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from tools.bloomos_execution_gate import build_action_request, request_action
from tools.calyx_telemetry_logger import new_request_id, new_session_id


class LogReadDenied(Exception):
    pass


def read_ctl_log(
    *,
    target_path: str,
    bytes_length: Optional[int] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    node_id: str = "BLOOMOS_KERNEL",
    node_role: str = "kernel_reflection",
    timebox_hours: Optional[int] = 2,
) -> Dict[str, Any]:
    """Request read-only access to a CTL log and, if allowed, return decision + content sample."""
    if not target_path.startswith("logs/calyx/"):
        raise ValueError("Path must be under logs/calyx/")

    request_id = request_id or new_request_id("log_read_helper")
    session_id = session_id or new_session_id("log_read_helper")

    action_req = build_action_request(
        request_id=request_id,
        session_id=session_id,
        node_id=node_id,
        node_role=node_role,
        capability="filesystem_read_logs",
        action="read_file",
        target={"path": target_path},
        parameters={"bytes_length": bytes_length},
        intent="read_only_ctl_logs_for_summary",
        justification="Enable controlled read-only summaries via Execution Gate test allow.",
        timestamp=None,
    )
    action_req["allow_test"] = True
    action_req["timebox_hours"] = timebox_hours

    decision = request_action(action_req)
    if not decision.get("allowed"):
        raise LogReadDenied(decision)

    path = Path(target_path)
    content = ""
    if path.exists():
        if bytes_length is not None:
            with path.open("rb") as handle:
                content = handle.read(bytes_length).decode("utf-8", errors="replace")
        else:
            # Read a small tail to avoid large payloads
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            content = "\n".join(lines[-20:])

    return {
        "decision": decision,
        "content_sample": content,
    }


__all__ = ["read_ctl_log", "LogReadDenied"]
