from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.kalshi_artifact_models.models import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactBundle,
    ExecutionReadinessReceipt,
    PRIMARY_MODELS,
)


FIXTURE_DIR = Path("staging/work/kalshi_artifact_models/fixtures")
SCHEMA_DIR = Path("staging/work/kalshi_artifact_models/schemas")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "fixture_name",
    [
      "correct_abstention.json",
      "research_only_recommendation.json",
      "execution_ready_low_confidence_recommendation.json",
      "execution_ready_recommendation.json",
      "variance_assisted_win.json",
      "disciplined_loss.json",
      "correct_abstention_after_resolution.json",
    ],
)
def test_fixture_bundle_validates(fixture_name: str) -> None:
    payload = _load_json(FIXTURE_DIR / fixture_name)
    bundle = ArtifactBundle.model_validate(payload)
    assert bundle is not None


def test_primary_schema_exports_exist_and_match_version() -> None:
    for artifact_type in PRIMARY_MODELS:
        schema_path = SCHEMA_DIR / f"{artifact_type}.schema.json"
        payload = _load_json(schema_path)
        assert payload["properties"]["schema_version"]["const"] == ARTIFACT_SCHEMA_VERSION


def test_execution_ready_does_not_confer_execution_authority() -> None:
    payload = _load_json(FIXTURE_DIR / "execution_ready_recommendation.json")
    receipt_payload = payload["execution_readiness_receipt"]
    receipt_payload["execution_authorized"] = True
    with pytest.raises(ValidationError):
        ExecutionReadinessReceipt.model_validate(receipt_payload)


def test_schema_version_required_on_every_artifact() -> None:
    payload = _load_json(FIXTURE_DIR / "correct_abstention.json")
    del payload["trade_thesis_artifact"]["schema_version"]
    with pytest.raises(ValidationError):
        ArtifactBundle.model_validate(payload)


def test_gate_outcome_enum_is_constrained() -> None:
    payload = _load_json(FIXTURE_DIR / "research_only_recommendation.json")
    payload["strategy_gate_result"]["gate_outcome"] = "looks.decent"
    with pytest.raises(ValidationError):
        ArtifactBundle.model_validate(payload)


def test_cross_artifact_references_must_resolve() -> None:
    payload = _load_json(FIXTURE_DIR / "execution_ready_recommendation.json")
    payload["execution_readiness_receipt"]["gate_result_ref"]["artifact_id"] = "gate.missing"
    with pytest.raises(ValidationError):
        ArtifactBundle.model_validate(payload)


def test_downgrade_flags_preserved() -> None:
    payload = _load_json(FIXTURE_DIR / "correct_abstention_after_resolution.json")
    bundle = ArtifactBundle.model_validate(payload)
    assert bundle.signal_score_record is not None
    assert bundle.signal_score_record.downgrade_flags == [
        "weak_evidence_relative_to_confidence",
        "unclear_risk",
    ]


def test_execution_readiness_class_matches_gate_outcome() -> None:
    payload = _load_json(FIXTURE_DIR / "execution_ready_low_confidence_recommendation.json")
    payload["strategy_gate_result"]["gate_outcome"] = "recommend.execution_ready"
    with pytest.raises(ValidationError):
        ArtifactBundle.model_validate(payload)


def test_review_preserves_original_gate_outcome() -> None:
    payload = _load_json(FIXTURE_DIR / "disciplined_loss.json")
    payload["post_resolution_review_artifact"]["original_gate_outcome"] = "abstain.low_confidence"
    with pytest.raises(ValidationError):
        ArtifactBundle.model_validate(payload)
