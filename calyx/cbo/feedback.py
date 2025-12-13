"""Feedback loop that inspects execution results and suggests adjustments."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, List

from .models import DispatchRecord, TaskStatus, ensure_list
from .task_store import TaskStore

LOGGER = logging.getLogger("cbo.feedback")


class FeedbackLoop:
    """Phase 1 feedback: track failures, TES trends, and policy compliance."""

    def __init__(self, task_store: TaskStore | None = None) -> None:
        self.task_store = task_store

    def evaluate(
        self,
        dispatch_results: Iterable[DispatchRecord],
        *,
        state: Dict[str, Any],
        tes_summary: Optional[Dict[str, Any]] = None,
        governance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Summarize recent execution outcomes."""

        records = list(dispatch_results)
        status_counts = Counter(record.task.status for record in records)
        registry = ensure_list(state.get("registry"))

        feedback = {
            "evaluated_at": datetime.utcnow().isoformat(),
            "dispatch_status_counts": {status.value: count for status, count in status_counts.items()},
            "registry_size": len(registry),
        }

        action_required = False
        actions: List[str] = []

        failed_dispatches = status_counts.get(TaskStatus.FAILED, 0)
        total_failed = failed_dispatches

        if self.task_store:
            queue_counts = self.task_store.status_counts()
            feedback["queue_status_counts"] = queue_counts
            feedback["active_tasks"] = self.task_store.count_active()
            total_failed += queue_counts.get(TaskStatus.FAILED.value, 0)

        if total_failed:
            action_required = True
            actions.append("Requeue failed tasks and alert overseer")
            LOGGER.warning("Detected %d failed task(s)", total_failed)

        if tes_summary:
            feedback["tes_summary"] = tes_summary
            if tes_summary.get("trend") == "declining":
                action_required = True
                actions.append("TES trending downward; investigate agent performance")

        if governance:
            feedback["governance"] = governance
            resource_info = governance.get("resource") or {}
            policy_info = governance.get("policy") or {}
            if not resource_info.get("compliant", True):
                action_required = True
                notes = resource_info.get("notes") or []
                actions.append("Resource limits exceeded; pause dispatch until usage declines")
                if notes:
                    feedback.setdefault("governance_notes", []).extend(notes)
            if not policy_info.get("compliant", True):
                action_required = True
                actions.append("Policy violation detected; review unregistered assignments")

        feedback["action_required"] = action_required
        if action_required and actions:
            feedback["recommendation"] = "; ".join(actions)
        elif action_required:
            feedback["recommendation"] = "Attention required"
        else:
            feedback["recommendation"] = "Continue monitoring"

        return feedback
