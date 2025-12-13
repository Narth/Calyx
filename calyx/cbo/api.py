"""FastAPI bridge exposing CBO coordination endpoints."""

from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .models import TaskStatus
from .sensors import SensorHub
from .task_store import TaskStore
from .tes_analyzer import TesAnalyzer
from .governance import GovernanceMonitor

ROOT = Path(__file__).resolve().parents[2]
APP = FastAPI(title="Station Calyx CBO", version="0.1.0")

OBJECTIVES_PATH = ROOT / "calyx" / "cbo" / "objectives.jsonl"
OBJECTIVES_HISTORY_PATH = ROOT / "calyx" / "cbo" / "objectives_history.jsonl"
CHARTER_PATH = ROOT / "calyx" / "cbo" / "CBO_CHARTER.md"
METRICS_PATH = ROOT / "metrics" / "bridge_pulse.csv"

OBJECTIVES_PATH.parent.mkdir(parents=True, exist_ok=True)
TASK_STORE = TaskStore(ROOT)
SENSOR_HUB = SensorHub(ROOT)
TES_ANALYZER = TesAnalyzer(ROOT)
GOVERNANCE = GovernanceMonitor()


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


class ObjectiveRequest(BaseModel):
    description: str = Field(..., min_length=3)
    priority: int = Field(ge=1, le=10, default=5)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    objective_id: Optional[str] = Field(default=None)


class StatusReport(BaseModel):
    task_id: str = Field(..., min_length=3)
    status: TaskStatus
    agent_id: Optional[str] = None
    notes: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ClaimRequest(BaseModel):
    agent_id: Optional[str] = None


@APP.get("/heartbeat")
def heartbeat() -> Dict[str, Any]:
    """Station gateway health probe."""

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "charter_present": CHARTER_PATH.exists(),
    }


@APP.post("/objective")
def submit_objective(request: ObjectiveRequest) -> Dict[str, Any]:
    """Queue a new objective for the CBO heartbeat to consume."""

    objective_id = request.objective_id or f"obj-{uuid.uuid4().hex[:10]}"
    record = {
        "objective_id": objective_id,
        "description": request.description,
        "priority": request.priority,
        "metadata": request.metadata,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    _append_jsonl(OBJECTIVES_PATH, record)
    _append_jsonl(OBJECTIVES_HISTORY_PATH, record)
    return {"objective_id": objective_id}


@APP.post("/status")
def update_status(report: StatusReport) -> Dict[str, Any]:
    """Record agent task status updates for the feedback loop."""

    updated = TASK_STORE.update_status(
        report.task_id,
        report.status,
        agent_id=report.agent_id,
        notes=report.notes,
        payload=report.payload,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"acknowledged": True, "task": updated}


@APP.post("/claim")
def claim_next(request: ClaimRequest) -> Dict[str, Any]:
    """Allow agents to claim the next available task."""

    task = TASK_STORE.claim_next(request.agent_id)
    if task is None:
        raise HTTPException(status_code=404, detail="No tasks available")
    return {"task": task}


@APP.get("/policy")
def read_policy() -> Dict[str, Any]:
    """Expose current Station policy for agents."""

    policy = SENSOR_HUB.load_policy()
    return {"policy": policy, "retrieved_at": datetime.utcnow().isoformat()}


@APP.get("/report")
def report() -> Dict[str, Any]:
    """Provide lightweight situational awareness from metrics and queues."""

    metrics = _load_metrics(limit=10)
    queue_depth = TASK_STORE.count_active()
    queue_status_counts = TASK_STORE.status_counts()
    status_updates = TASK_STORE.recent_status_updates(limit=20)
    objectives_pending = _count_objectives()
    tes_summary = TES_ANALYZER.compute_summary().as_dict()
    resource_snapshot = GOVERNANCE.resource_snapshot()
    policy = SENSOR_HUB.load_policy()
    registry = SENSOR_HUB.load_registry()
    snapshots = _load_snapshots(limit=5)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "queue_depth": queue_depth,
        "objectives_pending": objectives_pending,
        "queue_status_counts": queue_status_counts,
        "active_tasks": queue_depth,
        "recent_metrics": metrics,
        "recent_status_updates": status_updates,
        "tes_summary": tes_summary,
        "resource_snapshot": resource_snapshot,
        "recent_snapshots": snapshots,
        "registry_size": len(registry),
        "policy_flags": {
            "allow_unregistered_agents": policy.get("allow_unregistered_agents", True),
            "max_cpu_pct": policy.get("max_cpu_pct"),
            "max_ram_pct": policy.get("max_ram_pct"),
        },
    }


def _load_metrics(limit: int = 10) -> List[Dict[str, Any]]:
    if not METRICS_PATH.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with METRICS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    if limit > 0:
        rows = rows[-limit:]
    return rows


@APP.get("/status")
def summarize_status() -> Dict[str, Any]:
    """Summarize task state and latest heartbeat metrics."""

    statuses = TASK_STORE.recent_status_updates(limit=50)
    tes_summary = TES_ANALYZER.compute_summary().as_dict()
    return {
        "count": len(statuses),
        "latest": statuses[-1] if statuses else None,
        "tes_summary": tes_summary,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _count_objectives() -> int:
    if not OBJECTIVES_PATH.exists():
        return 0
    with OBJECTIVES_PATH.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _load_snapshots(limit: int = 5) -> List[Dict[str, Any]]:
    snapshots_path = ROOT / "logs" / "system_snapshots.jsonl"
    if not snapshots_path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with snapshots_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if limit > 0:
        rows = rows[-limit:]
    return rows


def create_app() -> FastAPI:
    """Return FastAPI application instance."""

    return APP


def run() -> None:  # pragma: no cover - runtime helper
    import uvicorn

    uvicorn.run("calyx.cbo.api:APP", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":  # pragma: no cover
    run()
