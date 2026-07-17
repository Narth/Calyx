"""Deterministic staging pipeline for synthetic Kalshi decision cases."""

from __future__ import annotations

import json
from pathlib import Path

from staging.work.kalshi_artifact_models.models import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactBundle,
    ArtifactRef,
    ExecutionReadinessReceipt,
    ExecutionSupportReceipt,
    PostResolutionReviewArtifact,
    PriceContext,
    ProfitLossResult,
    SignalScoreRecord,
    StrategyGateResult,
    TradeThesisArtifact,
    DecisionHorizon,
)
from staging.work.kalshi_decision_simulation.case_models import SimulatedKalshiCase


def load_case(path: Path) -> SimulatedKalshiCase:
    return SimulatedKalshiCase.model_validate_json(path.read_text(encoding="utf-8"))


def load_case_bundle(path: Path, *, include_resolution: bool) -> ArtifactBundle:
    case = load_case(path)
    if include_resolution:
        return generate_resolved_bundle(case)
    return generate_initial_bundle(case)


def generate_initial_bundle(case: SimulatedKalshiCase) -> ArtifactBundle:
    thesis = _build_thesis(case)
    score = _build_score(case)
    gate = _build_gate(case, thesis, score)
    readiness = _build_readiness(case, thesis, score, gate)
    execution = _build_execution(case)
    return ArtifactBundle(
        scenario_name=case.scenario_name,
        description=case.description,
        trade_thesis_artifact=thesis,
        signal_score_record=score,
        strategy_gate_result=gate,
        execution_readiness_receipt=readiness,
        execution_support_receipt=execution,
        post_resolution_review_artifact=None,
    )


def generate_resolved_bundle(case: SimulatedKalshiCase) -> ArtifactBundle:
    initial = generate_initial_bundle(case)
    review = _build_review(case, initial)
    return ArtifactBundle(
        scenario_name=case.scenario_name,
        description=case.description,
        trade_thesis_artifact=initial.trade_thesis_artifact,
        signal_score_record=initial.signal_score_record,
        strategy_gate_result=initial.strategy_gate_result,
        execution_readiness_receipt=initial.execution_readiness_receipt,
        execution_support_receipt=initial.execution_support_receipt,
        post_resolution_review_artifact=review,
    )


def _build_thesis(case: SimulatedKalshiCase) -> TradeThesisArtifact:
    return TradeThesisArtifact(
        schema_name="kalshi.trade_thesis_artifact",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="trade_thesis_artifact",
        artifact_id=f"{case.case_id}.thesis",
        corr_id=case.corr_id,
        timestamp_utc=case.initial_timestamp_utc,
        market_id=case.market_id,
        market_title=case.market_title,
        resolution_rule_summary=case.resolution_rule_summary,
        proposed_side=case.proposed_side,
        price_context=PriceContext(
            observed_price=case.market_observation.observed_price,
            price_unit=case.market_observation.price_unit,
            best_bid=case.market_observation.best_bid,
            best_ask=case.market_observation.best_ask,
            market_note=case.market_observation.market_note,
        ),
        entry_rationale=case.entry_rationale,
        expected_edge_source=case.expected_edge_source,
        decision_horizon=DecisionHorizon(
            horizon_hours=case.decision_horizon.horizon_hours,
            thesis_valid_until_utc=case.decision_horizon.thesis_valid_until_utc,
            rationale=case.decision_horizon.rationale,
        ),
        invalidation_condition=case.invalidation_condition,
        abstention_alternative=case.abstention_alternative,
        evidence_summary=case.evidence_summary,
        confidence_signal=case.confidence_signal,
        evidence_signal=case.evidence_signal,
        operator_engagement_state=case.operator_engagement_state,
    )


def _build_score(case: SimulatedKalshiCase) -> SignalScoreRecord:
    return SignalScoreRecord(
        schema_name="kalshi.signal_score_record",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="signal_score_record",
        artifact_id=f"{case.case_id}.score",
        corr_id=case.corr_id,
        timestamp_utc=case.score_timestamp_utc,
        market_id=case.market_id,
        score_dimensions=case.score_dimensions,
        composite_score=case.score_dimensions.average(),
        classification_band=case.classification_band,
        confidence_signal=case.confidence_signal,
        downgrade_flags=case.downgrade_flags,
        decay_state=case.decay_state,
        evidence_summary=case.evidence_summary,
        scoring_notes=case.scoring_notes,
    )


def _build_gate(
    case: SimulatedKalshiCase,
    thesis: TradeThesisArtifact,
    score: SignalScoreRecord,
) -> StrategyGateResult:
    presence_requirement = "required_for_execution" if case.gate_outcome.startswith("recommend.execution_ready") else "not_required"
    next_allowed_action = "operator_intent_required" if case.gate_outcome.startswith("recommend.execution_ready") else (
        "continue_research" if case.gate_outcome == "recommend.research_only" else "abstain"
    )
    return StrategyGateResult(
        schema_name="kalshi.strategy_gate_result",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="strategy_gate_result",
        artifact_id=f"{case.case_id}.gate",
        corr_id=case.corr_id,
        timestamp_utc=case.gate_timestamp_utc,
        market_id=case.market_id,
        gate_outcome=case.gate_outcome,
        gate_reasons=case.gate_reasons,
        thesis_ref=ArtifactRef(artifact_type=thesis.artifact_type, artifact_id=thesis.artifact_id),
        score_ref=ArtifactRef(artifact_type=score.artifact_type, artifact_id=score.artifact_id),
        operator_legibility_status=case.operator_legibility_status,
        wallet_policy_fit=case.wallet_policy_fit,
        presence_requirement=presence_requirement,
        next_allowed_action=next_allowed_action,
    )


def _build_readiness(
    case: SimulatedKalshiCase,
    thesis: TradeThesisArtifact,
    score: SignalScoreRecord,
    gate: StrategyGateResult,
) -> ExecutionReadinessReceipt | None:
    if case.gate_outcome not in ("recommend.execution_ready_low_confidence", "recommend.execution_ready"):
        return None
    return ExecutionReadinessReceipt(
        schema_name="kalshi.execution_readiness_receipt",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="execution_readiness_receipt",
        artifact_id=f"{case.case_id}.readiness",
        corr_id=case.corr_id,
        timestamp_utc=case.readiness_timestamp_utc,
        market_id=case.market_id,
        execution_readiness_class=case.gate_outcome,
        thesis_ref=ArtifactRef(artifact_type=thesis.artifact_type, artifact_id=thesis.artifact_id),
        score_ref=ArtifactRef(artifact_type=score.artifact_type, artifact_id=score.artifact_id),
        gate_result_ref=ArtifactRef(artifact_type=gate.artifact_type, artifact_id=gate.artifact_id),
        presence_gate_required=True,
        wallet_policy_required=True,
        execution_authorized=False,
        operator_action_required=True,
    )


def _build_execution(case: SimulatedKalshiCase) -> ExecutionSupportReceipt | None:
    if not case.trade_executed:
        return None
    requested_side = "yes" if case.position_taken == "yes" else "no"
    return ExecutionSupportReceipt(
        schema_name="kalshi.execution_support_receipt",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="execution_support_receipt",
        artifact_id=f"{case.case_id}.execution",
        corr_id=case.corr_id,
        timestamp_utc=case.execution_timestamp_utc,
        market_id=case.market_id,
        execution_status=case.execution_status,
        execution_mode="staging_only",
        requested_side=requested_side,
        operator_action_recorded=True,
        note="Deterministic staging-only execution placeholder. No live order path exists.",
    )


def _build_review(case: SimulatedKalshiCase, initial: ArtifactBundle) -> PostResolutionReviewArtifact:
    return PostResolutionReviewArtifact(
        schema_name="kalshi.post_resolution_review_artifact",
        schema_version=ARTIFACT_SCHEMA_VERSION,
        artifact_type="post_resolution_review_artifact",
        artifact_id=f"{case.case_id}.review",
        corr_id=case.corr_id,
        timestamp_utc=case.resolution_timestamp_utc,
        market_id=case.market_id,
        market_title=case.market_title,
        resolved_outcome=case.resolved_outcome,
        position_taken=case.position_taken,
        trade_executed=case.trade_executed,
        thesis_ref=ArtifactRef(
            artifact_type=initial.trade_thesis_artifact.artifact_type,
            artifact_id=initial.trade_thesis_artifact.artifact_id,
        ) if initial.trade_thesis_artifact else None,
        score_ref=ArtifactRef(
            artifact_type=initial.signal_score_record.artifact_type,
            artifact_id=initial.signal_score_record.artifact_id,
        ) if initial.signal_score_record else None,
        gate_result_ref=ArtifactRef(
            artifact_type=initial.strategy_gate_result.artifact_type,
            artifact_id=initial.strategy_gate_result.artifact_id,
        ) if initial.strategy_gate_result else None,
        execution_ref=ArtifactRef(
            artifact_type=initial.execution_support_receipt.artifact_type,
            artifact_id=initial.execution_support_receipt.artifact_id,
        ) if initial.execution_support_receipt else None,
        original_composite_score=initial.signal_score_record.composite_score,
        original_gate_outcome=initial.strategy_gate_result.gate_outcome,
        thesis_quality_assessment=case.review_plan.thesis_quality_assessment,
        score_quality_assessment=case.review_plan.score_quality_assessment,
        timing_quality_assessment=case.review_plan.timing_quality_assessment,
        governance_quality_assessment=case.review_plan.governance_quality_assessment,
        decision_quality_classification=case.review_plan.decision_quality_classification,
        outcome_interpretation_classification=case.review_plan.outcome_interpretation_classification,
        policy_alignment_classification=case.review_plan.policy_alignment_classification,
        profit_loss_result=ProfitLossResult(
            currency="USD",
            amount=case.review_plan.profit_loss_amount,
            note=case.review_plan.profit_loss_note,
        ),
        attention_cost_estimate=case.review_plan.attention_cost_estimate,
        abstention_counterfactual=case.review_plan.abstention_counterfactual,
        review_notes=case.review_plan.review_notes,
        recommended_followup=case.review_plan.recommended_followup,
    )
