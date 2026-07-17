from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.kalshi_artifact_models.models import ArtifactBundle
from staging.work.kalshi_decision_simulation.case_models import SimulatedKalshiCase
from staging.work.kalshi_decision_simulation.pipeline import generate_resolved_bundle
from staging.work.weather_research_models.integration import WeatherToKalshiCaseInput
from staging.work.weather_research_models.models import (
    WeatherDivergenceAssessment,
    WeatherForecastBundle,
    WeatherResearchSummary,
    WeatherSourceSnapshot,
)
from staging.work.weather_signal_interpretation_models.interpreter import (
    WeatherInterpretationContext,
    build_interpreted_weather_case,
    derive_weather_signal_interpretation,
)
from staging.work.weather_signal_interpretation_models.models import (
    PRIMARY_WEATHER_INTERPRETATION_MODELS,
    WEATHER_INTERPRETATION_SCHEMA_VERSION,
    WeatherSignalInterpretation,
)


FIXTURE_DIR = Path("staging/work/weather_signal_interpretation_models/fixtures")
SCHEMA_DIR = Path("staging/work/weather_signal_interpretation_models/schemas")
FIXTURE_FILES = [
    "strong_temperature_support.json",
    "temperature_threshold_ambiguity.json",
    "precipitation_supportive_divergence.json",
    "precipitation_high_disagreement.json",
    "stale_bundle_downgrade_case.json",
    "mixed_moderate_support_force_research_only.json",
    "edge_trap_marginal_edge.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_fixture(name: str) -> dict:
    payload = _load_json(FIXTURE_DIR / name)
    payload["source_snapshots"] = [WeatherSourceSnapshot.model_validate(item) for item in payload["source_snapshots"]]
    payload["forecast_bundle"] = WeatherForecastBundle.model_validate(payload["forecast_bundle"])
    payload["weather_divergence_assessment"] = WeatherDivergenceAssessment.model_validate(payload["weather_divergence_assessment"])
    payload["weather_research_summary"] = WeatherResearchSummary.model_validate(payload["weather_research_summary"])
    payload["interpretation_context"] = WeatherInterpretationContext.model_validate(payload["interpretation_context"])
    payload["weather_signal_interpretation"] = WeatherSignalInterpretation.model_validate(payload["weather_signal_interpretation"])
    payload["kalshi_input"] = WeatherToKalshiCaseInput.model_validate(payload["kalshi_input"])
    payload["kalshi_case"] = SimulatedKalshiCase.model_validate(payload["kalshi_case"])
    return payload


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_bundle_validates(fixture_name: str) -> None:
    payload = _validate_fixture(fixture_name)
    interpretation = payload["weather_signal_interpretation"]
    bundle = payload["forecast_bundle"]
    assert interpretation.source_bundle_ref == bundle.bundle_id


def test_schema_export_exists_and_is_versioned() -> None:
    for artifact_type in PRIMARY_WEATHER_INTERPRETATION_MODELS:
        payload = _load_json(SCHEMA_DIR / f"{artifact_type}.schema.json")
        assert payload["properties"]["schema_version"]["const"] == WEATHER_INTERPRETATION_SCHEMA_VERSION


def test_required_fields_present() -> None:
    payload = _load_json(FIXTURE_DIR / "strong_temperature_support.json")
    del payload["weather_signal_interpretation"]["weather_support_band"]
    with pytest.raises(ValidationError):
        WeatherSignalInterpretation.model_validate(payload["weather_signal_interpretation"])


def test_enums_strictly_enforced() -> None:
    payload = _load_json(FIXTURE_DIR / "strong_temperature_support.json")
    payload["weather_signal_interpretation"]["weather_support_band"] = "confident"
    with pytest.raises(ValidationError):
        WeatherSignalInterpretation.model_validate(payload["weather_signal_interpretation"])


def test_downgrade_flags_present_for_ambiguity_disagreement_and_staleness() -> None:
    ambiguity = _validate_fixture("temperature_threshold_ambiguity.json")["weather_signal_interpretation"]
    disagreement = _validate_fixture("precipitation_high_disagreement.json")["weather_signal_interpretation"]
    stale = _validate_fixture("stale_bundle_downgrade_case.json")["weather_signal_interpretation"]

    assert "temperature.threshold_ambiguity" in ambiguity.weather_downgrade_flags
    assert "precipitation.high_disagreement" in disagreement.weather_downgrade_flags
    assert any(flag.endswith(".stale_bundle") for flag in stale.weather_downgrade_flags)


def test_strong_support_cannot_exist_with_ambiguity_or_high_disagreement() -> None:
    payload = _load_json(FIXTURE_DIR / "temperature_threshold_ambiguity.json")
    payload["weather_signal_interpretation"]["weather_support_band"] = "strong"
    with pytest.raises(ValidationError):
        WeatherSignalInterpretation.model_validate(payload["weather_signal_interpretation"])

    payload = _load_json(FIXTURE_DIR / "precipitation_high_disagreement.json")
    payload["weather_signal_interpretation"]["weather_support_band"] = "strong"
    with pytest.raises(ValidationError):
        WeatherSignalInterpretation.model_validate(payload["weather_signal_interpretation"])


def test_stale_bundle_reduces_support_and_applies_downgrades() -> None:
    interpretation = _validate_fixture("stale_bundle_downgrade_case.json")["weather_signal_interpretation"]
    assert interpretation.freshness_assessment == "stale"
    assert interpretation.weather_support_band == "weak"
    assert any(flag.endswith(".stale_bundle") for flag in interpretation.weather_downgrade_flags)


def test_downstream_effects_remain_bounded_and_non_authorizing() -> None:
    interpretation = _validate_fixture("mixed_moderate_support_force_research_only.json")["weather_signal_interpretation"]
    assert "force_research_only_ceiling" in interpretation.downstream_signal_effects
    blob = json.dumps(interpretation.model_dump(mode="json"))
    assert "execution_ready" not in blob
    assert "authorized" not in blob


@pytest.mark.parametrize(
    ("fixture_name", "expected_band", "expected_classification"),
    [
        ("strong_temperature_support.json", "strong", "recommend.execution_ready_low_confidence"),
        ("temperature_threshold_ambiguity.json", "weak", "recommend.research_only"),
        ("precipitation_supportive_divergence.json", "moderate", "recommend.research_only"),
        ("precipitation_high_disagreement.json", "weak", "recommend.research_only"),
        ("stale_bundle_downgrade_case.json", "weak", "recommend.research_only"),
        ("mixed_moderate_support_force_research_only.json", "moderate", "recommend.research_only"),
        ("edge_trap_marginal_edge.json", "moderate", "recommend.research_only"),
    ],
)
def test_interpretation_bridge_integrates_without_schema_drift(
    fixture_name: str,
    expected_band: str,
    expected_classification: str,
) -> None:
    payload = _validate_fixture(fixture_name)
    case = build_interpreted_weather_case(
        source_snapshots=payload["source_snapshots"],
        forecast_bundle=payload["forecast_bundle"],
        divergence_assessment=payload["weather_divergence_assessment"],
        research_summary=payload["weather_research_summary"],
        interpretation=payload["weather_signal_interpretation"],
        kalshi_input=payload["kalshi_input"],
    )
    interpretation = payload["weather_signal_interpretation"]
    assert interpretation.weather_support_band == expected_band
    assert case.classification_band == expected_classification
    assert case == payload["kalshi_case"]
    assert interpretation.source_bundle_ref in case.scoring_notes


def test_weather_downgrade_flags_propagate_into_signal_score_record() -> None:
    payload = _validate_fixture("edge_trap_marginal_edge.json")
    resolved = generate_resolved_bundle(payload["kalshi_case"])
    assert isinstance(resolved, ArtifactBundle)
    assert resolved.signal_score_record is not None
    assert "temperature.marginal_edge" in resolved.signal_score_record.downgrade_flags


def test_interpretation_artifact_rederives_cleanly_from_bundle() -> None:
    payload = _validate_fixture("precipitation_high_disagreement.json")
    rederived = derive_weather_signal_interpretation(
        forecast_bundle=payload["forecast_bundle"],
        context=payload["interpretation_context"],
    )
    assert rederived == payload["weather_signal_interpretation"]


def test_full_pipeline_to_post_resolution_review_preserves_bundle_reference() -> None:
    payload = _validate_fixture("strong_temperature_support.json")
    resolved = generate_resolved_bundle(payload["kalshi_case"])
    assert resolved.trade_thesis_artifact is not None
    assert resolved.signal_score_record is not None
    assert resolved.post_resolution_review_artifact is not None
    assert payload["weather_signal_interpretation"].source_bundle_ref in resolved.trade_thesis_artifact.invalidation_condition
    assert "weather_interpretation_support_band=strong" in resolved.strategy_gate_result.gate_reasons[-1]
