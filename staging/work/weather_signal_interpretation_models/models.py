"""Canonical staging weather signal interpretation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from staging.work.weather_research_models.models import WeatherMarketType


WEATHER_INTERPRETATION_SCHEMA_VERSION = "1.0.0"

WeatherSupportBand = Literal["weak", "moderate", "strong"]
WeatherDowngradeFlag = Literal[
    "temperature.threshold_ambiguity",
    "temperature.high_source_spread",
    "temperature.stale_bundle",
    "temperature.marginal_edge",
    "precipitation.high_disagreement",
    "precipitation.accumulation_uncertain",
    "precipitation.window_mismatch",
    "precipitation.stale_bundle",
    "snow.threshold_ambiguity",
]
DownstreamSignalEffect = Literal[
    "reduce_evidence_strength",
    "reduce_mispricing_potential",
    "reduce_timing_quality",
    "reduce_decision_horizon_fit",
    "force_research_only_ceiling",
    "force_abstention_review",
]
ThresholdProximityAssessment = Literal["clear_separation", "near_threshold", "threshold_overlapping"]
SourceAgreementAssessment = Literal["high_agreement", "mixed_agreement", "high_disagreement"]
FreshnessAssessment = Literal["fresh", "aging", "stale"]


class StrictWeatherInterpretationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WeatherSignalInterpretation(StrictWeatherInterpretationModel):
    schema_name: Literal["weather.weather_signal_interpretation"]
    schema_version: Literal[WEATHER_INTERPRETATION_SCHEMA_VERSION]
    artifact_type: Literal["weather_signal_interpretation"] = "weather_signal_interpretation"
    corr_id: str = Field(min_length=3)
    timestamp_utc: AwareDatetime
    market_id: str = Field(min_length=2)
    weather_market_type: WeatherMarketType
    source_bundle_ref: str = Field(min_length=3)
    weather_support_band: WeatherSupportBand
    threshold_proximity_assessment: ThresholdProximityAssessment
    source_agreement_assessment: SourceAgreementAssessment
    freshness_assessment: FreshnessAssessment
    weather_downgrade_flags: list[WeatherDowngradeFlag] = Field(default_factory=list)
    downstream_signal_effects: list[DownstreamSignalEffect] = Field(default_factory=list)
    interpretation_notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_interpretation(self) -> "WeatherSignalInterpretation":
        notes = self.interpretation_notes.lower()
        banned = ("execution_ready", "authorized", "approve trade", "approved")
        if any(token in notes for token in banned):
            raise ValueError("weather interpretation artifacts must not emit execution authority language")
        if self.threshold_proximity_assessment == "threshold_overlapping":
            if (
                "temperature.threshold_ambiguity" not in self.weather_downgrade_flags
                and "snow.threshold_ambiguity" not in self.weather_downgrade_flags
                and "precipitation.accumulation_uncertain" not in self.weather_downgrade_flags
            ):
                raise ValueError("threshold_overlapping assessments require an ambiguity downgrade flag")
        if self.source_agreement_assessment == "high_disagreement":
            if "precipitation.high_disagreement" not in self.weather_downgrade_flags and "temperature.high_source_spread" not in self.weather_downgrade_flags:
                raise ValueError("high_disagreement assessments require a disagreement downgrade flag")
        if self.freshness_assessment == "stale":
            if not any(flag.endswith(".stale_bundle") for flag in self.weather_downgrade_flags):
                raise ValueError("stale interpretations require a stale_bundle downgrade flag")
            if self.weather_support_band == "strong":
                raise ValueError("stale interpretations cannot be strong")
        if self.weather_support_band == "strong":
            if self.threshold_proximity_assessment == "threshold_overlapping":
                raise ValueError("strong support cannot coexist with threshold ambiguity")
            if self.source_agreement_assessment == "high_disagreement":
                raise ValueError("strong support cannot coexist with high disagreement")
        return self


PRIMARY_WEATHER_INTERPRETATION_MODELS: dict[str, type[BaseModel]] = {
    "weather_signal_interpretation": WeatherSignalInterpretation,
}


def export_weather_interpretation_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, model in PRIMARY_WEATHER_INTERPRETATION_MODELS.items():
        destination = output_dir / f"{name}.schema.json"
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
