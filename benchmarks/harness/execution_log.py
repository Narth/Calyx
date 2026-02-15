"""
Execution event logging for autonomous runs.
Append-only JSONL. Schema per CALYX_AUTONOMOUS_GOVERNANCE_SPEC v0.1.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _payload_hash(payload: dict) -> str:
    """Compute SHA256 of canonical JSON (sorted keys), excluding ts_utc for determinism."""
    p = {k: v for k, v in payload.items() if k != "ts_utc"}
    canonical = json.dumps(p, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_event(
    log_path: Path,
    run_id: str,
    stage: str,
    *,
    action_id: str | None = None,
    decision_type: str = "allow",
    adapter_status: str | None = None,
    risk_label: str | None = None,
    risk_score: str | None = None,
    policy_reason: str | None = None,
    payload: dict | None = None,
) -> dict:
    """
    Append one execution event to the log. No buffering. Append-only.
    Returns the event dict as written.
    Phase 2A: supports risk_label, risk_score, policy_reason for risk_evaluation events.
    """
    event_id = str(uuid.uuid4())
    ts_utc = datetime.now(timezone.utc).isoformat()

    event: dict = {
        "event_id": event_id,
        "run_id": run_id,
        "stage": stage,
        "ts_utc": ts_utc,
        "decision_type": decision_type,
    }
    if action_id is not None:
        event["action_id"] = action_id
    if adapter_status is not None:
        event["adapter_status"] = adapter_status
    if risk_label is not None:
        event["risk_label"] = risk_label
    if risk_score is not None:
        event["risk_score"] = risk_score
    if policy_reason is not None:
        event["policy_reason"] = policy_reason

    if payload:
        event.update(payload)
    event["payload_hash"] = _payload_hash(event)

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        f.flush()
        if hasattr(f, "fileno"):
            import os
            os.fsync(f.fileno())

    try:
        import importlib.util
        from pathlib import Path as P
        repo = P(__file__).resolve().parents[2]
        mod_path = repo / "telemetry" / "outbox_mirror.py"
        if mod_path.exists():
            spec = importlib.util.spec_from_file_location("outbox_mirror", mod_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.mirror_event(event, "bench_harness", log_path=log_path)
    except Exception:
        pass

    return event


def compute_execution_log_hash(log_path: Path) -> str:
    """
    Compute SHA256 of canonical execution log.
    Excludes ts_utc and event_id for determinism (same plan => same hash).
    """
    log_path = Path(log_path)
    if not log_path.exists():
        return hashlib.sha256(b"[]").hexdigest()

    exclude_keys = frozenset({"ts_utc", "event_id"})
    events: list[dict] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            canonical_ev = {k: v for k, v in ev.items() if k not in exclude_keys}
            events.append(canonical_ev)

    canonical = json.dumps(events, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
