"""Normalization path from weather research artifacts into Kalshi simulation inputs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from staging.work.kalshi_artifact_models.models import ScoreDimensions
from staging.work.kalshi_decision_simulation.case_models import (
    ReviewPlan,
    SimulatedKalshiCase,
)
from staging.work.weather_research_models.models import (
    WeatherDivergenceAssessment,
    WeatherForecastBundle,
    WeatherResearchSummary,
    WeatherSourceSnapshot,
)


class WeatherToKalshiCaseInput(BaseModel):
    """Bridges weather research into the existing Kalshi simulation case shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=3)
    scenario_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    corr_id: str = Field(min_length=3)
    market_id: str = Field(min_length=2)
    market_title: str = Field(min_length=1)
    resolution_rule_summary: str = Field(min_length=1)
    initial_timestamp_utc: str
    score_timestamp_utc: str
    gate_timestamp_utc: str
    readiness_timestamp_utc: str | None = None
    execution_timestamp_utc: str | None = None
    resolution_timestamp_utc: str
    proposed_side: str
    operator_engagement_state: str
    market_observation: dict
    entry_rationale: str = Field(min_length=1)
    decision_horizon: dict
    confidence_signal: float
    gate_outcome: str
    gate_reasons: list[str] = Field(min_length=1)
    operator_legibility_status: str
    wallet_policy_fit: str
    resolved_outcome: str
    trade_executed: bool
    execution_status: str | None = None
    position_taken: str
    review_plan: ReviewPlan
    score_dimensions_override: ScoreDimensions | None = None
    classification_band_override: str | None = None
    scoring_notes_override: str | None = None


def build_weather_supported_case(
    *,
    source_snapshots: list[WeatherSourceSnapshot],
    forecast_bundle: WeatherForecastBundle,
    divergence_assessment: WeatherDivergenceAssessment,
    research_summary: WeatherResearchSummary,
    kalshi_input: WeatherToKalshiCaseInput,
) -> SimulatedKalshiCase:
    """Build a Kalshi simulation case while preserving weather provenance in text fields."""

    evidence_summary = (
        f"{research_summary.evidence_summary} "
        f"Freshness: {forecast_bundle.freshness_state}. "
        f"Spread: {forecast_bundle.forecast_spread_summary}. "
        f"Sources: {', '.join(value.source_name for value in source_snapshots)}."
    )
    invalidation_condition = (
        f"{'; '.join(research_summary.invalidation_cues)} "
        f"Forecast bundle ref={forecast_bundle.bundle_id}; divergence ref={divergence_assessment.assessment_id}."
    )
    scoring_notes = kalshi_input.scoring_notes_override or (
        f"Weather-supported scoring derived from bundle {forecast_bundle.bundle_id} "
        f"and divergence assessment {divergence_assessment.assessment_id}."
    )
    classification_band = kalshi_input.classification_band_override or (
        "recommend.research_only"
        if research_summary.preliminary_suitability_outcome in (
            "weather_research.inconclusive",
            "weather_research.supportive_but_uncertain",
        )
        else "recommend.execution_ready_low_confidence"
    )
    score_dimensions = kalshi_input.score_dimensions_override or ScoreDimensions(
        evidence_strength=0.5 if forecast_bundle.freshness_state != "stale" else 0.0,
        mispricing_potential=divergence_assessment.divergence_magnitude,
        timing_quality=0.5 if forecast_bundle.freshness_state == "current" else 0.0,
        resolution_clarity=1.0 if forecast_bundle.resolution_fit_assessment == "aligned" else 0.5,
        liquidity_tradability=(
            0.5
            if (
                kalshi_input.market_observation.get("best_bid") is not None
                and kalshi_input.market_observation.get("best_ask") is not None
                and kalshi_input.market_observation.get("best_ask", 0.0) > 0.0
            )
            else 0.0
        ),
        decision_horizon_fit=0.5 if forecast_bundle.freshness_state != "stale" else 0.0,
        risk_clarity=0.5,
    )

    return SimulatedKalshiCase.model_validate(
        {
            "schema_name": "kalshi.mock_candidate_market_case",
            "schema_version": "1.0.0",
            "artifact_schema_version": "1.0.0",
            "case_id": kalshi_input.case_id,
            "scenario_name": kalshi_input.scenario_name,
            "description": kalshi_input.description,
            "corr_id": kalshi_input.corr_id,
            "market_id": kalshi_input.market_id,
            "market_title": kalshi_input.market_title,
            "resolution_rule_summary": kalshi_input.resolution_rule_summary,
            "initial_timestamp_utc": kalshi_input.initial_timestamp_utc,
            "score_timestamp_utc": kalshi_input.score_timestamp_utc,
            "gate_timestamp_utc": kalshi_input.gate_timestamp_utc,
            "readiness_timestamp_utc": kalshi_input.readiness_timestamp_utc,
            "execution_timestamp_utc": kalshi_input.execution_timestamp_utc,
            "resolution_timestamp_utc": kalshi_input.resolution_timestamp_utc,
            "proposed_side": kalshi_input.proposed_side,
            "expected_edge_source": research_summary.expected_edge_source,
            "operator_engagement_state": kalshi_input.operator_engagement_state,
            "market_observation": kalshi_input.market_observation,
            "entry_rationale": kalshi_input.entry_rationale,
            "decision_horizon": kalshi_input.decision_horizon,
            "invalidation_condition": invalidation_condition,
            "abstention_alternative": research_summary.preliminary_suitability_note,
            "evidence_summary": evidence_summary,
            "evidence_signal": divergence_assessment.forecast_implied_probability,
            "confidence_signal": kalshi_input.confidence_signal,
            "score_dimensions": score_dimensions,
            "downgrade_flags": (["signal_decay_applied"] if forecast_bundle.freshness_state == "stale" else []),
            "decay_state": "decayed" if forecast_bundle.freshness_state == "stale" else "fresh",
            "scoring_notes": scoring_notes,
            "classification_band": classification_band,
            "gate_outcome": kalshi_input.gate_outcome,
            "gate_reasons": kalshi_input.gate_reasons + [
                f"weather_bundle_ref={forecast_bundle.bundle_id}",
                f"weather_summary_ref={research_summary.summary_id}",
            ],
            "operator_legibility_status": kalshi_input.operator_legibility_status,
            "wallet_policy_fit": kalshi_input.wallet_policy_fit,
            "resolved_outcome": kalshi_input.resolved_outcome,
            "trade_executed": kalshi_input.trade_executed,
            "execution_status": kalshi_input.execution_status,
            "position_taken": kalshi_input.position_taken,
            "review_plan": kalshi_input.review_plan,
        }
    )
