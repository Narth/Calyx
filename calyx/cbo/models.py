"""Shared dataclasses and type hints for the CBO runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class TaskStatus(str, Enum):
    """Lifecycle stages for tasks managed by the CBO dispatcher."""

    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Objective:
    """Manual or autonomous directive the CBO must execute."""

    objective_id: str
    description: str
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Task:
    """Atomic unit of work handed to an agent."""

    task_id: str
    objective_id: str
    action: str
    assignee: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class DispatchRecord:
    """Result of attempting to push a task to an agent."""

    task: Task
    accepted: bool
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class PulseReport:
    """Snapshot produced each heartbeat."""

    pulse_started_at: datetime
    pulse_completed_at: datetime
    objectives: List[Objective]
    planned_tasks: List[Task]
    dispatch_results: List[DispatchRecord]
    observations: Dict[str, Any]
    feedback: Dict[str, Any]
    governance: Dict[str, Any] = field(default_factory=dict)
    tes_summary: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    metrics_path: Optional[Path] = None


def ensure_list(value: Optional[Iterable[Any]]) -> List[Any]:
    """Coerce arbitrary iterables into a list, stripping None."""

    if not value:
        return []
    return [item for item in value if item is not None]
