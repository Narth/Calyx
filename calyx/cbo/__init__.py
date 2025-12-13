"""CBO package providing Station Calyx coordination primitives."""

from __future__ import annotations

from .approvals import ApprovalRecord, list_requests, request_approval, set_status
from .bridge_overseer import CBOBridgeOverseer
from .dispatch import TaskDispatcher
from .feedback import FeedbackLoop
from .maintenance import MaintenanceCycle, run_cycle
from .models import Objective, Task, TaskStatus
from .plan_engine import PlanEngine
from .sensors import SensorHub
from .task_store import TaskStore

try:  # Optional FastAPI dependency
    from .api import APP, create_app
except Exception:  # pragma: no cover
    APP = None  # type: ignore[assignment]

    def create_app() -> None:  # type: ignore[override]
        raise RuntimeError("FastAPI not available; install `fastapi` to enable the API service.")


__all__ = [
    "APP",
    "ApprovalRecord",
    "CBOBridgeOverseer",
    "FeedbackLoop",
    "MaintenanceCycle",
    "Objective",
    "PlanEngine",
    "SensorHub",
    "Task",
    "TaskDispatcher",
    "TaskStatus",
    "TaskStore",
    "create_app",
    "list_requests",
    "request_approval",
    "run_cycle",
    "set_status",
]
