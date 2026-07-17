"""Typed models for manual, receipt-backed runtime operator interventions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


RUNTIME_OPERATOR_INTERVENTION_SCHEMA_VERSION = "1.0.0"

InterventionTier = Literal["tier_0_observe", "tier_1_soft_intervention", "tier_2_hard_intervention"]
OperatorSignal = Literal["NORMAL", "ELEVATED", "UNEXPECTED", "RISK", "CRITICAL"]
SystemLoadCondition = Literal["normal", "elevated", "high", "unknown"]
GovernanceComplianceCondition = Literal["compliant", "ambiguous", "noncompliant", "critical"]
ActionType = Literal[
    "observe_only",
    "inspect_process",
    "terminate_process",
    "terminate_multiple_processes",
    "stop_station_services",
    "halt_station_activity",
    "restart_machine",
]
EvidenceArtifactType = Literal[
    "runtime.operator.summary",
    "runtime.capture.input",
    "runtime.capture.classification_result",
    "runtime_governance_bundle",
]
SafetyDecision = Literal["yes", "no", "unknown"]


class StrictRuntimeOperatorInterventionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InterventionTriggeringConditions(StrictRuntimeOperatorInterventionModel):
    system_load_condition: SystemLoadCondition
    governance_compliance_condition: GovernanceComplianceCondition
    operator_signal: OperatorSignal
    load_attributable_to_station: SafetyDecision
    behavior_expected: SafetyDecision


class InterventionDecisionFramework(StrictRuntimeOperatorInterventionModel):
    load_elevated: SafetyDecision
    station_attribution_clear: SafetyDecision
    governance_compliant: SafetyDecision
    behavior_expected: SafetyDecision
    action_threshold_met: bool
    notes: str | None = None


class InterventionEvidenceRef(StrictRuntimeOperatorInterventionModel):
    artifact_type: EvidenceArtifactType
    artifact_ref: str = Field(min_length=3)
    notes: str | None = None


class InterventionObservedProcess(StrictRuntimeOperatorInterventionModel):
    pid: int = Field(ge=1)
    process_name: str = Field(min_length=1)
    command_line: str | None = None
    service_name: Literal["station_health_loop", "bridge_overseer"] | None = None
    governance_role: str | None = None
    notes: str | None = None


class InterventionCommandRecord(StrictRuntimeOperatorInterventionModel):
    command: str = Field(min_length=1)
    notes: str | None = None


class InterventionActionTaken(StrictRuntimeOperatorInterventionModel):
    action_type: ActionType
    relevant_process_ids: list[int] = Field(default_factory=list)
    relevant_process_names: list[str] = Field(default_factory=list)
    commands_executed: list[InterventionCommandRecord] = Field(default_factory=list)
    command_execution_performed: bool
    notes: str | None = None

    @model_validator(mode="after")
    def validate_action_shape(self) -> "InterventionActionTaken":
        targeted_actions = {"inspect_process", "terminate_process", "terminate_multiple_processes"}
        if self.action_type in targeted_actions and not self.relevant_process_ids:
            raise ValueError("targeted actions require relevant_process_ids")
        if self.action_type == "observe_only":
            if self.relevant_process_ids or self.commands_executed or self.command_execution_performed:
                raise ValueError("observe_only cannot target processes or execute commands")
        if self.command_execution_performed and not self.commands_executed:
            raise ValueError("command_execution_performed requires commands_executed")
        if not self.command_execution_performed and self.commands_executed:
            raise ValueError("commands_executed require command_execution_performed=true")
        return self


class InterventionSafetyConstraints(StrictRuntimeOperatorInterventionModel):
    protected_process_targets_present: bool
    protected_process_names: list[str] = Field(default_factory=list)
    protected_process_override_acknowledged: bool = False
    protected_process_override_reason: str | None = None
    broad_kill_pattern_detected: bool = False
    broad_kill_pattern_blocked: bool = False
    safety_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_safety(self) -> "InterventionSafetyConstraints":
        if self.protected_process_targets_present:
            if not self.protected_process_names:
                raise ValueError("protected_process_targets_present requires protected_process_names")
            if self.protected_process_override_acknowledged and not self.protected_process_override_reason:
                raise ValueError("protected overrides require a reason")
        else:
            if self.protected_process_names:
                raise ValueError("protected_process_names require protected_process_targets_present")
            if self.protected_process_override_acknowledged or self.protected_process_override_reason:
                raise ValueError("protected overrides require protected process targets")
        if self.broad_kill_pattern_blocked and not self.broad_kill_pattern_detected:
            raise ValueError("broad_kill_pattern_blocked requires a detected pattern")
        return self


class RuntimeOperatorIntervention(StrictRuntimeOperatorInterventionModel):
    schema_name: Literal["runtime.operator.intervention"]
    schema_version: Literal[RUNTIME_OPERATOR_INTERVENTION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_operator_intervention"] = "runtime_operator_intervention"
    intervention_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    capture_id: str = Field(min_length=3)
    summary_id: str = Field(min_length=3)
    timestamp_utc: AwareDatetime
    initiated_by: Literal["operator"] = "operator"
    automated: Literal[False] = False
    intervention_tier: InterventionTier
    triggering_conditions: InterventionTriggeringConditions
    decision_framework: InterventionDecisionFramework
    observed_evidence: list[InterventionEvidenceRef] = Field(min_length=1)
    observed_processes: list[InterventionObservedProcess] = Field(default_factory=list)
    action_taken: InterventionActionTaken
    operator_reasoning: str = Field(min_length=1)
    safety_constraints: InterventionSafetyConstraints
    notes: str | None = None

    @model_validator(mode="after")
    def validate_intervention(self) -> "RuntimeOperatorIntervention":
        evidence_types = {item.artifact_type for item in self.observed_evidence}
        if "runtime.operator.summary" not in evidence_types:
            raise ValueError("observed_evidence must include a runtime.operator.summary reference")
        if "runtime.capture.classification_result" not in evidence_types:
            raise ValueError("observed_evidence must include a runtime.capture.classification_result reference")
        if self.intervention_tier == "tier_0_observe":
            if self.action_taken.action_type != "observe_only":
                raise ValueError("tier_0_observe must use observe_only action")
        if self.intervention_tier == "tier_1_soft_intervention":
            if self.action_taken.action_type not in {"inspect_process", "terminate_process", "terminate_multiple_processes"}:
                raise ValueError("tier_1_soft_intervention must remain targeted")
        if self.intervention_tier == "tier_2_hard_intervention":
            if self.action_taken.action_type not in {"stop_station_services", "halt_station_activity", "restart_machine"}:
                raise ValueError("tier_2_hard_intervention requires a broader intervention action")
        terminating = self.action_taken.action_type in {"terminate_process", "terminate_multiple_processes"}
        if terminating and self.safety_constraints.broad_kill_pattern_detected:
            raise ValueError("broad kill pattern detections cannot be recorded as valid interventions")
        if terminating and self.safety_constraints.protected_process_targets_present:
            if not self.safety_constraints.protected_process_override_acknowledged:
                raise ValueError("protected process termination requires explicit override acknowledgement")
        return self


PRIMARY_RUNTIME_OPERATOR_INTERVENTION_MODELS: dict[str, type[BaseModel]] = {
    "runtime_operator_intervention": RuntimeOperatorIntervention,
}


def export_runtime_operator_intervention_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_OPERATOR_INTERVENTION_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
