"""Deterministic staging interpretation for weather forecast bundles."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from staging.work.kalshi_artifact_models.models import ScoreDimensions
from staging.work.kalshi_decision_simulation.case_models import SimulatedKalshiCase
from staging.work.weather_research_models.integration import (
    WeatherToKalshiCaseInput,
    build_weather_supported_case,
)
from staging.work.weather_research_models.models import (
    WeatherDivergenceAssessment,
    WeatherForecastBundle,
    WeatherResearchSummary,
    WeatherSourceSnapshot,
)
from staging.work.weather_signal_interpretation_models.models import (
    DownstreamSignalEffect,
    FreshnessAssessment,
    SourceAgreementAssessment,
    ThresholdProximityAssessment,
    WeatherDowngradeFlag,
    WeatherSignalInterpretation,
    WeatherSupportBand,
)


class WeatherInterpretationContext(BaseModel):
    """Extra bounded context required to interpret bundle values against a market threshold."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    corr_id: str = Field(min_length=3)
    interpretation_timestamp_utc: str
    settlement_threshold: float | None = None
    threshold_unit: str | None = None
    occurrence_market: bool = False
    forecast_window_aligned: bool = True
    force_research_only_ceiling: bool = False
    force_abstention_review: bool = False


def derive_weather_signal_interpretation(
    *,
    forecast_bundle: WeatherForecastBundle,
    context: WeatherInterpretationContext,
) -> WeatherSignalInterpretation:
    values = forecast_bundle.source_values
    primary_values = [value.primary_value for value in values]
    threshold_relations = {value.threshold_relation for value in values}

    threshold_proximity = _threshold_proximity(
        forecast_bundle=forecast_bundle,
        context=context,
        primary_values=primary_values,
        threshold_relations=threshold_relations,
    )
    source_agreement = _source_agreement(
        forecast_bundle=forecast_bundle,
        threshold_relations=threshold_relations,
    )
    freshness = _freshness_assessment(forecast_bundle.freshness_state)

    downgrade_flags: list[WeatherDowngradeFlag] = []
    downstream_effects: list[DownstreamSignalEffect] = []

    if forecast_bundle.weather_market_type in ("daily_high_temperature", "daily_low_temperature"):
        if threshold_proximity == "threshold_overlapping":
            downgrade_flags.append("temperature.threshold_ambiguity")
            downstream_effects.extend(["reduce_evidence_strength", "force_research_only_ceiling"])
        if source_agreement == "high_disagreement":
            downgrade_flags.append("temperature.high_source_spread")
            downstream_effects.extend(["reduce_evidence_strength", "reduce_mispricing_potential"])
        if threshold_proximity == "near_threshold":
            downgrade_flags.append("temperature.marginal_edge")
            downstream_effects.extend(["reduce_mispricing_potential", "force_research_only_ceiling"])
        if freshness == "stale":
            downgrade_flags.append("temperature.stale_bundle")
            downstream_effects.extend(["reduce_timing_quality", "reduce_decision_horizon_fit"])
    elif forecast_bundle.weather_market_type == "measurable_precipitation":
        if source_agreement == "high_disagreement":
            downgrade_flags.append("precipitation.high_disagreement")
            downstream_effects.extend(["reduce_evidence_strength", "force_research_only_ceiling"])
        if not context.forecast_window_aligned:
            downgrade_flags.append("precipitation.window_mismatch")
            downstream_effects.extend(["reduce_timing_quality", "force_abstention_review"])
        if (
            not context.occurrence_market
            and threshold_proximity in ("near_threshold", "threshold_overlapping")
        ):
            downgrade_flags.append("precipitation.accumulation_uncertain")
            downstream_effects.extend(["reduce_mispricing_potential", "force_research_only_ceiling"])
        if freshness == "stale":
            downgrade_flags.append("precipitation.stale_bundle")
            downstream_effects.extend(["reduce_timing_quality", "reduce_decision_horizon_fit"])
    elif forecast_bundle.weather_market_type == "measurable_snowfall":
        if threshold_proximity in ("near_threshold", "threshold_overlapping"):
            downgrade_flags.append("snow.threshold_ambiguity")
            downstream_effects.extend(["reduce_evidence_strength", "force_research_only_ceiling"])

    if context.force_research_only_ceiling:
        downstream_effects.append("force_research_only_ceiling")
    if context.force_abstention_review:
        downstream_effects.append("force_abstention_review")

    downgrade_flags = _dedupe_preserve_order(downgrade_flags)
    downstream_effects = _dedupe_preserve_order(downstream_effects)
    support_band = _support_band(
        threshold_proximity=threshold_proximity,
        source_agreement=source_agreement,
        freshness=freshness,
        downgrade_flags=downgrade_flags,
    )

    notes = (
        f"Weather interpretation derived from bundle {forecast_bundle.bundle_id}. "
        f"Threshold proximity={threshold_proximity}; source agreement={source_agreement}; freshness={freshness}."
    )

    return WeatherSignalInterpretation.model_validate(
        {
            "schema_name": "weather.weather_signal_interpretation",
            "schema_version": "1.0.0",
            "artifact_type": "weather_signal_interpretation",
            "corr_id": context.corr_id,
            "timestamp_utc": context.interpretation_timestamp_utc,
            "market_id": forecast_bundle.market_id,
            "weather_market_type": forecast_bundle.weather_market_type,
            "source_bundle_ref": forecast_bundle.bundle_id,
            "weather_support_band": support_band,
            "threshold_proximity_assessment": threshold_proximity,
            "source_agreement_assessment": source_agreement,
            "freshness_assessment": freshness,
            "weather_downgrade_flags": downgrade_flags,
            "downstream_signal_effects": downstream_effects,
            "interpretation_notes": notes,
        }
    )


def build_interpreted_weather_case(
    *,
    source_snapshots: list[WeatherSourceSnapshot],
    forecast_bundle: WeatherForecastBundle,
    divergence_assessment: WeatherDivergenceAssessment,
    research_summary: WeatherResearchSummary,
    interpretation: WeatherSignalInterpretation,
    kalshi_input: WeatherToKalshiCaseInput,
) -> SimulatedKalshiCase:
    score_dimensions = _score_dimensions_from_interpretation(
        forecast_bundle=forecast_bundle,
        divergence_assessment=divergence_assessment,
        interpretation=interpretation,
        market_observation=kalshi_input.market_observation,
    )
    classification_band = _classification_band_from_interpretation(interpretation.weather_support_band, interpretation.downstream_signal_effects)
    scoring_notes = (
        f"Weather-supported scoring derived from bundle {forecast_bundle.bundle_id}, "
        f"interpretation support={interpretation.weather_support_band}, "
        f"weather downgrade flags={', '.join(interpretation.weather_downgrade_flags) or 'none'}."
    )
    patched_input = kalshi_input.model_copy(
        update={
            "score_dimensions_override": score_dimensions,
            "classification_band_override": classification_band,
            "scoring_notes_override": scoring_notes,
        }
    )
    case = build_weather_supported_case(
        source_snapshots=source_snapshots,
        forecast_bundle=forecast_bundle,
        divergence_assessment=divergence_assessment,
        research_summary=research_summary,
        kalshi_input=patched_input,
    )
    return SimulatedKalshiCase.model_validate(
        {
            **case.model_dump(mode="json"),
            "downgrade_flags": _kalshi_downgrade_flags(interpretation.weather_downgrade_flags, forecast_bundle.freshness_state),
            "scoring_notes": (
                f"{case.scoring_notes} "
                f"Interpretation ref={interpretation.source_bundle_ref}; support_band={interpretation.weather_support_band}; "
                f"effects={', '.join(interpretation.downstream_signal_effects) or 'none'}."
            ),
            "gate_reasons": case.gate_reasons + [f"weather_interpretation_support_band={interpretation.weather_support_band}"],
        }
    )


def _threshold_proximity(
    *,
    forecast_bundle: WeatherForecastBundle,
    context: WeatherInterpretationContext,
    primary_values: list[float],
    threshold_relations: set[str],
) -> ThresholdProximityAssessment:
    if len(threshold_relations) > 1 or "at_threshold" in threshold_relations:
        return "threshold_overlapping"
    if context.occurrence_market or context.settlement_threshold is None:
        return "clear_separation"
    min_distance = min(abs(value - context.settlement_threshold) for value in primary_values)
    if forecast_bundle.weather_market_type in ("daily_high_temperature", "daily_low_temperature"):
        if min_distance <= 1.5:
            return "near_threshold"
        return "clear_separation"
    if min_distance <= 0.02:
        return "threshold_overlapping"
    if min_distance <= 0.12:
        return "near_threshold"
    return "clear_separation"


def _source_agreement(
    *,
    forecast_bundle: WeatherForecastBundle,
    threshold_relations: set[str],
) -> SourceAgreementAssessment:
    spread = forecast_bundle.forecast_spread_value
    if len(threshold_relations) > 1:
        return "high_disagreement"
    if forecast_bundle.weather_market_type in ("daily_high_temperature", "daily_low_temperature"):
        if spread >= 3.0:
            return "high_disagreement"
        if spread > 1.5:
            return "mixed_agreement"
        return "high_agreement"
    if spread >= 0.15:
        return "high_disagreement"
    if spread > 0.05:
        return "mixed_agreement"
    return "high_agreement"


def _freshness_assessment(state: Literal["current", "aging", "stale"]) -> FreshnessAssessment:
    if state == "current":
        return "fresh"
    return state


def _support_band(
    *,
    threshold_proximity: ThresholdProximityAssessment,
    source_agreement: SourceAgreementAssessment,
    freshness: FreshnessAssessment,
    downgrade_flags: list[WeatherDowngradeFlag],
) -> WeatherSupportBand:
    if freshness == "stale":
        return "weak"
    if threshold_proximity == "threshold_overlapping" or source_agreement == "high_disagreement":
        return "weak"
    if any(flag in downgrade_flags for flag in ("temperature.marginal_edge", "precipitation.accumulation_uncertain", "snow.threshold_ambiguity")):
        return "moderate" if freshness == "fresh" and source_agreement != "high_disagreement" else "weak"
    if threshold_proximity == "clear_separation" and source_agreement == "high_agreement" and freshness == "fresh":
        return "strong"
    return "moderate"


def _score_dimensions_from_interpretation(
    *,
    forecast_bundle: WeatherForecastBundle,
    divergence_assessment: WeatherDivergenceAssessment,
    interpretation: WeatherSignalInterpretation,
    market_observation: dict,
) -> ScoreDimensions:
    support_base = {"weak": 0.25, "moderate": 0.5, "strong": 0.75}[interpretation.weather_support_band]
    evidence_strength = support_base if interpretation.weather_support_band != "strong" else 1.0
    mispricing_potential = max(divergence_assessment.divergence_magnitude, support_base)
    timing_quality = 0.75 if interpretation.freshness_assessment == "fresh" else 0.5 if interpretation.freshness_assessment == "aging" else 0.25
    decision_horizon_fit = timing_quality
    resolution_clarity = 1.0 if forecast_bundle.resolution_fit_assessment == "aligned" else 0.5
    liquidity_tradability = 0.5 if (
        market_observation.get("best_bid") is not None
        and market_observation.get("best_ask") is not None
        and market_observation.get("best_ask", 0.0) > 0.0
    ) else 0.0
    risk_clarity = 0.75 if interpretation.weather_support_band == "strong" else 0.5 if interpretation.weather_support_band == "moderate" else 0.25

    if "reduce_evidence_strength" in interpretation.downstream_signal_effects:
        evidence_strength = max(0.0, evidence_strength - 0.25)
    if "reduce_mispricing_potential" in interpretation.downstream_signal_effects:
        mispricing_potential = max(0.0, mispricing_potential - 0.25)
    if "reduce_timing_quality" in interpretation.downstream_signal_effects:
        timing_quality = max(0.0, timing_quality - 0.25)
    if "reduce_decision_horizon_fit" in interpretation.downstream_signal_effects:
        decision_horizon_fit = max(0.0, decision_horizon_fit - 0.25)

    return ScoreDimensions(
        evidence_strength=evidence_strength,
        mispricing_potential=min(1.0, mispricing_potential),
        timing_quality=timing_quality,
        resolution_clarity=resolution_clarity,
        liquidity_tradability=liquidity_tradability,
        decision_horizon_fit=decision_horizon_fit,
        risk_clarity=risk_clarity,
    )


def _classification_band_from_interpretation(
    support_band: WeatherSupportBand,
    downstream_effects: list[DownstreamSignalEffect],
) -> str:
    if "force_abstention_review" in downstream_effects:
        return "abstain.low_quality_candidate"
    if "force_research_only_ceiling" in downstream_effects:
        return "recommend.research_only"
    return {
        "weak": "abstain.low_quality_candidate",
        "moderate": "recommend.research_only",
        "strong": "recommend.execution_ready_low_confidence",
    }[support_band]


def _kalshi_downgrade_flags(
    weather_flags: list[WeatherDowngradeFlag],
    freshness_state: str,
) -> list[str]:
    flags = list(weather_flags)
    if freshness_state == "stale" and "signal_decay_applied" not in flags:
        flags.append("signal_decay_applied")
    return flags


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
