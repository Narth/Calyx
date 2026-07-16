"""Typed staging models for governed Kalshi artifact contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

ARTIFACT_SCHEMA_VERSION = "1.0.0"

ConfidenceValue = Annotated[float, Field(ge=0.0, le=1.0)]
ScoreValue = Annotated[float, Field(ge=0.0, le=1.0)]
ArtifactId = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")]
CorrId = Annotated[str, Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")]
MarketId = Annotated[str, Field(min_length=2, max_length=128)]
ReadableText = Annotated[str, Field(min_length=1)]

ProposedSide = Literal["yes", "no", "none"]
ResolvedOutcome = Literal["yes", "no", "void", "unresolved"]
ExpectedEdgeSource = Literal[
    "weather_forecast_divergence",
    "event_probability_mismatch",
    "stale_retail_pricing",
    "lagging_reaction_to_public_information",
    "overreaction_underreaction",
    "none",
]
OperatorEngagementState = Literal[
    "operator_absent",
    "operator_present",
    "operator_reviewing",
    "operator_directing",
]
SignalClassificationBand = Literal[
    "abstain.insufficient_edge",
    "abstain.low_quality_candidate",
    "recommend.research_only",
    "recommend.execution_ready_low_confidence",
    "recommend.execution_ready",
]
GateOutcome = Literal[
    "abstain.insufficient_evidence",
    "abstain.low_confidence",
    "abstain.poor_timing",
    "abstain.market_not_suitable",
    "recommend.research_only",
    "recommend.execution_ready_low_confidence",
    "recommend.execution_ready",
]
DowngradeFlag = Literal[
    "weak_evidence_relative_to_confidence",
    "ambiguous_resolution",
    "unclear_risk",
    "poor_timing_stability",
    "signal_decay_applied",
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
DecayState = Literal["fresh", "decayed", "revalidated"]
OperatorLegibilityStatus = Literal["legible", "needs_review", "not_legible"]
WalletPolicyFit = Literal["fit", "borderline", "not_fit"]
PresenceRequirement = Literal["not_required", "required_for_execution"]
NextAllowedAction = Literal["abstain", "continue_research", "operator_review", "operator_intent_required"]
DecisionQualityClassification = Literal[
    "decision_quality.strong",
    "decision_quality.acceptable",
    "decision_quality.weak",
    "decision_quality.unsound",
]
OutcomeInterpretationClassification = Literal[
    "outcome.validated_edge",
    "outcome.partial_validation",
    "outcome.variance_assist",
    "outcome.variance_penalty",
    "outcome.false_positive_signal",
    "outcome.correct_abstention",
    "outcome.missed_opportunity_but_valid_abstention",
]
PolicyAlignmentClassification = Literal[
    "policy.aligned",
    "policy.minor_drift_observed",
    "policy.review_gap_observed",
    "policy.misaligned",
]
RecommendedFollowup = Literal[
    "none",
    "watch_for_pattern",
    "review_signal_thresholds",
    "review_market_selection",
    "review_timing_logic",
    "review_confidence_calibration",
    "review_artifact_completeness",
]


class StrictArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactRef(StrictArtifactModel):
    artifact_type: Literal[
        "trade_thesis_artifact",
        "signal_score_record",
        "strategy_gate_result",
        "execution_readiness_receipt",
        "execution_support_receipt",
        "post_resolution_review_artifact",
    ]
    artifact_id: ArtifactId


class ArtifactBase(StrictArtifactModel):
    schema_name: str
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION]
    artifact_type: str
    artifact_id: ArtifactId
    corr_id: CorrId
    timestamp_utc: AwareDatetime
    market_id: MarketId


class PriceContext(StrictArtifactModel):
    observed_price: ConfidenceValue
    price_unit: Literal["probability", "cents"]
    best_bid: ConfidenceValue | None = None
    best_ask: ConfidenceValue | None = None
    market_note: str | None = None


class DecisionHorizon(StrictArtifactModel):
    horizon_hours: Annotated[float, Field(gt=0.0)]
    thesis_valid_until_utc: AwareDatetime
    rationale: ReadableText


class ScoreDimensions(StrictArtifactModel):
    evidence_strength: ScoreValue
    mispricing_potential: ScoreValue
    timing_quality: ScoreValue
    resolution_clarity: ScoreValue
    liquidity_tradability: ScoreValue
    decision_horizon_fit: ScoreValue
    risk_clarity: ScoreValue

    def average(self) -> float:
        total = (
            self.evidence_strength
            + self.mispricing_potential
            + self.timing_quality
            + self.resolution_clarity
            + self.liquidity_tradability
            + self.decision_horizon_fit
            + self.risk_clarity
        )
        return total / 7.0


class ProfitLossResult(StrictArtifactModel):
    currency: Literal["USD"]
    amount: float
    note: str | None = None


class TradeThesisArtifact(ArtifactBase):
    schema_name: Literal["kalshi.trade_thesis_artifact"]
    artifact_type: Literal["trade_thesis_artifact"] = "trade_thesis_artifact"
    market_title: ReadableText
    resolution_rule_summary: ReadableText
    proposed_side: ProposedSide
    price_context: PriceContext
    entry_rationale: ReadableText
    expected_edge_source: ExpectedEdgeSource
    decision_horizon: DecisionHorizon
    invalidation_condition: ReadableText
    abstention_alternative: ReadableText
    evidence_summary: ReadableText
    confidence_signal: ConfidenceValue
    evidence_signal: ConfidenceValue
    operator_engagement_state: OperatorEngagementState


class SignalScoreRecord(ArtifactBase):
    schema_name: Literal["kalshi.signal_score_record"]
    artifact_type: Literal["signal_score_record"] = "signal_score_record"
    score_dimensions: ScoreDimensions
    composite_score: ScoreValue
    classification_band: SignalClassificationBand
    confidence_signal: ConfidenceValue
    downgrade_flags: list[DowngradeFlag] = Field(default_factory=list)
    decay_state: DecayState
    evidence_summary: ReadableText
    scoring_notes: ReadableText

    @model_validator(mode="after")
    def validate_scores(self) -> "SignalScoreRecord":
        if abs(self.composite_score - self.score_dimensions.average()) > 1e-9:
            raise ValueError("composite_score must equal the simple average of score_dimensions")
        if self.confidence_signal > self.composite_score:
            raise ValueError("confidence_signal cannot exceed composite_score")
        if self.confidence_signal > min(
            self.score_dimensions.evidence_strength,
            self.score_dimensions.risk_clarity,
        ):
            raise ValueError("confidence_signal cannot exceed min(evidence_strength, risk_clarity)")
        return self


class StrategyGateResult(ArtifactBase):
    schema_name: Literal["kalshi.strategy_gate_result"]
    artifact_type: Literal["strategy_gate_result"] = "strategy_gate_result"
    gate_outcome: GateOutcome
    gate_reasons: list[ReadableText] = Field(min_length=1)
    thesis_ref: ArtifactRef
    score_ref: ArtifactRef
    operator_legibility_status: OperatorLegibilityStatus
    wallet_policy_fit: WalletPolicyFit
    presence_requirement: PresenceRequirement
    next_allowed_action: NextAllowedAction

    @model_validator(mode="after")
    def validate_refs_and_actions(self) -> "StrategyGateResult":
        if self.thesis_ref.artifact_type != "trade_thesis_artifact":
            raise ValueError("thesis_ref must point to trade_thesis_artifact")
        if self.score_ref.artifact_type != "signal_score_record":
            raise ValueError("score_ref must point to signal_score_record")
        if self.gate_outcome in ("recommend.execution_ready", "recommend.execution_ready_low_confidence"):
            if self.presence_requirement != "required_for_execution":
                raise ValueError("execution-ready gate outcomes require presence_requirement=required_for_execution")
            if self.next_allowed_action != "operator_intent_required":
                raise ValueError("execution-ready gate outcomes require next_allowed_action=operator_intent_required")
        return self


class ExecutionReadinessReceipt(ArtifactBase):
    schema_name: Literal["kalshi.execution_readiness_receipt"]
    artifact_type: Literal["execution_readiness_receipt"] = "execution_readiness_receipt"
    execution_readiness_class: Literal[
        "recommend.execution_ready_low_confidence",
        "recommend.execution_ready",
    ]
    thesis_ref: ArtifactRef
    score_ref: ArtifactRef
    gate_result_ref: ArtifactRef
    presence_gate_required: Literal[True] = True
    wallet_policy_required: Literal[True] = True
    execution_authorized: Literal[False] = False
    operator_action_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_refs(self) -> "ExecutionReadinessReceipt":
        if self.thesis_ref.artifact_type != "trade_thesis_artifact":
            raise ValueError("thesis_ref must point to trade_thesis_artifact")
        if self.score_ref.artifact_type != "signal_score_record":
            raise ValueError("score_ref must point to signal_score_record")
        if self.gate_result_ref.artifact_type != "strategy_gate_result":
            raise ValueError("gate_result_ref must point to strategy_gate_result")
        return self


class ExecutionSupportReceipt(ArtifactBase):
    """Staging-only placeholder for downstream execution references."""

    schema_name: Literal["kalshi.execution_support_receipt"]
    artifact_type: Literal["execution_support_receipt"] = "execution_support_receipt"
    execution_status: Literal["attempted", "success", "failed"]
    execution_mode: Literal["staging_only"] = "staging_only"
    requested_side: Literal["yes", "no"]
    operator_action_recorded: Literal[True] = True
    note: ReadableText


class PostResolutionReviewArtifact(ArtifactBase):
    schema_name: Literal["kalshi.post_resolution_review_artifact"]
    artifact_type: Literal["post_resolution_review_artifact"] = "post_resolution_review_artifact"
    market_title: ReadableText
    resolved_outcome: ResolvedOutcome
    position_taken: ProposedSide
    trade_executed: bool
    thesis_ref: ArtifactRef | None = None
    score_ref: ArtifactRef | None = None
    gate_result_ref: ArtifactRef | None = None
    execution_ref: ArtifactRef | None = None
    original_composite_score: ScoreValue
    original_gate_outcome: GateOutcome
    thesis_quality_assessment: ReadableText
    score_quality_assessment: ReadableText
    timing_quality_assessment: ReadableText
    governance_quality_assessment: ReadableText
    decision_quality_classification: DecisionQualityClassification
    outcome_interpretation_classification: OutcomeInterpretationClassification
    policy_alignment_classification: PolicyAlignmentClassification
    profit_loss_result: ProfitLossResult
    attention_cost_estimate: ReadableText
    abstention_counterfactual: ReadableText
    review_notes: ReadableText
    recommended_followup: RecommendedFollowup

    @model_validator(mode="after")
    def validate_review(self) -> "PostResolutionReviewArtifact":
        if self.trade_executed and self.position_taken == "none":
            raise ValueError("trade_executed reviews must record a position_taken")
        if not self.trade_executed and self.position_taken != "none":
            raise ValueError("non-executed reviews must use position_taken='none'")
        if self.trade_executed and self.execution_ref is None:
            raise ValueError("trade_executed reviews must include execution_ref")
        if not self.trade_executed and self.execution_ref is not None:
            raise ValueError("non-executed reviews must not include execution_ref")
        return self


class ArtifactBundle(StrictArtifactModel):
    scenario_name: ReadableText
    description: ReadableText
    trade_thesis_artifact: TradeThesisArtifact | None = None
    signal_score_record: SignalScoreRecord | None = None
    strategy_gate_result: StrategyGateResult | None = None
    execution_readiness_receipt: ExecutionReadinessReceipt | None = None
    execution_support_receipt: ExecutionSupportReceipt | None = None
    post_resolution_review_artifact: PostResolutionReviewArtifact | None = None

    @model_validator(mode="after")
    def validate_bundle(self) -> "ArtifactBundle":
        artifacts = [
            artifact
            for artifact in (
                self.trade_thesis_artifact,
                self.signal_score_record,
                self.strategy_gate_result,
                self.execution_readiness_receipt,
                self.execution_support_receipt,
                self.post_resolution_review_artifact,
            )
            if artifact is not None
        ]
        if not artifacts:
            raise ValueError("artifact bundle must contain at least one artifact")

        corr_ids = {artifact.corr_id for artifact in artifacts}
        if len(corr_ids) != 1:
            raise ValueError("all artifacts in a bundle must share the same corr_id")

        market_ids = {artifact.market_id for artifact in artifacts}
        if len(market_ids) != 1:
            raise ValueError("all artifacts in a bundle must share the same market_id")

        artifact_map = {artifact.artifact_id: artifact for artifact in artifacts}
        if len(artifact_map) != len(artifacts):
            raise ValueError("artifact_id values must be unique within a bundle")

        if self.strategy_gate_result and not (self.trade_thesis_artifact and self.signal_score_record):
            raise ValueError("strategy_gate_result requires thesis and score artifacts in the same bundle")
        if self.execution_readiness_receipt and not (
            self.trade_thesis_artifact and self.signal_score_record and self.strategy_gate_result
        ):
            raise ValueError("execution_readiness_receipt requires thesis, score, and gate artifacts")

        self._ensure_ref(self.strategy_gate_result.thesis_ref if self.strategy_gate_result else None, artifact_map)
        self._ensure_ref(self.strategy_gate_result.score_ref if self.strategy_gate_result else None, artifact_map)

        if self.execution_readiness_receipt:
            self._ensure_ref(self.execution_readiness_receipt.thesis_ref, artifact_map)
            self._ensure_ref(self.execution_readiness_receipt.score_ref, artifact_map)
            gate = self._ensure_ref(self.execution_readiness_receipt.gate_result_ref, artifact_map)
            assert isinstance(gate, StrategyGateResult)
            if gate.gate_outcome != self.execution_readiness_receipt.execution_readiness_class:
                raise ValueError("execution_readiness_class must match the referenced gate_outcome")

        if self.post_resolution_review_artifact:
            review = self.post_resolution_review_artifact
            if review.thesis_ref is not None:
                self._ensure_ref(review.thesis_ref, artifact_map)
            if review.score_ref is not None:
                score = self._ensure_ref(review.score_ref, artifact_map)
                assert isinstance(score, SignalScoreRecord)
                if abs(score.composite_score - review.original_composite_score) > 1e-9:
                    raise ValueError("post-resolution review must preserve original_composite_score")
            if review.gate_result_ref is not None:
                gate = self._ensure_ref(review.gate_result_ref, artifact_map)
                assert isinstance(gate, StrategyGateResult)
                if gate.gate_outcome != review.original_gate_outcome:
                    raise ValueError("post-resolution review must preserve original_gate_outcome")
            if review.execution_ref is not None:
                self._ensure_ref(review.execution_ref, artifact_map)

        return self

    @staticmethod
    def _ensure_ref(ref: ArtifactRef | None, artifact_map: dict[str, ArtifactBase]) -> ArtifactBase | None:
        if ref is None:
            return None
        artifact = artifact_map.get(ref.artifact_id)
        if artifact is None:
            raise ValueError(f"unresolved artifact reference: {ref.artifact_id}")
        if artifact.artifact_type != ref.artifact_type:
            raise ValueError(f"artifact reference type mismatch for {ref.artifact_id}")
        return artifact


PRIMARY_MODELS: dict[str, type[ArtifactBase]] = {
    "trade_thesis_artifact": TradeThesisArtifact,
    "signal_score_record": SignalScoreRecord,
    "strategy_gate_result": StrategyGateResult,
    "execution_readiness_receipt": ExecutionReadinessReceipt,
    "post_resolution_review_artifact": PostResolutionReviewArtifact,
}


def export_primary_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for artifact_type, model in PRIMARY_MODELS.items():
        destination = output_dir / f"{artifact_type}.schema.json"
        payload = model.model_json_schema()
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[artifact_type] = destination
    return written
