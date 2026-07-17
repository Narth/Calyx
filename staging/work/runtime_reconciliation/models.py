"""Typed models for staging-only runtime singleton and reconciliation enforcement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from staging.work.runtime_observer_simulation.models import RuntimeObserverSnapshot


RUNTIME_RECONCILIATION_SCHEMA_VERSION = "1.0.0"

TopologyClass = Literal["single_process", "wrapper_child_runtime_pair", "bounded_multi_surface_runtime"]
MultiplicityPosture = Literal[
    "single_instance_only",
    "single_wrapper_child_pair_only",
    "bounded_multi_instance",
    "bounded_multi_pair",
    "unclassified_no_launch_without_review",
]
LaunchDisposition = Literal[
    "permit_new_launch",
    "refuse_duplicate_launch",
    "attach_to_existing_runtime",
    "permit_declared_multiplicity",
    "ambiguous_runtime_blocked",
]
LaunchOrigin = Literal["operator", "scheduler", "launcher", "wrapper", "unknown"]
MatchingKind = Literal["powershell_script_path", "python_module", "command_token"]
TopologyMatchState = Literal["matches_expected", "duplicate_peer_detected", "ambiguous_host", "topology_mismatch"]
AmbiguityType = Literal[
    "missing_command_line",
    "missing_executable_path",
    "host_process_ambiguous",
    "insufficient_identity_evidence",
    "topology_ambiguous",
    "unclassified_service_target",
]
ServiceName = Literal[
    "station_health_loop",
    "bridge_overseer",
    "navigator_triage_loop",
    "cp6_cp7_loop",
    "energy_churn_cp9_loop",
    "service_failure_watch",
    "cli_avatar",
    "test_bounded_worker",
]


class StrictRuntimeReconciliationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeIdentityMarker(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.runtime_identity_marker"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_runtime_identity_marker"] = "runtime_runtime_identity_marker"
    marker_id: str = Field(min_length=3)
    service_name: ServiceName
    marker_kind: MatchingKind
    marker_value: str = Field(min_length=1)
    notes: str | None = None


class RuntimeEquivalenceMatcher(StrictRuntimeReconciliationModel):
    matching_kind: MatchingKind
    required_tokens: list[str] = Field(min_length=1)
    match_against: Literal["command_line", "executable_path", "either"] = "command_line"
    notes: str | None = None


class RuntimeServiceDeclaration(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.service_declaration.reconciliation"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_service_declaration_reconciliation"] = "runtime_service_declaration_reconciliation"
    declaration_id: str = Field(min_length=3)
    service_name: ServiceName
    expected_topology_class: TopologyClass
    multiplicity_posture: MultiplicityPosture
    permitted_multiplicity_count: int = Field(ge=0)
    equivalence_matchers: list[RuntimeEquivalenceMatcher] = Field(min_length=1)
    manual_override_allowed: bool = False
    expected_identity_markers: list[RuntimeIdentityMarker] = Field(default_factory=list)
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_posture(self) -> "RuntimeServiceDeclaration":
        if self.multiplicity_posture == "single_instance_only":
            if self.expected_topology_class != "single_process" or self.permitted_multiplicity_count != 1:
                raise ValueError("single_instance_only requires single_process and multiplicity count 1")
        if self.multiplicity_posture == "single_wrapper_child_pair_only":
            if self.expected_topology_class != "wrapper_child_runtime_pair" or self.permitted_multiplicity_count != 1:
                raise ValueError("single_wrapper_child_pair_only requires wrapper_child_runtime_pair and multiplicity count 1")
        if self.multiplicity_posture == "unclassified_no_launch_without_review" and self.permitted_multiplicity_count != 0:
            raise ValueError("unclassified_no_launch_without_review requires multiplicity count 0")
        return self


class RuntimeReconciliationRequest(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.reconciliation.request"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_reconciliation_request"] = "runtime_reconciliation_request"
    request_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    requested_at_utc: AwareDatetime
    declared_service_target: ServiceName
    launch_origin: LaunchOrigin
    initiating_surface: str = Field(min_length=1)
    requested_command_line: str = Field(min_length=1)
    requested_executable_path: str | None = None
    snapshot_ref: str = Field(min_length=3)
    capture_context: str = Field(min_length=1)
    notes: str | None = None


class EquivalentResident(StrictRuntimeReconciliationModel):
    resident_id: str = Field(min_length=3)
    service_name: ServiceName
    member_process_ids: list[int] = Field(min_length=1)
    topology_class: TopologyClass
    evidence_fields: list[str] = Field(min_length=1)
    matched_tokens: list[str] = Field(min_length=1)
    notes: str | None = None


class RuntimeReconciliationResult(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.reconciliation.result"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_reconciliation_result"] = "runtime_reconciliation_result"
    result_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    request_ref: str = Field(min_length=3)
    declaration_ref: str = Field(min_length=3)
    snapshot_ref: str = Field(min_length=3)
    evaluated_at_utc: AwareDatetime
    matching_posture_used: MultiplicityPosture
    permitted_multiplicity_count: int = Field(ge=0)
    equivalent_residents: list[EquivalentResident] = Field(default_factory=list)
    resident_count: int = Field(ge=0)
    topology_match_state: TopologyMatchState
    ambiguity_conditions: list[AmbiguityType] = Field(default_factory=list)
    disposition: LaunchDisposition
    resulting_reasoning: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> "RuntimeReconciliationResult":
        if self.resident_count != len(self.equivalent_residents):
            raise ValueError("resident_count must match equivalent_residents length")
        if self.disposition == "ambiguous_runtime_blocked" and not self.ambiguity_conditions:
            raise ValueError("ambiguous_runtime_blocked requires ambiguity_conditions")
        return self


class RuntimeDuplicateDetected(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.duplicate.runtime_detected"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_duplicate_runtime_detected"] = "runtime_duplicate_runtime_detected"
    artifact_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    request_ref: str = Field(min_length=3)
    result_ref: str = Field(min_length=3)
    service_name: ServiceName
    failure_class: Literal["singleton_violation", "undeclared_multiplicity", "duplicate_wrapper_child_pair"]
    equivalent_resident_count: int = Field(ge=1)
    notes: str = Field(min_length=1)


class RuntimeLaunchRefused(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.launch.refused"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_launch_refused"] = "runtime_launch_refused"
    artifact_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    request_ref: str = Field(min_length=3)
    result_ref: str = Field(min_length=3)
    service_name: ServiceName
    refusal_reason: Literal["duplicate_runtime", "ambiguous_runtime", "unclassified_service_target"]
    notes: str = Field(min_length=1)


class RuntimeReconciliationOperatorView(StrictRuntimeReconciliationModel):
    schema_name: Literal["runtime.reconciliation.operator_view"]
    schema_version: Literal[RUNTIME_RECONCILIATION_SCHEMA_VERSION]
    artifact_type: Literal["runtime_reconciliation_operator_view"] = "runtime_reconciliation_operator_view"
    artifact_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    request_ref: str = Field(min_length=3)
    result_ref: str = Field(min_length=3)
    service_name: ServiceName
    requested_disposition: LaunchDisposition
    resident_count: int = Field(ge=0)
    resident_process_ids: list[int] = Field(default_factory=list)
    evidence_support: list[str] = Field(min_length=1)
    ambiguity_conditions: list[AmbiguityType] = Field(default_factory=list)
    notes: str = Field(min_length=1)


class RuntimeReconciliationBundle(StrictRuntimeReconciliationModel):
    scenario_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    snapshot: RuntimeObserverSnapshot
    declaration: RuntimeServiceDeclaration
    request: RuntimeReconciliationRequest
    result: RuntimeReconciliationResult
    duplicate_detected: RuntimeDuplicateDetected | None = None
    launch_refused: RuntimeLaunchRefused | None = None
    operator_view: RuntimeReconciliationOperatorView


PRIMARY_RUNTIME_RECONCILIATION_MODELS: dict[str, type[BaseModel]] = {
    "runtime_service_declaration_reconciliation": RuntimeServiceDeclaration,
    "runtime_reconciliation_request": RuntimeReconciliationRequest,
    "runtime_reconciliation_result": RuntimeReconciliationResult,
    "runtime_duplicate_runtime_detected": RuntimeDuplicateDetected,
    "runtime_launch_refused": RuntimeLaunchRefused,
    "runtime_runtime_identity_marker": RuntimeIdentityMarker,
    "runtime_reconciliation_operator_view": RuntimeReconciliationOperatorView,
}


def export_runtime_reconciliation_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_RECONCILIATION_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
