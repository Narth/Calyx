"""Task dispatcher responsible for handing work to downstream agents."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

from .models import DispatchRecord, Task, TaskStatus
from .task_store import TaskStore

LOGGER = logging.getLogger("cbo.dispatch")


class TaskDispatcher:
    """Phase 1 dispatcher writing queue entries to JSONL for agents to ingest."""

    def __init__(
        self,
        root: Path,
        *,
        queue_path: Path | None = None,
        audit_path: Path | None = None,
        task_store: TaskStore | None = None,
        status_log_path: Path | None = None,
    ) -> None:
        self.root = root
        self.audit_path = audit_path or (root / "logs" / "cbo_dispatch.log")
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = task_store or TaskStore(
            root,
            queue_path=queue_path,
            status_log_path=status_log_path,
        )

    def dispatch(self, tasks: Sequence[Task]) -> List[DispatchRecord]:
        """Persist tasks to the queue for agents to claim."""

        records: List[DispatchRecord] = []
        if not tasks:
            return records

        prepared: List[Task] = []
        for task in tasks:
            updated_task = replace(task, status=TaskStatus.DISPATCHED, updated_at=datetime.utcnow())
            prepared.append(updated_task)
            records.append(DispatchRecord(task=updated_task, accepted=True, notes="queued"))

        # Persist first, then audit only on success
        try:
            self.store.append_tasks(prepared)
            LOGGER.info("Dispatched %d task(s) to %s", len(records), self.store.queue_path)
            # Audit after successful persistence
            for task in prepared:
                self._log_audit(task)
        except Exception as exc:
            LOGGER.error("Failed to persist tasks: %s", exc, exc_info=True)
            # Mark all records as failed
            for record in records:
                record.accepted = False
                record.notes = f"persistence failed: {exc}"
        return records

    def _log_audit(self, task: Task) -> None:
        """Append a human-friendly note for operators."""

        message = (
            f"{datetime.utcnow().isoformat()} task={task.task_id} "
            f"objective={task.objective_id} assignee={task.assignee or 'unassigned'} "
            f"status={task.status.value}"
        )
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
