"""Typed input and output models for staging runtime observer simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from staging.work.runtime_governance_models.models import RuntimeGovernanceBundle


RUNTIME_OBSERVER_SCHEMA_VERSION = "1.0.0"


class StrictRuntimeObserverModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ObservedProcess(StrictRuntimeObserverModel):
    pid: int = Field(ge=1)
    parent_pid: int | None = Field(default=None, ge=1)
    executable_path: str = Field(min_length=3)
    command_line: str = Field(min_length=3)
    started_at_utc: AwareDatetime | None = None


class HealthObserverContext(StrictRuntimeObserverModel):
    declared_interval_seconds: float = Field(gt=0)
    observed_loop_elapsed_ms: int = Field(ge=0)
    observed_sleep_ms: int = Field(ge=0)
    health_state: Literal["pass", "warn", "fail", "unknown"]
    freshness_state: Literal["fresh", "aging", "stale", "unknown"]
    stale_reason: str | None = None
    cpu_pct: int | None = Field(default=None, ge=0, le=100)
    ram_pct: int | None = Field(default=None, ge=0, le=100)
    memory_pressure_tier: int | None = Field(default=None, ge=0, le=4)
    expiry_sweep_invoked: bool
    enrichment_interval_seconds: float | None = Field(default=None, gt=0)
    enrichment_sample_age_ms: int | None = Field(default=None, ge=0)
    top_processes: list[str] = Field(default_factory=list)
    entropy_sources: list[str] = Field(default_factory=list)
    gpu_metrics_present: bool = False
    launch_notice_status: Literal["launch_adjacent_declared", "retroactive_classification_only"] | None = None

    @model_validator(mode="after")
    def validate_enrichment_pairing(self) -> "HealthObserverContext":
        if self.enrichment_interval_seconds is None and self.enrichment_sample_age_ms is not None:
            raise ValueError("enrichment_sample_age_ms requires enrichment_interval_seconds")
        if self.enrichment_interval_seconds is not None and self.enrichment_sample_age_ms is None:
            raise ValueError("enrichment_interval_seconds requires enrichment_sample_age_ms")
        return self


class BridgeObserverContext(StrictRuntimeObserverModel):
    objectives_count: int = Field(ge=0)
    planned_tasks_count: int = Field(ge=0)
    dispatched_count: int = Field(ge=0)
    work_state: Literal["objectives_present", "objectives_absent", "objectives_empty"]
    idle_reason: Literal["none", "no_objectives_file", "empty_objectives_file", "no_dispatchable_work"] | None = None
    backoff_active: bool = False
    backoff_seconds: int = Field(default=0, ge=0)
    truthful_visibility_preserved: bool = True
    launch_notice_status: Literal[
        "prelaunch_declared",
        "launch_adjacent_declared",
        "retroactive_classification_only",
    ] | None = None

    @model_validator(mode="after")
    def validate_backoff(self) -> "BridgeObserverContext":
        if self.backoff_active and self.backoff_seconds <= 0:
            raise ValueError("backoff_active requires positive backoff_seconds")
        if not self.backoff_active and self.backoff_seconds != 0:
            raise ValueError("backoff_seconds must be zero when backoff_active is false")
        return self


class RuntimeObserverSnapshot(StrictRuntimeObserverModel):
    schema_name: Literal["runtime.observer.process_snapshot"]
    schema_version: Literal[RUNTIME_OBSERVER_SCHEMA_VERSION]
    artifact_type: Literal["runtime_observer_process_snapshot"] = "runtime_observer_process_snapshot"
    snapshot_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    captured_at_utc: AwareDatetime
    observer_mode: Literal["staging_only"] = "staging_only"
    processes: list[ObservedProcess] = Field(min_length=1)
    health_context: HealthObserverContext | None = None
    bridge_context: BridgeObserverContext | None = None
    capture_notes: str = Field(min_length=1)


class RuntimeObserverEmission(StrictRuntimeObserverModel):
    schema_name: Literal["runtime.observer.emission"]
    schema_version: Literal[RUNTIME_OBSERVER_SCHEMA_VERSION]
    artifact_type: Literal["runtime_observer_emission"] = "runtime_observer_emission"
    snapshot_id: str = Field(min_length=3)
    corr_id: str = Field(min_length=3)
    captured_at_utc: AwareDatetime
    emitted_at_utc: AwareDatetime
    governance_bundles: list[RuntimeGovernanceBundle] = Field(min_length=1)
    notes: str = Field(min_length=1)


PRIMARY_RUNTIME_OBSERVER_MODELS: dict[str, type[BaseModel]] = {
    "runtime_observer_process_snapshot": RuntimeObserverSnapshot,
    "runtime_observer_emission": RuntimeObserverEmission,
}


def export_runtime_observer_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_RUNTIME_OBSERVER_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
