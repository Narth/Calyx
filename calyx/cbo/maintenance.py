"""Maintenance cycle for Station Calyx repositories."""

from __future__ import annotations

import csv
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import connect
from typing import Dict, List, Optional, Tuple

from .task_store import TaskStore

LOGGER = logging.getLogger("cbo.maintenance")


@dataclass(slots=True)
class MaintenanceResult:
    """Summarised outcome of a maintenance cycle."""

    archived: List[str]
    truncated: List[str]
    requeued: int
    vacuumed: bool
    notes: List[str]

    def as_dict(self) -> Dict[str, object]:
        return {
            "archived": self.archived,
            "truncated": self.truncated,
            "requeued": self.requeued,
            "vacuumed": self.vacuumed,
            "notes": self.notes,
        }


class MaintenanceCycle:
    """Encapsulates repository clean-up and governance housekeeping."""

    def __init__(
        self,
        root: Path,
        *,
        archive_dir: Optional[Path] = None,
        max_jsonl_rows: int = 500,
        max_metrics_rows: int = 1000,
    ) -> None:
        self.root = root
        self.archive_dir = archive_dir or (root / "logs" / "archive")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.max_jsonl_rows = max_jsonl_rows
        self.max_metrics_rows = max_metrics_rows

        cbo_dir = root / "calyx" / "cbo"
        self.queue_path = cbo_dir / "task_queue.jsonl"
        self.status_path = cbo_dir / "task_status.jsonl"
        self.objectives_history_path = cbo_dir / "objectives_history.jsonl"
        self.objectives_path = cbo_dir / "objectives.jsonl"
        self.metrics_path = root / "metrics" / "bridge_pulse.csv"
        self.agent_metrics_path = root / "logs" / "agent_metrics.csv"
        self.memory_db_path = cbo_dir / "memory.sqlite"
        self.task_store = TaskStore(root)

    # ------------------------------------------------------------------ public API
    def run(self) -> MaintenanceResult:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived: List[str] = []
        truncated: List[str] = []
        notes: List[str] = []

        for path in (
            self.queue_path,
            self.status_path,
            self.objectives_history_path,
            self.objectives_path,
        ):
            archive_made, truncated_file = self._prune_jsonl(path, self.max_jsonl_rows, timestamp)
            if archive_made:
                archived.append(archive_made)
            if truncated_file:
                truncated.append(truncated_file)

        metrics_archive, metrics_truncated = self._prune_csv(self.metrics_path, self.max_metrics_rows, timestamp)
        if metrics_archive:
            archived.append(metrics_archive)
        if metrics_truncated:
            truncated.append(metrics_truncated)

        # Keep agent metrics manageable (they can grow quickly)
        agent_archive, agent_truncated = self._prune_csv(self.agent_metrics_path, 2000, timestamp)
        if agent_archive:
            archived.append(agent_archive)
        if agent_truncated:
            truncated.append(agent_truncated)

        requeued = self.task_store.requeue_failed()
        if requeued:
            notes.append(f"auto-requeued {requeued} task(s)")

        vacuumed = self._vacuum_sqlite(self.memory_db_path)

        notes.extend(self._summarise_counts())

        return MaintenanceResult(archived=archived, truncated=truncated, requeued=requeued, vacuumed=vacuumed, notes=notes)

    # ------------------------------------------------------------------ helpers
    def _prune_jsonl(self, path: Path, keep: int, timestamp: str) -> Tuple[Optional[str], Optional[str]]:
        if not path.exists() or keep <= 0:
            return (None, None)

        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= keep:
            return (None, None)

        archive_name = path.name + f".{timestamp}"
        archive_path = self.archive_dir / archive_name
        shutil.copy2(path, archive_path)
        retained = lines[-keep:]
        path.write_text("\n".join(retained) + "\n", encoding="utf-8")
        LOGGER.info("Pruned %s to last %d records", path, keep)
        return (str(archive_path), str(path))

    def _prune_csv(self, path: Path, keep: int, timestamp: str) -> Tuple[Optional[str], Optional[str]]:
        if not path.exists() or keep <= 0:
            return (None, None)

        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        if len(rows) <= keep + 1:  # account for header
            return (None, None)

        header, data = rows[0], rows[1:]
        retained = data[-keep:]

        archive_name = path.name + f".{timestamp}"
        archive_path = self.archive_dir / archive_name
        shutil.copy2(path, archive_path)

        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(retained)
        LOGGER.info("Pruned %s to last %d rows", path, keep)
        return (str(archive_path), str(path))

    def _vacuum_sqlite(self, db_path: Path) -> bool:
        if not db_path.exists() or db_path.stat().st_size == 0:
            return False
        try:
            with connect(db_path) as conn:
                conn.execute("VACUUM")
            LOGGER.info("VACUUM executed on %s", db_path)
            return True
        except Exception as exc:  # pragma: no cover - defensive, runtime only
            LOGGER.warning("Unable to VACUUM %s: %s", db_path, exc)
            return False

    def _summarise_counts(self) -> List[str]:
        notes: List[str] = []
        for path in (self.queue_path, self.status_path, self.objectives_history_path):
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    count = sum(1 for _ in handle if _.strip())
                notes.append(f"{path.name}: {count} entries")
            except Exception as exc:  # pragma: no cover
                LOGGER.debug("Failed counting %s: %s", path, exc)
        return notes


def run_cycle(root: Path) -> MaintenanceResult:
    """Convenience helper for CLI usage."""

    cycle = MaintenanceCycle(root)
    return cycle.run()
