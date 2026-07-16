"""Canonical staging weather research artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


WEATHER_SCHEMA_VERSION = "1.0.0"

UnitValue = Annotated[float, Field(ge=0.0)]
ConfidenceValue = Annotated[float, Field(ge=0.0, le=1.0)]
ReadableText = Annotated[str, Field(min_length=1)]

WeatherMarketType = Literal[
    "daily_high_temperature",
    "daily_low_temperature",
    "measurable_precipitation",
    "measurable_snowfall",
    "weather_threshold_event",
]
WeatherMetric = Literal[
    "temperature_high_f",
    "temperature_low_f",
    "precip_probability",
    "precip_accumulation_in",
    "snow_accumulation_in",
    "threshold_event_probability",
]
FreshnessState = Literal["current", "aging", "stale"]
ResolutionFitAssessment = Literal["aligned", "partial_fit", "misaligned"]
WeatherSuitabilityOutcome = Literal[
    "weather_research.unsuitable",
    "weather_research.inconclusive",
    "weather_research.possible_divergence",
    "weather_research.supportive_but_uncertain",
    "weather_research.supportive",
]


class StrictWeatherModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WeatherValue(StrictWeatherModel):
    metric: WeatherMetric
    value: float
    unit: str = Field(min_length=1)
    threshold_relation: str = Field(min_length=1)
    forecast_probability: ConfidenceValue | None = None
    qualitative_note: str | None = None


class WeatherSourceSnapshot(StrictWeatherModel):
    schema_name: Literal["weather.weather_source_snapshot"]
    schema_version: Literal[WEATHER_SCHEMA_VERSION]
    artifact_type: Literal["weather_source_snapshot"] = "weather_source_snapshot"
    snapshot_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    market_id: str = Field(min_length=2)
    weather_market_type: WeatherMarketType
    source_name: str = Field(min_length=1)
    captured_at_utc: AwareDatetime
    location_basis: str = Field(min_length=1)
    forecast_target_window: str = Field(min_length=1)
    forecast_value_summary: str = Field(min_length=1)
    raw_reference: str = Field(min_length=1)
    raw_payload: dict | None = None
    values: list[WeatherValue] = Field(min_length=1)


class ForecastSourceValue(StrictWeatherModel):
    source_snapshot_ref: str = Field(min_length=3)
    source_name: str = Field(min_length=1)
    captured_at_utc: AwareDatetime
    value_summary: str = Field(min_length=1)
    primary_metric: WeatherMetric
    primary_value: float
    primary_unit: str = Field(min_length=1)
    threshold_relation: str = Field(min_length=1)
    forecast_probability: ConfidenceValue | None = None


class WeatherForecastBundle(StrictWeatherModel):
    schema_name: Literal["weather.weather_forecast_bundle"]
    schema_version: Literal[WEATHER_SCHEMA_VERSION]
    artifact_type: Literal["weather_forecast_bundle"] = "weather_forecast_bundle"
    bundle_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    market_id: str = Field(min_length=2)
    weather_market_type: WeatherMarketType
    target_location: str = Field(min_length=1)
    target_resolution_window: str = Field(min_length=1)
    relevant_weather_metric: WeatherMetric
    source_values: list[ForecastSourceValue] = Field(min_length=1)
    forecast_spread_value: float = Field(ge=0.0)
    forecast_spread_summary: str = Field(min_length=1)
    latest_observation_summary: str | None = None
    freshness_state: FreshnessState
    freshness_window_hours: float = Field(gt=0.0)
    resolution_fit_assessment: ResolutionFitAssessment
    uncertainty_note: str = Field(min_length=1)
    raw_snapshot_refs: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_distinction(self) -> "WeatherForecastBundle":
        refs = {value.source_snapshot_ref for value in self.source_values}
        if len(refs) != len(self.source_values):
            raise ValueError("source_values must preserve distinct source snapshot references")
        if sorted(refs) != sorted(self.raw_snapshot_refs):
            raise ValueError("raw_snapshot_refs must match source_values source_snapshot_ref entries")
        return self


class WeatherDivergenceAssessment(StrictWeatherModel):
    schema_name: Literal["weather.weather_divergence_assessment"]
    schema_version: Literal[WEATHER_SCHEMA_VERSION]
    artifact_type: Literal["weather_divergence_assessment"] = "weather_divergence_assessment"
    assessment_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    market_id: str = Field(min_length=2)
    bundle_ref: str = Field(min_length=3)
    market_implied_probability: ConfidenceValue
    forecast_implied_probability: ConfidenceValue
    divergence_magnitude: ConfidenceValue
    divergence_note: str = Field(min_length=1)
    source_value_trace: list[ForecastSourceValue] = Field(min_length=1)
    tradability_note: str = Field(min_length=1)
    preliminary_suitability_outcome: WeatherSuitabilityOutcome
    uncertainty_note: str = Field(min_length=1)


class WeatherResearchSummary(StrictWeatherModel):
    schema_name: Literal["weather.weather_research_summary"]
    schema_version: Literal[WEATHER_SCHEMA_VERSION]
    artifact_type: Literal["weather_research_summary"] = "weather_research_summary"
    summary_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    market_id: str = Field(min_length=2)
    weather_market_type: WeatherMarketType
    research_timestamp_utc: AwareDatetime
    forecast_bundle_ref: str = Field(min_length=3)
    divergence_assessment_ref: str = Field(min_length=3)
    source_summary_table: list[ForecastSourceValue] = Field(min_length=1)
    divergence_note: str = Field(min_length=1)
    freshness_note: str = Field(min_length=1)
    uncertainty_note: str = Field(min_length=1)
    preliminary_suitability_note: str = Field(min_length=1)
    preliminary_suitability_outcome: WeatherSuitabilityOutcome
    evidence_summary: str = Field(min_length=1)
    invalidation_cues: list[str] = Field(min_length=1)
    expected_edge_source: Literal["weather_forecast_divergence"] = "weather_forecast_divergence"
    review_reference_snapshot_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_non_authority_language(self) -> "WeatherResearchSummary":
        banned = ("execution_ready", "authorized", "approve trade", "approved")
        combined = " ".join(
            [
                self.divergence_note.lower(),
                self.freshness_note.lower(),
                self.uncertainty_note.lower(),
                self.preliminary_suitability_note.lower(),
                self.evidence_summary.lower(),
            ]
        )
        if any(token in combined for token in banned):
            raise ValueError("weather research artifacts must not emit execution authority language")
        return self


PRIMARY_WEATHER_MODELS: dict[str, type[BaseModel]] = {
    "weather_source_snapshot": WeatherSourceSnapshot,
    "weather_forecast_bundle": WeatherForecastBundle,
    "weather_research_summary": WeatherResearchSummary,
    "weather_divergence_assessment": WeatherDivergenceAssessment,
}


def export_weather_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_WEATHER_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
