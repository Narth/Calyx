"""CBO heartbeat loop orchestrating Reflect -> Plan -> Act -> Critique."""

from __future__ import annotations

import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List

from .dispatch import TaskDispatcher
from .feedback import FeedbackLoop
from .governance import GovernanceMonitor
from .models import Objective, PulseReport
from .plan_engine import PlanEngine
from .runtime_paths import get_objectives_path
from .sensors import SensorHub
from .task_store import TaskStore
from .tes_analyzer import TesAnalyzer

# Coordinator integration
try:
    from .coordinator import Coordinator
    COORDINATOR_AVAILABLE = True
except ImportError:
    COORDINATOR_AVAILABLE = False
    Coordinator = None

LOGGER = logging.getLogger("cbo.bridge_overseer")


class ObjectiveSourceEmpty(Exception):
    """Raised when the overseer expected objectives but found none."""


class CBOBridgeOverseer:
    """Main supervisor that executes the CBO operational cycle."""

    def __init__(
        self,
        root: Path,
        *,
        heartbeat_seconds: int = 240,
        objectives_path: Path | None = None,
        metrics_path: Path | None = None,
    ) -> None:
        self.root = root
        self.heartbeat_seconds = heartbeat_seconds
        self.objectives_path = objectives_path or get_objectives_path(root)
        self.objectives_history_path = self.objectives_path.with_name("objectives_history.jsonl")
        self.metrics_path = metrics_path or (root / "metrics" / "bridge_pulse.csv")

        self.sensors = SensorHub(root)
        self.plan_engine = PlanEngine()
        self.task_store = TaskStore(root)
        self.dispatcher = TaskDispatcher(root, task_store=self.task_store)
        self.feedback = FeedbackLoop(task_store=self.task_store)
        self.tes_analyzer = TesAnalyzer(root)
        self.governance = GovernanceMonitor()
        self._loaded_objective_records: list[str] = []
        
        # Initialize coordinator if available
        self.coordinator = None
        if COORDINATOR_AVAILABLE and Coordinator:
            try:
                self.coordinator = Coordinator(root)
                LOGGER.info("Coordinator initialized")
            except Exception as e:
                LOGGER.warning(f"Failed to initialize coordinator: {e}")

        self._ensure_metrics_has_header()

    def run_once(self) -> PulseReport:
        """Perform a single Reflect -> Plan -> Act -> Critique cycle."""

        pulse_started = datetime.utcnow()
        observations = self.sensors.snapshot()
        objectives = self._load_objectives()
        tes_summary = self.tes_analyzer.compute_summary().as_dict()
        observations["tes_summary"] = tes_summary

        planned_tasks = self.plan_engine.build_plan(objectives, observations)
        governance_result = self.governance.evaluate(
            policy=observations.get("policy", {}),
            registry=observations.get("registry", []),
            tasks=planned_tasks,
        )
        observations["governance"] = {
            key: value for key, value in governance_result.items() if key != "tasks"
        }

        adjusted_tasks = governance_result.get("tasks", planned_tasks)
        dispatch_results = []
        if adjusted_tasks and governance_result.get("dispatch_allowed", True):
            dispatch_results = self.dispatcher.dispatch(adjusted_tasks)
        elif adjusted_tasks:
            LOGGER.warning("Dispatch paused due to governance constraints")

        feedback = self.feedback.evaluate(
            dispatch_results,
            state=observations,
            tes_summary=tes_summary,
            governance=governance_result,
        )
        
        # Execute coordinator pulse if available
        coordinator_report = None
        if self.coordinator:
            try:
                coordinator_report = self.coordinator.pulse()
                observations["coordinator"] = coordinator_report
            except Exception as e:
                LOGGER.warning(f"Coordinator pulse failed: {e}")
        
        pulse_completed = datetime.utcnow()
        self._acknowledge_objectives(objectives)

        report = PulseReport(
            pulse_started_at=pulse_started,
            pulse_completed_at=pulse_completed,
            objectives=list(objectives),
            planned_tasks=list(adjusted_tasks),
            dispatch_results=list(dispatch_results),
            observations=observations,
            feedback=feedback,
            governance=governance_result,
            tes_summary=tes_summary,
            metrics_path=self.metrics_path,
        )

        self._log_metrics(report)
        return report

    def run_forever(self) -> None:
        """Continuous heartbeat execution until interrupted."""

        LOGGER.info("Starting CBO bridge overseer heartbeat=%ss", self.heartbeat_seconds)
        try:
            while True:
                started = time.perf_counter()
                report = self.run_once()
                self._log_summary(report)
                elapsed = time.perf_counter() - started
                sleep_for = max(0.0, self.heartbeat_seconds - elapsed)
                if sleep_for:
                    time.sleep(sleep_for)
        except KeyboardInterrupt:
            LOGGER.warning("Bridge overseer interrupted by operator")

    def _load_objectives(self) -> List[Objective]:
        """Read objectives from JSONL, returning an empty list if absent."""

        self._loaded_objective_records = []
        if not self.objectives_path.exists():
            return []

        objectives: List[Objective] = []
        with self.objectives_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = line.strip()
                if not record:
                    continue
                try:
                    data = json.loads(record)
                except json.JSONDecodeError as exc:
                    LOGGER.error("Invalid objective JSON: %s (%s)", record, exc)
                    continue
                objectives.append(self._objective_from_dict(data))
                self._loaded_objective_records.append(record)
        return objectives

    def _objective_from_dict(self, data: dict) -> Objective:
        """Construct Objective while applying defaults."""

        objective_id = str(data.get("objective_id") or data.get("id") or self._fallback_objective_id(data))
        description = str(data.get("description") or data.get("goal") or "unspecified objective")
        priority = int(data.get("priority", 5))
        metadata = data.get("metadata") or {}
        return Objective(objective_id=objective_id, description=description, priority=priority, metadata=metadata)

    def _fallback_objective_id(self, data: dict) -> str:
        """Generate a deterministic identifier for sloppy/manual entries."""

        base = f"{data.get('description','objective')}:{datetime.utcnow().isoformat()}"
        return base.replace(" ", "_").lower()

    def _objective_to_dict(self, objective: Objective) -> dict:
        """Serialize Objective for history logging."""

        return {
            "objective_id": objective.objective_id,
            "description": objective.description,
            "priority": objective.priority,
            "metadata": objective.metadata,
            "created_at": objective.created_at.isoformat(),
        }

    def _acknowledge_objectives(self, objectives: List[Objective]) -> None:
        """Move processed objectives to history and remove them from queue."""

        if not objectives or not self._loaded_objective_records:
            return

        existing_lines: list[str] = []
        if self.objectives_path.exists():
            with self.objectives_path.open("r", encoding="utf-8") as handle:
                existing_lines = [line.strip() for line in handle if line.strip()]

        remaining = existing_lines.copy()
        for record in self._loaded_objective_records:
            try:
                remaining.remove(record)
            except ValueError:
                continue

        with self.objectives_path.open("w", encoding="utf-8") as handle:
            for line in remaining:
                handle.write(line + "\n")

        history_entries = [self._objective_to_dict(obj) for obj in objectives]
        with self.objectives_history_path.open("a", encoding="utf-8") as handle:
            for entry in history_entries:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")

        self._loaded_objective_records = []

    def _ensure_metrics_has_header(self) -> None:
        """Create metrics CSV header if file is empty."""

        if not self.metrics_path.exists():
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
            with self.metrics_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "phase", "status", "details"])
                writer.writeheader()
            return

        if self.metrics_path.stat().st_size == 0:
            with self.metrics_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "phase", "status", "details"])
                writer.writeheader()

    def _log_metrics(self, report: PulseReport) -> None:
        """Append metrics summary for the latest pulse."""

        resource_ok = (report.governance.get("resource") or {}).get("compliant", True)
        policy_ok = (report.governance.get("policy") or {}).get("compliant", True)
        tes_mean = report.tes_summary.get("mean_last_20")
        details = (
            f"objectives={len(report.objectives)} "
            f"tasks={len(report.planned_tasks)} "
            f"dispatched={len(report.dispatch_results)} "
            f"resource_ok={int(bool(resource_ok))} "
            f"policy_ok={int(bool(policy_ok))} "
        )
        if tes_mean is not None:
            details += f"tes_mean20={tes_mean:.1f}"
        row = {
            "timestamp": report.pulse_completed_at.isoformat(),
            "phase": "bridge_pulse",
            "status": report.feedback.get("recommendation", ""),
            "details": details,
        }
        with self.metrics_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "phase", "status", "details"])
            writer.writerow(row)

    def _log_summary(self, report: PulseReport) -> None:
        """Emit a concise summary to the logger."""

        objective_ids = [obj.objective_id for obj in report.objectives]
        LOGGER.info(
            "Pulse completed objectives=%s tasks=%s dispatch=%s feedback=%s",
            objective_ids or "none",
            len(report.planned_tasks),
            len(report.dispatch_results),
            report.feedback.get("recommendation"),
        )


def run_cli() -> None:
    """Entry point for manual launching."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = Path(__file__).resolve().parents[2]
    overseer = CBOBridgeOverseer(root)
    overseer.run_forever()


if __name__ == "__main__":
    run_cli()
