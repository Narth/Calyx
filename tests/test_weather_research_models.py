from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from staging.work.kalshi_artifact_models.models import ArtifactBundle
from staging.work.kalshi_decision_simulation.pipeline import generate_resolved_bundle
from staging.work.weather_research_models.integration import (
    WeatherToKalshiCaseInput,
    build_weather_supported_case,
)
from staging.work.weather_research_models.models import (
    PRIMARY_WEATHER_MODELS,
    WEATHER_SCHEMA_VERSION,
    WeatherDivergenceAssessment,
    WeatherForecastBundle,
    WeatherResearchSummary,
    WeatherSourceSnapshot,
)


FIXTURE_DIR = Path("staging/work/weather_research_models/fixtures")
SCHEMA_DIR = Path("staging/work/weather_research_models/schemas")
FIXTURE_FILES = [
    "temperature_strong_agreement.json",
    "temperature_threshold_ambiguity.json",
    "precipitation_supportive_divergence.json",
    "precipitation_high_source_disagreement.json",
    "stale_forecast_bundle_requiring_downgrade.json",
    "non_actionable_weather_case_despite_interesting_narrative.json",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_fixture(name: str) -> dict:
    return _load_json(FIXTURE_DIR / name)


def _validate_fixture(name: str) -> tuple[list[WeatherSourceSnapshot], WeatherForecastBundle, WeatherDivergenceAssessment, WeatherResearchSummary, WeatherToKalshiCaseInput]:
    payload = _load_fixture(name)
    snapshots = [WeatherSourceSnapshot.model_validate(item) for item in payload["source_snapshots"]]
    bundle = WeatherForecastBundle.model_validate(payload["forecast_bundle"])
    divergence = WeatherDivergenceAssessment.model_validate(payload["weather_divergence_assessment"])
    summary = WeatherResearchSummary.model_validate(payload["weather_research_summary"])
    kalshi_input = WeatherToKalshiCaseInput.model_validate(payload["kalshi_input"])
    return snapshots, bundle, divergence, summary, kalshi_input


@pytest.mark.parametrize("fixture_name", FIXTURE_FILES)
def test_fixture_artifacts_validate(fixture_name: str) -> None:
    snapshots, bundle, divergence, summary, _ = _validate_fixture(fixture_name)
    assert len(snapshots) >= 2
    assert bundle.bundle_id == divergence.bundle_ref
    assert summary.forecast_bundle_ref == bundle.bundle_id
    assert summary.divergence_assessment_ref == divergence.assessment_id


def test_weather_schema_exports_exist_and_match_version() -> None:
    for artifact_type in PRIMARY_WEATHER_MODELS:
        schema_path = SCHEMA_DIR / f"{artifact_type}.schema.json"
        payload = _load_json(schema_path)
        assert payload["properties"]["schema_version"]["const"] == WEATHER_SCHEMA_VERSION


def test_required_source_attribution_fields_enforced() -> None:
    payload = _load_fixture("temperature_strong_agreement.json")
    del payload["source_snapshots"][0]["source_name"]
    with pytest.raises(ValidationError):
        WeatherSourceSnapshot.model_validate(payload["source_snapshots"][0])


def test_capture_timestamp_required() -> None:
    payload = _load_fixture("temperature_strong_agreement.json")
    del payload["source_snapshots"][0]["captured_at_utc"]
    with pytest.raises(ValidationError):
        WeatherSourceSnapshot.model_validate(payload["source_snapshots"][0])


def test_location_basis_required() -> None:
    payload = _load_fixture("temperature_strong_agreement.json")
    del payload["source_snapshots"][0]["location_basis"]
    with pytest.raises(ValidationError):
        WeatherSourceSnapshot.model_validate(payload["source_snapshots"][0])


def test_target_resolution_window_required() -> None:
    payload = _load_fixture("temperature_strong_agreement.json")
    del payload["forecast_bundle"]["target_resolution_window"]
    with pytest.raises(ValidationError):
        WeatherForecastBundle.model_validate(payload["forecast_bundle"])


def test_source_distinctions_preserved_through_normalization() -> None:
    snapshots, bundle, divergence, summary, _ = _validate_fixture("precipitation_high_source_disagreement.json")
    snapshot_ids = {snapshot.snapshot_id for snapshot in snapshots}
    bundle_refs = {value.source_snapshot_ref for value in bundle.source_values}
    divergence_refs = {value.source_snapshot_ref for value in divergence.source_value_trace}
    summary_refs = {value.source_snapshot_ref for value in summary.source_summary_table}

    assert len(bundle_refs) == len(bundle.source_values)
    assert bundle_refs == snapshot_ids
    assert divergence_refs == snapshot_ids
    assert summary_refs == snapshot_ids


def test_freshness_state_required() -> None:
    payload = _load_fixture("stale_forecast_bundle_requiring_downgrade.json")
    del payload["forecast_bundle"]["freshness_state"]
    with pytest.raises(ValidationError):
        WeatherForecastBundle.model_validate(payload["forecast_bundle"])


def test_divergence_claims_trace_to_explicit_source_values() -> None:
    snapshots, _, divergence, _, _ = _validate_fixture("precipitation_supportive_divergence.json")
    source_map = {snapshot.snapshot_id: snapshot for snapshot in snapshots}
    for traced_value in divergence.source_value_trace:
        snapshot = source_map[traced_value.source_snapshot_ref]
        assert any(
            value.metric == traced_value.primary_metric
            and value.value == traced_value.primary_value
            and value.unit == traced_value.primary_unit
            for value in snapshot.values
        )


def test_weather_summary_rejects_execution_authority_language() -> None:
    payload = _load_fixture("temperature_strong_agreement.json")
    payload["weather_research_summary"]["evidence_summary"] = "This is execution_ready and approved."
    with pytest.raises(ValidationError):
        WeatherResearchSummary.model_validate(payload["weather_research_summary"])


@pytest.mark.parametrize(
    ("fixture_name", "expected_gate_outcome"),
    [
        ("temperature_strong_agreement.json", "recommend.research_only"),
        ("temperature_threshold_ambiguity.json", "abstain.low_confidence"),
        ("precipitation_supportive_divergence.json", "recommend.execution_ready_low_confidence"),
        ("precipitation_high_source_disagreement.json", "recommend.research_only"),
        ("stale_forecast_bundle_requiring_downgrade.json", "abstain.poor_timing"),
        ("non_actionable_weather_case_despite_interesting_narrative.json", "abstain.market_not_suitable"),
    ],
)
def test_weather_artifacts_normalize_into_kalshi_case_without_semantic_drift(
    fixture_name: str,
    expected_gate_outcome: str,
) -> None:
    snapshots, bundle, divergence, summary, kalshi_input = _validate_fixture(fixture_name)
    case = build_weather_supported_case(
        source_snapshots=snapshots,
        forecast_bundle=bundle,
        divergence_assessment=divergence,
        research_summary=summary,
        kalshi_input=kalshi_input,
    )

    assert case.expected_edge_source == "weather_forecast_divergence"
    assert case.gate_outcome == expected_gate_outcome
    assert f"weather_bundle_ref={bundle.bundle_id}" in case.gate_reasons
    assert f"weather_summary_ref={summary.summary_id}" in case.gate_reasons
    assert bundle.bundle_id in case.invalidation_condition
    for snapshot in snapshots:
        assert snapshot.source_name in case.evidence_summary


def test_stale_bundle_produces_decay_flag_in_kalshi_case() -> None:
    snapshots, bundle, divergence, summary, kalshi_input = _validate_fixture(
        "stale_forecast_bundle_requiring_downgrade.json"
    )
    case = build_weather_supported_case(
        source_snapshots=snapshots,
        forecast_bundle=bundle,
        divergence_assessment=divergence,
        research_summary=summary,
        kalshi_input=kalshi_input,
    )
    assert case.decay_state == "decayed"
    assert case.downgrade_flags == ["signal_decay_applied"]


def test_weather_supported_case_can_traverse_resolved_bundle_with_reviewable_provenance() -> None:
    snapshots, bundle, divergence, summary, kalshi_input = _validate_fixture(
        "precipitation_supportive_divergence.json"
    )
    case = build_weather_supported_case(
        source_snapshots=snapshots,
        forecast_bundle=bundle,
        divergence_assessment=divergence,
        research_summary=summary,
        kalshi_input=kalshi_input,
    )
    resolved = generate_resolved_bundle(case)

    assert isinstance(resolved, ArtifactBundle)
    assert resolved.post_resolution_review_artifact is not None
    assert resolved.trade_thesis_artifact is not None
    assert resolved.strategy_gate_result is not None
    assert resolved.execution_readiness_receipt is not None
    assert resolved.execution_readiness_receipt.execution_authorized is False
    assert bundle.bundle_id in resolved.trade_thesis_artifact.invalidation_condition
    assert summary.summary_id in resolved.strategy_gate_result.gate_reasons[-1]
    assert resolved.post_resolution_review_artifact.thesis_ref is not None
    assert resolved.post_resolution_review_artifact.gate_result_ref is not None
