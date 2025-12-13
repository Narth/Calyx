"""Translate Station objectives into executable task graphs."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .models import Objective, Task, TaskStatus, ensure_list

LOGGER = logging.getLogger("cbo.plan_engine")


def _normalize_action(description: str) -> str:
    """Produce a concise action label from a full description."""

    fragment = description.strip().split(".")[0]
    fragment = fragment.replace("->", " to ")
    if len(fragment) > 80:
        fragment = fragment[:77].rsplit(" ", 1)[0] + "..."
    return fragment or "unspecified_action"


def _task_id(objective: Objective, suffix: str) -> str:
    """Stable, unique identifier for a task inside an objective."""

    base = f"{objective.objective_id}:{suffix}:{objective.created_at.isoformat()}"
    return hashlib.sha1(base.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


@dataclass(slots=True)
class PlanContext:
    """Material facts used to influence task creation."""

    registry: List[Dict[str, Any]]
    policy: Dict[str, Any]
    metrics: List[Dict[str, Any]]


class PlanEngine:
    """Phase 0/1 planning logic for Station Calyx."""

    def __init__(self, *, default_assignee: str | None = None) -> None:
        self.default_assignee = default_assignee

    def build_plan(
        self,
        objectives: Sequence[Objective],
        state: Dict[str, Any],
    ) -> List[Task]:
        """Convert objectives into actionable tasks."""

        context = PlanContext(
            registry=ensure_list(state.get("registry")),
            policy=state.get("policy", {}),
            metrics=ensure_list(state.get("metrics")),
        )

        plan: List[Task] = []
        for objective in objectives:
            plan.extend(self._decompose_objective(objective, context))
        return plan

    def _decompose_objective(self, objective: Objective, context: PlanContext) -> List[Task]:
        """Minimal decomposition: one primary task per objective."""

        action = _normalize_action(objective.description)
        assignee = self._select_assignee(objective, context)

        task = Task(
            task_id=_task_id(objective, "primary"),
            objective_id=objective.objective_id,
            action=action,
            assignee=assignee,
            status=TaskStatus.PENDING,
            payload={
                "description": objective.description,
                "priority": objective.priority,
                "generated_at": datetime.utcnow().isoformat(),
            },
        )
        LOGGER.debug("Created task %s for objective %s", task.task_id, objective.objective_id)
        return [task]

    def _select_assignee(self, objective: Objective, context: PlanContext) -> Optional[str]:
        """Pick an agent to own the task (round-robin placeholder)."""

        registry = context.registry
        if not registry:
            return self.default_assignee

        # Route by declared skill tags when present
        requested_tags = set(ensure_list(objective.metadata.get("skills")))
        if requested_tags:
            for record in registry:
                tags = set(ensure_list(record.get("skills")))
                if requested_tags.issubset(tags):
                    return record.get("agent_id")

        # Fallback: assume registry order is pre-balanced
        index = int(datetime.utcnow().timestamp()) % len(registry)
        return registry[index].get("agent_id")
