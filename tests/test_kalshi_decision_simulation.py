from __future__ import annotations

import json
from pathlib import Path

import pytest

from staging.work.kalshi_artifact_models.models import ArtifactBundle
from staging.work.kalshi_decision_simulation.case_models import CASE_SCHEMA_VERSION, SimulatedKalshiCase
from staging.work.kalshi_decision_simulation.pipeline import (
    generate_initial_bundle,
    generate_resolved_bundle,
    load_case,
)


CASE_DIR = Path("staging/work/kalshi_decision_simulation/cases")
SCHEMA_PATH = Path("staging/work/kalshi_decision_simulation/schemas/mock_candidate_market_case.schema.json")


CASE_FILES = [
    "obvious_abstention.json",
    "research_only_candidate.json",
    "execution_ready_low_confidence.json",
    "execution_ready_strong_candidate.json",
    "false_positive_strong_candidate.json",
    "disciplined_losing_trade.json",
    "correct_abstention_in_hindsight.json",
]


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_case_schema_validates(case_name: str) -> None:
    case = load_case(CASE_DIR / case_name)
    assert isinstance(case, SimulatedKalshiCase)


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_initial_bundle_is_valid_and_has_no_review(case_name: str) -> None:
    case = load_case(CASE_DIR / case_name)
    bundle = generate_initial_bundle(case)
    assert isinstance(bundle, ArtifactBundle)
    assert bundle.post_resolution_review_artifact is None


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_resolved_bundle_is_valid_and_replayable(case_name: str) -> None:
    case = load_case(CASE_DIR / case_name)
    first = generate_resolved_bundle(case)
    second = generate_resolved_bundle(case)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


@pytest.mark.parametrize("case_name", CASE_FILES)
def test_resolved_bundle_preserves_upstream_artifacts(case_name: str) -> None:
    case = load_case(CASE_DIR / case_name)
    initial = generate_initial_bundle(case)
    resolved = generate_resolved_bundle(case)
    assert resolved.trade_thesis_artifact == initial.trade_thesis_artifact
    assert resolved.signal_score_record == initial.signal_score_record
    assert resolved.strategy_gate_result == initial.strategy_gate_result
    assert resolved.execution_readiness_receipt == initial.execution_readiness_receipt
    assert resolved.execution_support_receipt == initial.execution_support_receipt


def test_case_schema_export_exists_and_is_versioned() -> None:
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert payload["properties"]["schema_version"]["const"] == CASE_SCHEMA_VERSION


def test_non_ready_cases_do_not_emit_readiness_receipts() -> None:
    for case_name in [
        "obvious_abstention.json",
        "research_only_candidate.json",
        "correct_abstention_in_hindsight.json",
    ]:
        case = load_case(CASE_DIR / case_name)
        bundle = generate_initial_bundle(case)
        assert bundle.execution_readiness_receipt is None


def test_ready_cases_emit_execution_authorized_false() -> None:
    for case_name in [
        "execution_ready_low_confidence.json",
        "execution_ready_strong_candidate.json",
        "false_positive_strong_candidate.json",
        "disciplined_losing_trade.json",
    ]:
        case = load_case(CASE_DIR / case_name)
        bundle = generate_initial_bundle(case)
        assert bundle.execution_readiness_receipt is not None
        assert bundle.execution_readiness_receipt.execution_authorized is False


def test_only_executed_cases_emit_execution_support_receipts() -> None:
    for case_name in CASE_FILES:
        case = load_case(CASE_DIR / case_name)
        bundle = generate_initial_bundle(case)
        if case.trade_executed:
            assert bundle.execution_support_receipt is not None
        else:
            assert bundle.execution_support_receipt is None


def test_review_outcomes_cover_required_hindsight_cases() -> None:
    false_positive = generate_resolved_bundle(load_case(CASE_DIR / "false_positive_strong_candidate.json"))
    disciplined_loss = generate_resolved_bundle(load_case(CASE_DIR / "disciplined_losing_trade.json"))
    correct_abstention = generate_resolved_bundle(load_case(CASE_DIR / "correct_abstention_in_hindsight.json"))

    assert false_positive.post_resolution_review_artifact.outcome_interpretation_classification == "outcome.false_positive_signal"
    assert disciplined_loss.post_resolution_review_artifact.outcome_interpretation_classification == "outcome.variance_penalty"
    assert correct_abstention.post_resolution_review_artifact.outcome_interpretation_classification == "outcome.correct_abstention"
