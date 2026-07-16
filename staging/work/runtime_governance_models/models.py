"""Typed staging models for runtime multiplicity, health-loop, and bridge artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


RUNTIME_GOVERNANCE_SCHEMA_VERSION = "1.0.0"

ArtifactId = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")]
CorrId = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
ServiceName = Literal["station_health_loop", "bridge_overseer"]
TopologyClass = Literal["single_process", "wrapper_child_runtime_pair", "bounded_multi_surface_runtime"]
MultiplicityPosture = Literal[
    "single_instance_only",
    "wrapper_child_expected",
    "bounded_multiplicity_optional",
    "bounded_multiplicity_required",
]
RuntimeRole = Literal[
    "authoritative_writer",
    "health_enrichment_sampler",
    "launcher_wrapper",
    "effective_service_runtime",
    "runtime_supervisor",
    "bridge_cycle_owner",
    "bridge_idle_monitor",
    "duplicate_peer",
]
LaunchNoticeStatus = Literal["prelaunch_declared", "launch_adjacent_declared", "retroactive_classification_only"]
SteadyStateOrTemporary = Literal["steady_state", "temporary"]
MultiplicityValidationOutcome = Literal[
    "topology_valid",
    "multiplicity_declared_and_compliant",
    "multiplicity_declared_but_noncompliant",
    "undeclared_multiplicity",
    "duplicate_concerning",
]
MultiplicityPostureConsequence = Literal[
    "none",
    "warning_posture",
    "degraded_trust_posture",
    "sunrise_noncompliance",
    "operator_review_required",
]
HealthState = Literal["pass", "warn", "fail", "unknown"]
FreshnessState = Literal["fresh", "aging", "stale", "unknown"]
HealthSamplingLane = Literal["fast_path", "enrichment_path"]
BridgePulseClass = Literal["active", "idle"]
BridgeIdleReason = Literal["none", "no_objectives_file", "empty_objectives_file", "no_dispatchable_work"]
BridgeWorkState = Literal["objectives_present", "objectives_absent", "objectives_empty"]


class StrictRuntimeGovernanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeProcessIdentity(StrictRuntimeGovernanceModel):
    pid: int = Field(ge=1)
    executable_path: str = Field(min_length=3)
    command_line: str = Field(min_length=3)
    started_at_utc: AwareDatetime | None = None


class RuntimeServiceDeclaration(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.service_declaration"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_service_declaration"] = "runtime_service_declaration"
    artifact_id: ArtifactId
    service_name: ServiceName
    topology_class: TopologyClass
    multiplicity_posture: MultiplicityPosture
    authoritative_runtime_role: RuntimeRole
    expected_runtime_roles: list[RuntimeRole] = Field(min_length=1)
    launch_notice_required: bool

    @model_validator(mode="after")
    def validate_roles(self) -> "RuntimeServiceDeclaration":
        if self.authoritative_runtime_role not in self.expected_runtime_roles:
            raise ValueError("authoritative_runtime_role must be present in expected_runtime_roles")
        if self.service_name == "station_health_loop":
            if self.multiplicity_posture != "single_instance_only":
                raise ValueError("station_health_loop must remain single_instance_only in staging design")
            if self.authoritative_runtime_role != "authoritative_writer":
                raise ValueError("station_health_loop authoritative_runtime_role must be authoritative_writer")
        if self.service_name == "bridge_overseer":
            if self.authoritative_runtime_role not in ("bridge_cycle_owner", "effective_service_runtime"):
                raise ValueError("bridge_overseer authoritative role must identify the active overseer")
        return self


class RuntimeLaunchNotice(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.launch_notice"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_launch_notice"] = "runtime_launch_notice"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: ServiceName
    declared_by_surface: str = Field(min_length=3)
    topology_class: TopologyClass
    multiplicity_posture: MultiplicityPosture
    launch_reason: str = Field(min_length=1)
    parent_process_identity: RuntimeProcessIdentity
    child_or_additional_process_identity: RuntimeProcessIdentity | None = None
    intended_runtime_role: RuntimeRole
    steady_state_or_temporary: SteadyStateOrTemporary
    expected_lifecycle: str = Field(min_length=1)
    reconciliation_condition: str = Field(min_length=1)
    launch_notice_status: LaunchNoticeStatus


class RuntimeMultiplicityValidation(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.multiplicity.validation"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_multiplicity_validation"] = "runtime_multiplicity_validation"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: ServiceName
    declaration_ref: ArtifactId
    observed_process_identities: list[RuntimeProcessIdentity] = Field(min_length=1)
    required_launch_notice_refs: list[ArtifactId] = Field(default_factory=list)
    validation_outcome: MultiplicityValidationOutcome
    posture_consequence: MultiplicityPostureConsequence
    classification_notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_multiplicity_outcome(self) -> "RuntimeMultiplicityValidation":
        if self.validation_outcome == "topology_valid" and len(self.observed_process_identities) != 1:
            raise ValueError("topology_valid requires a single observed process identity")
        if self.validation_outcome == "multiplicity_declared_and_compliant" and not self.required_launch_notice_refs:
            raise ValueError("declared multiplicity must reference launch notice artifacts")
        if self.validation_outcome in ("undeclared_multiplicity", "duplicate_concerning") and self.required_launch_notice_refs:
            raise ValueError("undeclared or duplicate_concerning outcomes cannot claim launch notice refs as compliance")
        return self


class RuntimeMultiplicityNoncompliance(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.multiplicity.noncompliance"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_multiplicity_noncompliance"] = "runtime_multiplicity_noncompliance"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: ServiceName
    declaration_ref: ArtifactId
    validation_ref: ArtifactId
    noncompliance_type: Literal["missing_launch_notice", "duplicate_writer_attempt", "duplicate_overseer_attempt", "temporary_persistence_violation"]
    severity: Literal["moderate", "high"]
    required_operator_visibility: Literal["warn", "review_required"]
    notes: str = Field(min_length=1)


class HealthAuthoritativeSnapshot(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.health.authoritative_snapshot"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["health_authoritative_snapshot"] = "health_authoritative_snapshot"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: Literal["station_health_loop"] = "station_health_loop"
    declared_interval_seconds: float = Field(gt=0)
    observed_loop_elapsed_ms: int = Field(ge=0)
    observed_sleep_ms: int = Field(ge=0)
    cadence_compliant: bool
    sampling_lane: Literal["fast_path"] = "fast_path"
    health_state: HealthState
    freshness_state: FreshnessState
    stale_reason: str | None = None
    cpu_pct: int | None = Field(default=None, ge=0, le=100)
    ram_pct: int | None = Field(default=None, ge=0, le=100)
    memory_pressure_tier: int | None = Field(default=None, ge=0, le=4)
    expiry_sweep_invoked: bool
    truth_contract_surface: Literal["runtime/station_health.json"] = "runtime/station_health.json"

    @model_validator(mode="after")
    def validate_health_state(self) -> "HealthAuthoritativeSnapshot":
        if self.health_state == "unknown":
            if self.freshness_state not in ("stale", "unknown"):
                raise ValueError("unknown health must correspond to stale or unknown freshness")
        if not self.cadence_compliant and self.observed_sleep_ms > 0 and self.observed_loop_elapsed_ms + self.observed_sleep_ms > (self.declared_interval_seconds * 1000 * 1.5):
            raise ValueError("noncompliant cadence should not overstate sleep while missing the declared interval")
        return self


class HealthEnrichmentSnapshot(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.health.enrichment_snapshot"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["health_enrichment_snapshot"] = "health_enrichment_snapshot"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: Literal["station_health_loop"] = "station_health_loop"
    authoritative_snapshot_ref: ArtifactId
    sampling_lane: Literal["enrichment_path"] = "enrichment_path"
    enrichment_interval_seconds: float = Field(gt=0)
    enrichment_sample_age_ms: int = Field(ge=0)
    top_processes: list[str] = Field(default_factory=list)
    entropy_sources: list[str] = Field(default_factory=list)
    gpu_metrics_present: bool
    notes: str = Field(min_length=1)


class BridgePulseClassification(StrictRuntimeGovernanceModel):
    schema_name: Literal["runtime.bridge.pulse_classification"]
    schema_version: Literal[RUNTIME_GOVERNANCE_SCHEMA_VERSION]
    artifact_type: Literal["bridge_pulse_classification"] = "bridge_pulse_classification"
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    service_name: Literal["bridge_overseer"] = "bridge_overseer"
    pulse_class: BridgePulseClass
    work_state: BridgeWorkState
    idle_reason: BridgeIdleReason
    idle_mode_active: bool
    backoff_active: bool
    backoff_seconds: int = Field(ge=0)
    objectives_count: int = Field(ge=0)
    planned_tasks_count: int = Field(ge=0)
    dispatched_count: int = Field(ge=0)
    truthful_visibility_preserved: bool
    notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bridge_classification(self) -> "BridgePulseClassification":
        if self.pulse_class == "active":
            if self.idle_mode_active:
                raise ValueError("active pulse cannot set idle_mode_active")
            if self.idle_reason != "none":
                raise ValueError("active pulse cannot have an idle_reason")
        if self.pulse_class == "idle":
            if not self.idle_mode_active:
                raise ValueError("idle pulse must set idle_mode_active")
            if self.idle_reason == "none":
                raise ValueError("idle pulse requires an idle_reason")
        if self.backoff_active and self.backoff_seconds <= 0:
            raise ValueError("backoff_active requires a positive backoff_seconds")
        if not self.backoff_active and self.backoff_seconds != 0:
            raise ValueError("backoff_seconds must be zero when backoff is inactive")
        return self


class RuntimeGovernanceBundle(StrictRuntimeGovernanceModel):
    scenario_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    service_declaration: RuntimeServiceDeclaration
    runtime_launch_notice: RuntimeLaunchNotice | None = None
    runtime_multiplicity_validation: RuntimeMultiplicityValidation
    runtime_multiplicity_noncompliance: RuntimeMultiplicityNoncompliance | None = None
    health_authoritative_snapshot: HealthAuthoritativeSnapshot | None = None
    health_enrichment_snapshot: HealthEnrichmentSnapshot | None = None
    bridge_pulse_classification: BridgePulseClassification | None = None

    @model_validator(mode="after")
    def validate_bundle(self) -> "RuntimeGovernanceBundle":
        if self.service_declaration.service_name == "station_health_loop":
            if self.health_authoritative_snapshot is None:
                raise ValueError("station_health_loop scenarios require a health_authoritative_snapshot")
            if self.bridge_pulse_classification is not None:
                raise ValueError("station_health_loop scenarios cannot include bridge_pulse_classification")
        if self.service_declaration.service_name == "bridge_overseer":
            if self.bridge_pulse_classification is None:
                raise ValueError("bridge_overseer scenarios require a bridge_pulse_classification")
            if self.health_authoritative_snapshot is not None or self.health_enrichment_snapshot is not None:
                raise ValueError("bridge_overseer scenarios cannot include health snapshots")
        if self.runtime_multiplicity_noncompliance is not None:
            if self.runtime_multiplicity_noncompliance.validation_ref != self.runtime_multiplicity_validation.artifact_id:
                raise ValueError("noncompliance validation_ref must target the bundle validation artifact")
        if self.health_enrichment_snapshot is not None and self.health_authoritative_snapshot is None:
            raise ValueError("health_enrichment_snapshot requires health_authoritative_snapshot")
        if self.health_enrichment_snapshot is not None:
            if self.health_enrichment_snapshot.authoritative_snapshot_ref != self.health_authoritative_snapshot.artifact_id:
                raise ValueError("health enrichment must reference the bundle authoritative snapshot")
        return self


PRIMARY_RUNTIME_GOVERNANCE_MODELS: dict[str, type[BaseModel]] = {
    "runtime_service_declaration": RuntimeServiceDeclaration,
    "runtime_launch_notice": RuntimeLaunchNotice,
    "runtime_multiplicity_validation": RuntimeMultiplicityValidation,
    "runtime_multiplicity_noncompliance": RuntimeMultiplicityNoncompliance,
    "health_authoritative_snapshot": HealthAuthoritativeSnapshot,
    "health_enrichment_snapshot": HealthEnrichmentSnapshot,
    "bridge_pulse_classification": BridgePulseClassification,
}


def export_runtime_governance_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_GOVERNANCE_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
