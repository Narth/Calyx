"""Helpers for staging-only operator intervention receipts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from staging.work.runtime_capture_adapter.models import RuntimeCaptureClassificationResult
from staging.work.runtime_operator_intervention.models import (
    InterventionActionTaken,
    InterventionCommandRecord,
    InterventionDecisionFramework,
    InterventionEvidenceRef,
    InterventionObservedProcess,
    InterventionSafetyConstraints,
    InterventionTriggeringConditions,
    RuntimeOperatorIntervention,
)
from staging.work.runtime_operator_summary.models import RuntimeOperatorSummary


PROTECTED_PROCESS_NAMES = {
    "system",
    "client server runtime process",
    "csrss.exe",
    "wmiprvse.exe",
    "windows management instrumentation",
}

BLIND_KILL_PATTERNS = (
    "stop-process -name python",
    "stop-process -name node",
    "taskkill /im python.exe",
    "taskkill /im node.exe",
    "pkill python",
    "pkill node",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _contains_blind_kill(commands: Iterable[str]) -> bool:
    lowered = [item.lower() for item in commands]
    return any(pattern in command for command in lowered for pattern in BLIND_KILL_PATTERNS)


def _normalize_processes(processes: list[InterventionObservedProcess | dict]) -> list[InterventionObservedProcess]:
    return [
        item if isinstance(item, InterventionObservedProcess) else InterventionObservedProcess.model_validate(item)
        for item in processes
    ]


def _protected_names(processes: Iterable[InterventionObservedProcess]) -> list[str]:
    names = []
    for process in processes:
        if process.process_name.lower() in PROTECTED_PROCESS_NAMES:
            names.append(process.process_name)
    return sorted(set(names))


def _derive_station_attribution(summary: RuntimeOperatorSummary) -> str:
    if not summary.station_runtime_view.processes:
        return "no"
    governed_pids = {item.pid for item in summary.station_runtime_view.processes}
    top_pids = {item.pid for item in summary.top_processes if item.pid is not None}
    if not top_pids:
        return "unknown"
    if governed_pids & top_pids:
        return "yes"
    return "no"


def build_intervention_receipt(
    *,
    summary: RuntimeOperatorSummary,
    classification: RuntimeCaptureClassificationResult,
    intervention_id: str,
    intervention_tier: str,
    action_type: str,
    operator_reasoning: str,
    observed_processes: list[InterventionObservedProcess | dict],
    commands_executed: list[str] | None = None,
    notes: str | None = None,
    protected_process_override_acknowledged: bool = False,
    protected_process_override_reason: str | None = None,
    extra_evidence_refs: list[InterventionEvidenceRef] | None = None,
    timestamp_utc: datetime | None = None,
) -> RuntimeOperatorIntervention:
    commands_executed = commands_executed or []
    normalized_processes = _normalize_processes(observed_processes)
    command_records = [InterventionCommandRecord(command=item) for item in commands_executed]
    process_ids = [item.pid for item in normalized_processes]
    process_names = sorted({item.process_name for item in normalized_processes})
    blind_kill_detected = _contains_blind_kill(commands_executed)
    protected_names = _protected_names(normalized_processes)

    action = InterventionActionTaken(
        action_type=action_type,
        relevant_process_ids=process_ids,
        relevant_process_names=process_names,
        commands_executed=command_records,
        command_execution_performed=bool(command_records),
        notes=notes,
    )

    evidence = [
        InterventionEvidenceRef(
            artifact_type="runtime.operator.summary",
            artifact_ref=summary.summary_id,
            notes="Operator summary reviewed before intervention.",
        ),
        InterventionEvidenceRef(
            artifact_type="runtime.capture.classification_result",
            artifact_ref=classification.capture_id,
            notes="Classification result reviewed before intervention.",
        ),
        InterventionEvidenceRef(
            artifact_type="runtime.capture.input",
            artifact_ref=classification.capture_id,
            notes="Raw capture associated with the reviewed summary.",
        ),
    ]
    if extra_evidence_refs:
        evidence.extend(extra_evidence_refs)

    return RuntimeOperatorIntervention(
        schema_name="runtime.operator.intervention",
        schema_version="1.0.0",
        intervention_id=intervention_id,
        corr_id=summary.corr_id,
        capture_id=summary.capture_id,
        summary_id=summary.summary_id,
        timestamp_utc=timestamp_utc or _utc_now(),
        intervention_tier=intervention_tier,
        triggering_conditions=InterventionTriggeringConditions(
            system_load_condition=summary.system_load_condition,
            governance_compliance_condition=summary.governance_compliance_condition,
            operator_signal=summary.operator_risk_signal,
            load_attributable_to_station=_derive_station_attribution(summary),
            behavior_expected="yes" if summary.operator_risk_signal == "NORMAL" else "no",
        ),
        decision_framework=InterventionDecisionFramework(
            load_elevated="yes" if summary.system_load_condition in {"elevated", "high"} else "no",
            station_attribution_clear="no" if summary.attribution_gaps else "yes",
            governance_compliant="yes" if summary.governance_compliance_condition == "compliant" else "no",
            behavior_expected="yes" if summary.operator_risk_signal == "NORMAL" else "no",
            action_threshold_met=summary.operator_risk_signal in {"UNEXPECTED", "RISK", "CRITICAL"},
            notes="Derived from runtime.operator.summary without introducing new authority.",
        ),
        observed_evidence=evidence,
        observed_processes=normalized_processes,
        action_taken=action,
        operator_reasoning=operator_reasoning,
        safety_constraints=InterventionSafetyConstraints(
            protected_process_targets_present=bool(protected_names),
            protected_process_names=protected_names,
            protected_process_override_acknowledged=protected_process_override_acknowledged,
            protected_process_override_reason=protected_process_override_reason,
            broad_kill_pattern_detected=blind_kill_detected,
            broad_kill_pattern_blocked=blind_kill_detected,
            safety_notes=[
                "Manual-only protocol. No runtime action is initiated by the system.",
                "Blind kill patterns are blocked at schema-validation time.",
            ],
        ),
        notes=notes,
    )


def load_summary(path: Path) -> RuntimeOperatorSummary:
    return RuntimeOperatorSummary.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_classification(path: Path) -> RuntimeCaptureClassificationResult:
    return RuntimeCaptureClassificationResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def build_intervention_receipt_from_paths(
    *,
    summary_path: Path,
    classification_path: Path,
    intervention_id: str,
    intervention_tier: str,
    action_type: str,
    operator_reasoning: str,
    observed_processes: list[InterventionObservedProcess | dict],
    commands_executed: list[str] | None = None,
    notes: str | None = None,
    protected_process_override_acknowledged: bool = False,
    protected_process_override_reason: str | None = None,
    timestamp_utc: datetime | None = None,
) -> RuntimeOperatorIntervention:
    return build_intervention_receipt(
        summary=load_summary(summary_path),
        classification=load_classification(classification_path),
        intervention_id=intervention_id,
        intervention_tier=intervention_tier,
        action_type=action_type,
        operator_reasoning=operator_reasoning,
        observed_processes=observed_processes,
        commands_executed=commands_executed,
        notes=notes,
        protected_process_override_acknowledged=protected_process_override_acknowledged,
        protected_process_override_reason=protected_process_override_reason,
        timestamp_utc=timestamp_utc,
    )
