"""Typed models for operator-facing runtime safety summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


RUNTIME_OPERATOR_SUMMARY_SCHEMA_VERSION = "1.1.0"


class StrictRuntimeOperatorSummaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OperatorSystemLoadSnapshot(StrictRuntimeOperatorSummaryModel):
    cpu_pct: int | None = Field(default=None, ge=0, le=100)
    ram_pct: int | None = Field(default=None, ge=0, le=100)
    memory_pressure_tier: int | None = Field(default=None, ge=0, le=4)
    gpu_metrics_present: bool | None = None
    vram_metrics_available: bool = False
    health_state: Literal["pass", "warn", "fail", "unknown"] | None = None
    freshness_state: Literal["fresh", "aging", "stale", "unknown"] | None = None
    source_surface: str = Field(min_length=1)
    notes: str = Field(min_length=1)


class OperatorTopProcess(StrictRuntimeOperatorSummaryModel):
    rank: int = Field(ge=1)
    source: Literal["health_enrichment_snapshot", "station_health_capture"]
    process_label: str = Field(min_length=1)
    pid: int | None = Field(default=None, ge=1)
    executable_path: str | None = None
    command_line: str | None = None
    governed_surface: str | None = None
    notes: str | None = None


class OperatorGovernancePosture(StrictRuntimeOperatorSummaryModel):
    service_name: Literal["station_health_loop", "bridge_overseer"]
    topology_class: Literal["single_process", "wrapper_child_runtime_pair", "bounded_multi_surface_runtime"]
    multiplicity_posture: Literal[
        "single_instance_only",
        "wrapper_child_expected",
        "bounded_multiplicity_optional",
        "bounded_multiplicity_required",
    ]
    authoritative_runtime_role: str = Field(min_length=1)
    observed_process_count: int = Field(ge=1)
    validation_outcome: Literal[
        "topology_valid",
        "multiplicity_declared_and_compliant",
        "multiplicity_declared_but_noncompliant",
        "undeclared_multiplicity",
        "duplicate_concerning",
    ]
    posture_consequence: Literal[
        "none",
        "warning_posture",
        "degraded_trust_posture",
        "sunrise_noncompliance",
        "operator_review_required",
    ]
    noncompliance_type: Literal[
        "missing_launch_notice",
        "duplicate_writer_attempt",
        "duplicate_overseer_attempt",
        "temporary_persistence_violation",
    ] | None = None
    noncompliance_severity: Literal["moderate", "high"] | None = None
    health_state: Literal["pass", "warn", "fail", "unknown"] | None = None
    freshness_state: Literal["fresh", "aging", "stale", "unknown"] | None = None
    pulse_class: Literal["active", "idle"] | None = None
    idle_reason: Literal["none", "no_objectives_file", "empty_objectives_file", "no_dispatchable_work"] | None = None
    notes: list[str] = Field(default_factory=list)


class OperatorExpectationSignal(StrictRuntimeOperatorSummaryModel):
    signal_type: Literal[
        "multiplicity_noncompliance",
        "duplicate_concerning",
        "health_stale",
        "health_unknown",
        "health_fail",
        "cadence_noncompliant",
        "idle_bridge_visible",
        "governed_ambiguity_present",
        "load_elevated",
    ]
    service_name: Literal["station_health_loop", "bridge_overseer", "capture_layer", "system"]
    severity: Literal["info", "warn", "risk", "critical"]
    reasoning: str = Field(min_length=1)


class OperatorAmbiguityRecord(StrictRuntimeOperatorSummaryModel):
    service_name: Literal["station_health_loop", "bridge_overseer", "capture_layer"]
    ambiguity_type: Literal[
        "missing_command_line",
        "missing_executable_path",
        "health_cadence_unresolved",
        "health_expiry_sweep_unresolved",
        "bridge_idle_reason_unresolved",
        "bridge_work_state_unresolved",
        "no_matching_service_processes",
    ]
    notes: str = Field(min_length=1)


class OperatorWorkstationLoadView(StrictRuntimeOperatorSummaryModel):
    system_load_snapshot: OperatorSystemLoadSnapshot
    top_processes: list[OperatorTopProcess] = Field(default_factory=list)
    observed_process_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)


class OperatorStationRuntimeProcess(StrictRuntimeOperatorSummaryModel):
    pid: int = Field(ge=1)
    executable_path: str | None = None
    command_line: str | None = None
    station_membership: Literal["known_governed_service", "candidate_unattributed", "ambiguous_station_membership"]
    service_name: Literal["station_health_loop", "bridge_overseer"] | None = None
    evidence_notes: list[str] = Field(default_factory=list)


class OperatorStationRuntimeView(StrictRuntimeOperatorSummaryModel):
    processes: list[OperatorStationRuntimeProcess] = Field(default_factory=list)
    governance_posture: list[OperatorGovernancePosture] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)


class OperatorAttributionGap(StrictRuntimeOperatorSummaryModel):
    gap_type: Literal[
        "missing_launch_notice",
        "undeclared_runtime_process",
        "topology_mismatch",
        "missing_command_line_data",
        "missing_executable_path_data",
        "unresolved_parent_child_relationship",
        "health_cadence_unresolved",
        "health_expiry_sweep_unresolved",
        "bridge_idle_reason_unresolved",
        "bridge_work_state_unresolved",
    ]
    service_name: Literal["station_health_loop", "bridge_overseer", "capture_layer"]
    severity: Literal["info", "warn", "risk", "critical"]
    reasoning: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    affected_process_ids: list[int] = Field(default_factory=list)


class RuntimeOperatorSummary(StrictRuntimeOperatorSummaryModel):
    schema_name: Literal["runtime.operator.summary"]
    schema_version: Literal[RUNTIME_OPERATOR_SUMMARY_SCHEMA_VERSION]
    artifact_type: Literal["runtime_operator_summary"] = "runtime_operator_summary"
    summary_id: str = Field(min_length=3)
    capture_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    generated_at_utc: AwareDatetime
    source_capture_mode: Literal["live_read_only", "offline_replay"]
    workstation_load_view: OperatorWorkstationLoadView
    station_runtime_view: OperatorStationRuntimeView
    attribution_gaps: list[OperatorAttributionGap] = Field(default_factory=list)
    system_load_snapshot: OperatorSystemLoadSnapshot
    top_processes: list[OperatorTopProcess] = Field(default_factory=list)
    governance_posture: list[OperatorGovernancePosture] = Field(min_length=1)
    expectation_signals: list[OperatorExpectationSignal] = Field(default_factory=list)
    ambiguities: list[OperatorAmbiguityRecord] = Field(default_factory=list)
    system_load_condition: Literal["normal", "elevated", "high", "unknown"]
    governance_compliance_condition: Literal["compliant", "ambiguous", "noncompliant", "critical"]
    operator_risk_signal: Literal["NORMAL", "ELEVATED", "UNEXPECTED", "RISK", "CRITICAL"]
    operator_risk_reasoning: list[str] = Field(min_length=1)
    notes: str = Field(min_length=1)


PRIMARY_RUNTIME_OPERATOR_SUMMARY_MODELS: dict[str, type[BaseModel]] = {
    "runtime_operator_summary": RuntimeOperatorSummary,
}


def export_runtime_operator_summary_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_OPERATOR_SUMMARY_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
