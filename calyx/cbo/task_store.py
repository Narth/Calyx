"""Task persistence helpers for the CBO dispatcher and API."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .models import Task, TaskStatus


class TaskStore:
    """Manages the persistent JSONL queue and status log for tasks."""

    def __init__(
        self,
        root: Path,
        *,
        queue_path: Path | None = None,
        status_log_path: Path | None = None,
    ) -> None:
        self.root = root
        self.queue_path = queue_path or (root / "calyx" / "cbo" / "task_queue.jsonl")
        self.status_log_path = status_log_path or (root / "calyx" / "cbo" / "task_status.jsonl")
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.status_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ----- queue management -------------------------------------------------
    def append_tasks(self, tasks: Sequence[Task]) -> None:
        """Persist new tasks to the queue."""

        records = self._load_queue()
        for task in tasks:
            serialized = self._serialize_task(task)
            records.append(serialized)
            self._log_status(task.task_id, task.status, agent_id=task.assignee, payload={"event": "dispatch"})
        self._write_queue(records)

    def claim_next(self, agent_id: Optional[str]) -> Optional[Dict[str, object]]:
        """Mark the next unclaimed task as in progress and return it."""

        records = self._load_queue()
        now = datetime.utcnow().isoformat()
        for record in records:
            if record.get("status") in (TaskStatus.PENDING.value, TaskStatus.DISPATCHED.value):
                record["status"] = TaskStatus.IN_PROGRESS.value
                if agent_id:
                    record["assignee"] = agent_id
                record["claimed_at"] = now
                record["updated_at"] = now
                self._write_queue(records)
                self._log_status(
                    str(record.get("task_id")),
                    TaskStatus.IN_PROGRESS,
                    agent_id=agent_id,
                    payload={"event": "claim"},
                )
                return record
        return None

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        agent_id: Optional[str] = None,
        notes: Optional[str] = None,
        payload: Optional[Dict[str, object]] = None,
    ) -> Optional[Dict[str, object]]:
        """Update a task status and append to the status log."""

        records = self._load_queue()
        updated: Optional[Dict[str, object]] = None
        now = datetime.utcnow().isoformat()
        for record in records:
            if str(record.get("task_id")) == task_id:
                record["status"] = status.value
                record["updated_at"] = now
                if agent_id:
                    record["assignee"] = agent_id
                if payload:
                    record_payload = record.setdefault("payload", {})
                    if isinstance(record_payload, dict):
                        record_payload.update(payload)
                if notes:
                    record["notes"] = notes
                updated = record
                break
        if updated is not None:
            self._write_queue(records)
        self._log_status(task_id, status, agent_id=agent_id, notes=notes, payload=payload)
        return updated

    def status_counts(self) -> Dict[str, int]:
        """Return a count of tasks by status."""

        records = self._load_queue()
        counts: Dict[str, int] = {}
        for record in records:
            status = str(record.get("status") or TaskStatus.PENDING.value)
            counts[status] = counts.get(status, 0) + 1
        return counts

    def count_total(self) -> int:
        """Count all tasks currently in the queue."""

        return len(self._load_queue())

    def count_active(self) -> int:
        """Count tasks that still require attention."""

        records = self._load_queue()
        active_states = {
            TaskStatus.PENDING.value,
            TaskStatus.DISPATCHED.value,
            TaskStatus.IN_PROGRESS.value,
            TaskStatus.FAILED.value,
        }
        return sum(1 for record in records if record.get("status") in active_states)

    def recent_status_updates(self, limit: int = 20) -> List[Dict[str, object]]:
        """Return recent status log entries."""

        entries = self._load_status_log()
        if limit > 0:
            entries = entries[-limit:]
        return entries

    def requeue_failed(self, *, max_retries: int = 3) -> int:
        """Reset failed tasks back to pending for another attempt."""

        records = self._load_queue()
        if not records:
            return 0

        now = datetime.utcnow().isoformat()
        requeued = 0
        updated = False
        for record in records:
            if record.get("status") != TaskStatus.FAILED.value:
                continue

            payload = record.get("payload")
            if not isinstance(payload, dict):
                payload = {}
                record["payload"] = payload

            attempts = int(payload.get("retry_count", 0))
            if attempts >= max_retries:
                continue

            payload["retry_count"] = attempts + 1
            record["status"] = TaskStatus.PENDING.value
            record["updated_at"] = now
            record["assignee"] = None
            record.pop("claimed_at", None)
            updated = True
            requeued += 1

            self._log_status(
                str(record.get("task_id")),
                TaskStatus.PENDING,
                agent_id=None,
                notes="auto-retry",
                payload={"retry_count": payload["retry_count"]},
            )

        if updated:
            self._write_queue(records)
        return requeued

    # ----- internal helpers -------------------------------------------------
    def _load_queue(self) -> List[Dict[str, object]]:
        if not self.queue_path.exists():
            return []
        records: List[Dict[str, object]] = []
        with self.queue_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = line.strip()
                if not entry:
                    continue
                try:
                    records.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
        return records

    def _write_queue(self, records: Iterable[Dict[str, object]]) -> None:
        with self.queue_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _load_status_log(self) -> List[Dict[str, object]]:
        if not self.status_log_path.exists():
            return []
        entries: List[Dict[str, object]] = []
        with self.status_log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = line.strip()
                if not entry:
                    continue
                try:
                    entries.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
        return entries

    def _log_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        agent_id: Optional[str] = None,
        notes: Optional[str] = None,
        payload: Optional[Dict[str, object]] = None,
    ) -> None:
        record = {
            "task_id": task_id,
            "status": status.value,
            "agent_id": agent_id,
            "notes": notes,
            "payload": payload or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        with self.status_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _serialize_task(self, task: Task) -> Dict[str, object]:
        return {
            "task_id": task.task_id,
            "objective_id": task.objective_id,
            "action": task.action,
            "assignee": task.assignee,
            "status": task.status.value,
            "payload": task.payload,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }
