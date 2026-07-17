"""Mock input schema for staging Kalshi decision simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from staging.work.kalshi_artifact_models.models import (
    ARTIFACT_SCHEMA_VERSION,
    ConfidenceValue,
    DecisionQualityClassification,
    DowngradeFlag,
    ExpectedEdgeSource,
    GateOutcome,
    OperatorEngagementState,
    OperatorLegibilityStatus,
    OutcomeInterpretationClassification,
    PolicyAlignmentClassification,
    ProposedSide,
    RecommendedFollowup,
    ResolvedOutcome,
    ScoreDimensions,
    SignalClassificationBand,
    WalletPolicyFit,
)

CASE_SCHEMA_VERSION = "1.0.0"


class StrictCaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MarketObservation(StrictCaseModel):
    observed_price: ConfidenceValue
    best_bid: ConfidenceValue | None = None
    best_ask: ConfidenceValue | None = None
    market_note: str | None = None
    price_unit: Literal["probability", "cents"] = "probability"


class DecisionHorizonInput(StrictCaseModel):
    horizon_hours: float = Field(gt=0.0)
    thesis_valid_until_utc: AwareDatetime
    rationale: str = Field(min_length=1)


class ReviewPlan(StrictCaseModel):
    thesis_quality_assessment: str = Field(min_length=1)
    score_quality_assessment: str = Field(min_length=1)
    timing_quality_assessment: str = Field(min_length=1)
    governance_quality_assessment: str = Field(min_length=1)
    decision_quality_classification: DecisionQualityClassification
    outcome_interpretation_classification: OutcomeInterpretationClassification
    policy_alignment_classification: PolicyAlignmentClassification
    profit_loss_amount: float
    profit_loss_note: str | None = None
    attention_cost_estimate: str = Field(min_length=1)
    abstention_counterfactual: str = Field(min_length=1)
    review_notes: str = Field(min_length=1)
    recommended_followup: RecommendedFollowup


class SimulatedKalshiCase(StrictCaseModel):
    schema_name: Literal["kalshi.mock_candidate_market_case"]
    schema_version: Literal[CASE_SCHEMA_VERSION]
    artifact_schema_version: Literal[ARTIFACT_SCHEMA_VERSION]
    case_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    scenario_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    corr_id: str = Field(min_length=3)
    market_id: str = Field(min_length=2)
    market_title: str = Field(min_length=1)
    resolution_rule_summary: str = Field(min_length=1)
    initial_timestamp_utc: AwareDatetime
    score_timestamp_utc: AwareDatetime
    gate_timestamp_utc: AwareDatetime
    readiness_timestamp_utc: AwareDatetime | None = None
    execution_timestamp_utc: AwareDatetime | None = None
    resolution_timestamp_utc: AwareDatetime
    proposed_side: ProposedSide
    expected_edge_source: ExpectedEdgeSource
    operator_engagement_state: OperatorEngagementState
    market_observation: MarketObservation
    entry_rationale: str = Field(min_length=1)
    decision_horizon: DecisionHorizonInput
    invalidation_condition: str = Field(min_length=1)
    abstention_alternative: str = Field(min_length=1)
    evidence_summary: str = Field(min_length=1)
    evidence_signal: ConfidenceValue
    confidence_signal: ConfidenceValue
    score_dimensions: ScoreDimensions
    downgrade_flags: list[DowngradeFlag] = Field(default_factory=list)
    decay_state: Literal["fresh", "decayed", "revalidated"] = "fresh"
    scoring_notes: str = Field(min_length=1)
    classification_band: SignalClassificationBand
    gate_outcome: GateOutcome
    gate_reasons: list[str] = Field(min_length=1)
    operator_legibility_status: OperatorLegibilityStatus
    wallet_policy_fit: WalletPolicyFit
    resolved_outcome: ResolvedOutcome
    trade_executed: bool
    execution_status: Literal["attempted", "success", "failed"] | None = None
    position_taken: ProposedSide
    review_plan: ReviewPlan

    @model_validator(mode="after")
    def validate_case(self) -> "SimulatedKalshiCase":
        composite = self.score_dimensions.average()
        if self.confidence_signal > composite:
            raise ValueError("confidence_signal cannot exceed composite score")
        if self.confidence_signal > min(
            self.score_dimensions.evidence_strength,
            self.score_dimensions.risk_clarity,
        ):
            raise ValueError("confidence_signal cannot exceed min(evidence_strength, risk_clarity)")
        if self.gate_outcome in ("recommend.execution_ready", "recommend.execution_ready_low_confidence"):
            if self.readiness_timestamp_utc is None:
                raise ValueError("execution-ready cases require readiness_timestamp_utc")
        else:
            if self.readiness_timestamp_utc is not None:
                raise ValueError("non-execution-ready cases must not set readiness_timestamp_utc")
        if self.trade_executed:
            if self.execution_timestamp_utc is None or self.execution_status is None:
                raise ValueError("trade_executed cases require execution timestamp and status")
            if self.position_taken == "none":
                raise ValueError("trade_executed cases must record a position_taken")
        else:
            if self.execution_timestamp_utc is not None or self.execution_status is not None:
                raise ValueError("non-executed cases must not carry execution fields")
            if self.position_taken != "none":
                raise ValueError("non-executed cases must use position_taken='none'")
        return self


def export_case_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "mock_candidate_market_case.schema.json"
    destination.write_text(
        json.dumps(SimulatedKalshiCase.model_json_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"mock_candidate_market_case": destination}
