"""Policy and resource compliance checks for Station Calyx."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from .models import Task

LOGGER = logging.getLogger("cbo.governance")

try:  # Optional dependency
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore


class GovernanceMonitor:
    """Validates policy compliance and resource limits before dispatch."""

    def resource_snapshot(self) -> Dict[str, Any]:
        """Return current CPU and RAM usage."""

        if not psutil:
            return {"cpu_pct": None, "ram_pct": None, "psutil_available": False}

        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem_pct = psutil.virtual_memory().percent
            return {
                "cpu_pct": float(cpu_pct),
                "ram_pct": float(mem_pct),
                "psutil_available": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Failed to collect resource snapshot: %s", exc)
            return {"cpu_pct": None, "ram_pct": None, "psutil_available": False}

    def evaluate(
        self,
        *,
        policy: Dict[str, Any],
        registry: Iterable[Dict[str, Any]],
        tasks: Iterable[Task],
    ) -> Dict[str, Any]:
        """Return compliance summary and optionally adjust outgoing tasks."""

        resource_snapshot = self.resource_snapshot()
        cpu_limit = self._parse_limit(policy.get("max_cpu_pct"), default=100.0)
        ram_limit = self._parse_limit(policy.get("max_ram_pct"), default=100.0)

        resource_notes: List[str] = []
        resource_compliant = True
        cpu_pct = resource_snapshot.get("cpu_pct")
        if self._exceeds(cpu_pct, cpu_limit):
            resource_compliant = False
            resource_notes.append(f"CPU usage {cpu_pct:.1f}% exceeds limit {cpu_limit:.1f}%")

        ram_pct = resource_snapshot.get("ram_pct")
        if self._exceeds(ram_pct, ram_limit):
            resource_compliant = False
            resource_notes.append(f"RAM usage {ram_pct:.1f}% exceeds limit {ram_limit:.1f}%")

        allow_unregistered = bool(policy.get("allow_unregistered_agents", True))
        registered_ids = self._registered_ids(registry)

        adjusted_tasks: List[Task] = []
        unregistered_assignments: List[Dict[str, Any]] = []

        for task in tasks:
            candidate = task
            if not allow_unregistered and task.assignee:
                if task.assignee not in registered_ids:
                    unregistered_assignments.append(
                        {
                            "task_id": task.task_id,
                            "assignee": task.assignee,
                        }
                    )
                    candidate = replace(task, assignee=None)
            adjusted_tasks.append(candidate)

        policy_compliant = not unregistered_assignments
        if unregistered_assignments:
            LOGGER.warning("Cleared assignees for %d task(s) lacking registry match", len(unregistered_assignments))

        dispatch_allowed = resource_compliant

        return {
            "resource": {
                "compliant": resource_compliant,
                "cpu_limit": cpu_limit,
                "ram_limit": ram_limit,
                "snapshot": resource_snapshot,
                "notes": resource_notes,
            },
            "policy": {
                "compliant": policy_compliant,
                "allow_unregistered_agents": allow_unregistered,
                "unregistered_assignments": unregistered_assignments,
            },
            "dispatch_allowed": dispatch_allowed,
            "tasks": adjusted_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _parse_limit(value: Any, *, default: float) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _exceeds(value: Any, limit: float) -> bool:
        try:
            if value is None:
                return False
            return float(value) > limit
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _registered_ids(registry: Iterable[Dict[str, Any]]) -> Set[str]:
        ids: Set[str] = set()
        for record in registry:
            ident = record.get("agent_id")
            if ident:
                ids.add(str(ident))
        return ids
