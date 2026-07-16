"""Typed models for real capture to canonical observer snapshot mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from staging.work.runtime_observer_simulation.models import RuntimeObserverEmission, RuntimeObserverSnapshot


RUNTIME_CAPTURE_SCHEMA_VERSION = "1.0.0"


class StrictRuntimeCaptureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CapturedPort(StrictRuntimeCaptureModel):
    local_address: str | None = None
    local_port: int | None = Field(default=None, ge=1, le=65535)
    remote_address: str | None = None
    remote_port: int | None = Field(default=None, ge=1, le=65535)
    state: str | None = None


class CapturedProcessRow(StrictRuntimeCaptureModel):
    pid: int = Field(ge=1)
    parent_pid: int | None = Field(default=None, ge=1)
    process_name: str = Field(min_length=1)
    executable_path: str | None = None
    command_line: str | None = None
    started_at_utc: AwareDatetime | None = None
    ports: list[CapturedPort] = Field(default_factory=list)


class CapturedStationHealth(StrictRuntimeCaptureModel):
    source_path: str = Field(min_length=3)
    captured_at_utc: AwareDatetime
    health: Literal["pass", "warn", "fail", "unknown"]
    cpu_pct: int | None = Field(default=None, ge=0, le=100)
    ram_pct: int | None = Field(default=None, ge=0, le=100)
    interval_s: float | None = Field(default=None, gt=0)
    memory_pressure_tier: int | None = Field(default=None, ge=0, le=4)
    truth_state: Literal["fresh", "stale", "unknown"] | None = None
    stale_reason: str | None = None
    top_processes: list[str] = Field(default_factory=list)
    entropy_sources: list[str] = Field(default_factory=list)
    gpu_metrics_present: bool = False
    loop_elapsed_ms: int | None = Field(default=None, ge=0)
    loop_sleep_ms: int | None = Field(default=None, ge=0)
    expiry_sweep_invoked: bool | None = None


class CapturedBridgePulse(StrictRuntimeCaptureModel):
    source_path: str = Field(min_length=3)
    captured_at_utc: AwareDatetime
    phase: str = Field(min_length=1)
    status: str | None = None
    details: str = Field(min_length=1)
    work_state_hint: Literal["objectives_present", "objectives_absent", "objectives_empty"] | None = None
    idle_reason_hint: Literal["no_objectives_file", "empty_objectives_file", "no_dispatchable_work"] | None = None
    launch_notice_status_hint: Literal[
        "prelaunch_declared",
        "launch_adjacent_declared",
        "retroactive_classification_only",
    ] | None = None


class RuntimeCaptureInput(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.input"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_input"] = "runtime_capture_input"
    capture_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    captured_at_utc: AwareDatetime
    capture_mode: Literal["live_read_only", "offline_replay"]
    process_rows: list[CapturedProcessRow] = Field(min_length=1)
    station_health: CapturedStationHealth | None = None
    bridge_pulse: CapturedBridgePulse | None = None
    capture_notes: str = Field(min_length=1)


class RuntimeCaptureAmbiguityMarker(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.ambiguity_marker"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_ambiguity_marker"] = "runtime_capture_ambiguity_marker"
    marker_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    capture_id: str = Field(min_length=3)
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


class RuntimeCaptureIngestionTrace(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.ingestion_trace"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_ingestion_trace"] = "runtime_capture_ingestion_trace"
    trace_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    capture_id: str = Field(min_length=3)
    timestamp_utc: AwareDatetime
    source_process_count: int = Field(ge=0)
    mapped_process_count: int = Field(ge=0)
    defaulted_fields: list[str] = Field(default_factory=list)
    dropped_fields: list[str] = Field(default_factory=list)
    notes: str = Field(min_length=1)


class RuntimeCaptureMappingValidation(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.mapping_validation"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_mapping_validation"] = "runtime_capture_mapping_validation"
    validation_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    capture_id: str = Field(min_length=3)
    timestamp_utc: AwareDatetime
    snapshot_schema_valid: bool
    observer_emission_valid: bool
    no_mutation_performed: Literal[True] = True
    notes: str = Field(min_length=1)


class RuntimeCaptureNormalizationResult(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.normalization_result"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_normalization_result"] = "runtime_capture_normalization_result"
    capture_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    normalized_at_utc: AwareDatetime
    canonical_snapshot: RuntimeObserverSnapshot
    ingestion_trace: RuntimeCaptureIngestionTrace
    ambiguity_markers: list[RuntimeCaptureAmbiguityMarker] = Field(default_factory=list)


class RuntimeCaptureClassificationResult(StrictRuntimeCaptureModel):
    schema_name: Literal["runtime.capture.classification_result"]
    schema_version: Literal[RUNTIME_CAPTURE_SCHEMA_VERSION]
    artifact_type: Literal["runtime_capture_classification_result"] = "runtime_capture_classification_result"
    capture_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    classified_at_utc: AwareDatetime
    normalization: RuntimeCaptureNormalizationResult
    observer_emission: RuntimeObserverEmission
    mapping_validation: RuntimeCaptureMappingValidation


PRIMARY_RUNTIME_CAPTURE_MODELS: dict[str, type[BaseModel]] = {
    "runtime_capture_input": RuntimeCaptureInput,
    "runtime_capture_ambiguity_marker": RuntimeCaptureAmbiguityMarker,
    "runtime_capture_ingestion_trace": RuntimeCaptureIngestionTrace,
    "runtime_capture_mapping_validation": RuntimeCaptureMappingValidation,
    "runtime_capture_normalization_result": RuntimeCaptureNormalizationResult,
    "runtime_capture_classification_result": RuntimeCaptureClassificationResult,
}


def export_runtime_capture_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_CAPTURE_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
