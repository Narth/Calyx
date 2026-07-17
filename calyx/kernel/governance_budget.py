"""
WO_GOVERNANCE_BUDGET_ACCOUNTING_V1 — Log one budget record per governed request at response.finalized.
WO_IDLE_ACTIVITY_GOVERNANCE_V3 — Task budget (gov.budget.task.v1), FE candidate append.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _resolve_repo_root() -> Path:
    import os
    env_root = os.environ.get("CALYX_REPO_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def _budget_path() -> Path:
    """runtime/receipts/budget/governance_budget__YYYYMMDD.jsonl"""
    root = _resolve_repo_root()
    return root / "runtime" / "receipts" / "budget" / f"governance_budget__{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"


def _auth_mode_from_signer(signer_fingerprint: str) -> str:
    if not signer_fingerprint:
        return "none"
    if signer_fingerprint.startswith("gateway:"):
        return "gateway"
    if signer_fingerprint.startswith("key:"):
        return "signature"
    return "none"


def _tool_calls_from_executed(executed_tools: list[str]) -> list[dict[str, Any]]:
    """Convert executed_tools to [{"name": "repo_search", "count": 2}, ...]"""
    counts = Counter(executed_tools or [])
    return [{"name": name, "count": c} for name, c in sorted(counts.items())]


def _load_lifecycle_snapshot() -> dict[str, Any] | None:
    try:
        root = _resolve_repo_root()
        path = root / "runtime" / "station_heartbeat.json"
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("\ufeff"):
            text = text.lstrip("\ufeff")
        data = json.loads(text)
        lifecycle: dict[str, Any] = {}
        for key in (
            "heartbeat_emitted_ts",
            "station_boot_ts",
            "boot_session_id",
            "memory_pressure_tier",
            "service_snapshot_sha256",
            "ingest_group_id",
        ):
            val = data.get(key)
            if val not in (None, "", []):
                lifecycle[key] = val
        return lifecycle or None
    except Exception:
        return None


def write_budget_record(
    *,
    ts_utc: str,
    corr_id: str,
    request_id: str,
    entry_point: str,
    node_id: str,
    auth_mode: str,
    auth_verified: bool,
    signer_fingerprint: str,
    intent: str,
    fastpath_used: bool,
    wall_time_ms: int,
    tool_calls: list[dict],
    tool_calls_total: int,
    claims_attempted: int,
    claims_verified: int,
    claims_failed: int,
    canonical_receipt_written: bool,
    canonical_receipt_path: str,
    equivalence_hash_emitted: bool,
    response_sha256: str,
    equivalence_hash_sha256: str,
    receipt_hash_sha256: str,
    _emit: Any,
    _append_fe: Any,
) -> str | None:
    """
    Write one budget record to governance_budget__YYYYMMDD.jsonl.
    Returns budget_receipt_path on success, None on failure.
    Emits budget.request.recorded; on violation emits budget.violation and appends FE candidate.
    """
    record: dict[str, Any] = {
        "schema": "gov.budget.v1",
        "ts_utc": ts_utc,
        "corr_id": corr_id,
        "request_id": request_id,
        "entry_point": entry_point,
        "node_id": node_id,
        "auth_mode": auth_mode,
        "auth_verified": auth_verified,
        "signer_fingerprint": signer_fingerprint,
        "intent": intent,
        "fastpath_used": fastpath_used,
        "wall_time_ms": wall_time_ms,
        "tool_calls": tool_calls,
        "tool_calls_total": tool_calls_total,
        "claims": {
            "attempted": claims_attempted,
            "verified": claims_verified,
            "failed": claims_failed,
        },
        "receipts": {
            "canonical_receipt_written": canonical_receipt_written,
            "canonical_receipt_path": canonical_receipt_path,
            "equivalence_hash_emitted": equivalence_hash_emitted,
        },
        "hashes": {
            "response_sha256": response_sha256,
            "equivalence_hash_sha256": equivalence_hash_sha256,
            "receipt_hash_sha256": receipt_hash_sha256,
        },
    }
    lifecycle = _load_lifecycle_snapshot()
    if lifecycle:
        record["lifecycle"] = lifecycle

    path = _budget_path()
    violations: list[str] = []

    if tool_calls_total > 25:
        violations.append(f"tool_calls_total={tool_calls_total}>25")
    if wall_time_ms > 60000:
        violations.append(f"wall_time_ms={wall_time_ms}>60000")
    if claims_failed > 0:
        violations.append(f"claims.failed={claims_failed}")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        violations.append(f"budget_write_failed:{str(e)[:100]}")
        try:
            _emit("governance.assertion.failed", "Budget record missing (write failed)", level="WARN", data={"claim_type": "budget_missing", "corr_id": corr_id, "reason": str(e)[:200]})
            _emit("budget.violation", f"Budget record write failed: {e}", level="WARN", data={"corr_id": corr_id, "reason": str(e)[:200]})
            _append_fe("budget_write", corr_id, str(e)[:500], str(path))
        except Exception:
            pass
        return None

    if violations:
        try:
            _emit("budget.violation", f"Budget tripwire: {'; '.join(violations)}", level="WARN", data={"corr_id": corr_id, "violations": violations})
            _append_fe("budget_violation", corr_id, "; ".join(violations), None)
        except Exception:
            pass

    try:
        _emit(
            "budget.request.recorded",
            "Governance budget record written",
            level="INFO",
            data={
                "corr_id": corr_id,
                "budget_receipt_path": str(path),
                "intent": intent,
                "wall_time_ms": wall_time_ms,
                "tool_calls_total": tool_calls_total,
                "claim_failed_count": claims_failed,
            },
        )
    except Exception:
        pass

    return str(path)


# --- WO_IDLE_ACTIVITY_GOVERNANCE_V3: Task budget (gov.budget.task.v1) ---


def _task_budget_path() -> Path:
    """runtime/receipts/budget/task_budget__YYYYMMDD.jsonl"""
    root = _resolve_repo_root()
    return root / "runtime" / "receipts" / "budget" / f"task_budget__{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"


def write_task_budget_record(
    *,
    ts_utc: str,
    task_corr_id: str,
    task_name: str,
    schedule_id: str,
    node_id: str,
    entry_point: str,
    wall_time_ms: int,
    tool_calls: list[dict],
    tool_calls_total: int,
    claims_attempted: int,
    claims_verified: int,
    claims_failed: int,
    outbound_kind: str,
    outbound_destination: str,
    outbound_message_type: str,
    canonical_receipt_written: bool,
    _emit: Any,
) -> str | None:
    """
    Write one task budget record to task_budget__YYYYMMDD.jsonl.
    Returns budget_receipt_path on success, None on failure.
    Emits budget.task.recorded.
    """
    record: dict[str, Any] = {
        "schema": "gov.budget.task.v1",
        "ts_utc": ts_utc,
        "task_corr_id": task_corr_id,
        "task_name": task_name,
        "schedule_id": schedule_id,
        "node_id": node_id,
        "entry_point": entry_point,
        "wall_time_ms": wall_time_ms,
        "tool_calls": tool_calls,
        "tool_calls_total": tool_calls_total,
        "claims": {
            "attempted": claims_attempted,
            "verified": claims_verified,
            "failed": claims_failed,
        },
        "outbound": {
            "kind": outbound_kind,
            "destination": outbound_destination,
            "message_type": outbound_message_type,
        },
        "receipts": {
            "canonical_receipt_written": canonical_receipt_written,
        },
    }
    lifecycle = _load_lifecycle_snapshot()
    if lifecycle:
        record["lifecycle"] = lifecycle

    path = _task_budget_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        try:
            _emit("governance.assertion.failed", "Task budget record write failed", level="WARN", data={"task_corr_id": task_corr_id, "reason": str(e)[:200]})
            _emit("budget.violation", f"Task budget write failed: {e}", level="WARN", data={"task_corr_id": task_corr_id, "reason": str(e)[:200]})
        except Exception:
            pass
        return None

    try:
        _emit(
            "budget.task.recorded",
            "Task budget record written",
            level="INFO",
            data={
                "task_corr_id": task_corr_id,
                "task_name": task_name,
                "budget_receipt_path": str(path),
                "wall_time_ms": wall_time_ms,
                "tool_calls_total": tool_calls_total,
            },
        )
    except Exception:
        pass

    return str(path)


def append_fe_candidate(
    claim_type: str,
    corr_id_or_task_id: str,
    reason: str,
    artifact_path: str | None = None,
    component: str = "unknown",
) -> None:
    """WO_IDLE_ACTIVITY_GOVERNANCE_V3: Append FE candidate on governance violation. Never throws."""
    try:
        root = _resolve_repo_root()
        fe_path = root / "docs" / "operations" / "FAILURE_EVENT_LOG.md"
        if not fe_path.exists():
            return
        content = fe_path.read_text(encoding="utf-8", errors="replace")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        prefix = f"FE-{today}"
        matches = list(re.finditer(r"FE-(\d{4})-(\d{2})-(\d{2})-(\d+)", content))
        max_n = 0
        for m in matches:
            if m.group(0).startswith(prefix):
                max_n = max(max_n, int(m.group(4)))
        parts = today.split("-")
        fe_id = f"FE-{parts[0]}-{parts[1]}-{parts[2]}-{max_n + 1}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d ~%H:%M UTC")
        entry = f"""

---

## {fe_id}: [Auto] governance violation — {claim_type}

| Field | Content |
|-------|---------|
| **ID** | {fe_id} |
| **Timestamp** | {ts} |
| **Component** | {component} |
| **Goal** | WO_IDLE_ACTIVITY_GOVERNANCE_V3: all actions attributable |
| **End Result** | {claim_type} |
| **Root Cause** | {reason[:500]} |
| **Rectification** | Investigate; ensure corr_id or task_corr_id set |
| **Status** | open |
| **Detection Signal** | {claim_type}, id={corr_id_or_task_id[:32]} |
"""
        if artifact_path:
            entry = entry.replace("Investigate;", f"Artifact: {artifact_path[:200]}. Investigate;")
        changelog = "## Changelog"
        if changelog in content:
            idx = content.find(changelog)
            content = content[:idx] + entry + "\n" + content[idx:]
        else:
            content = content.rstrip() + entry + "\n"
        fe_path.write_text(content, encoding="utf-8")
    except Exception:
        pass
