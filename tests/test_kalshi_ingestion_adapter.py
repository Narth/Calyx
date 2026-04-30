from __future__ import annotations

import json
from pathlib import Path

from staging.work.kalshi_artifact_models.models import ArtifactBundle
from staging.work.kalshi_ingestion_adapter.adapter import ingest_manual_snapshot, normalize_snapshot_to_case
from staging.work.kalshi_ingestion_adapter.models import (
    INGESTION_SCHEMA_VERSION,
    KalshiCaseOverlay,
    KalshiRawMarketSnapshot,
)


FIXTURE_DIR = Path("staging/work/kalshi_ingestion_adapter/fixtures")
SCHEMA_DIR = Path("staging/work/kalshi_ingestion_adapter/schemas")


def test_manual_snapshot_ingests_end_to_end(tmp_path: Path) -> None:
    result = ingest_manual_snapshot(
        FIXTURE_DIR / "manual_market_snapshot.json",
        FIXTURE_DIR / "manual_overlay.json",
        output_root=tmp_path,
    )

    assert Path(result.snapshot_path).exists()
    assert Path(result.normalized_case_path).exists()
    assert Path(result.evaluated_bundle_path).exists()
    assert len(result.receipt_paths) == 3
    assert all(Path(path).exists() for path in result.receipt_paths)

    bundle = ArtifactBundle.model_validate_json(Path(result.evaluated_bundle_path).read_text(encoding="utf-8"))
    assert bundle.execution_readiness_receipt is not None
    assert bundle.execution_readiness_receipt.execution_authorized is False
    assert bundle.post_resolution_review_artifact is not None


def test_normalization_preserves_raw_market_identity() -> None:
    snapshot = KalshiRawMarketSnapshot.model_validate_json((FIXTURE_DIR / "manual_market_snapshot.json").read_text(encoding="utf-8"))
    overlay = KalshiCaseOverlay.model_validate_json((FIXTURE_DIR / "manual_overlay.json").read_text(encoding="utf-8"))
    case = normalize_snapshot_to_case(snapshot, overlay)

    assert case.market_id == snapshot.raw_market_payload["ticker"]
    assert case.market_title == snapshot.raw_market_payload["title"]
    assert case.proposed_side == overlay.proposed_side


def test_ingestion_receipts_are_emitted_with_expected_types(tmp_path: Path) -> None:
    result = ingest_manual_snapshot(
        FIXTURE_DIR / "manual_market_snapshot.json",
        FIXTURE_DIR / "manual_overlay.json",
        output_root=tmp_path,
    )
    receipt_types = []
    for receipt_path in result.receipt_paths:
        payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        receipt_types.append(payload["receipt_type"])
        assert payload["schema_version"] == INGESTION_SCHEMA_VERSION

    assert receipt_types == [
        "kalshi.market.snapshot.captured",
        "kalshi.market.normalization.completed",
        "kalshi.market.decision_pipeline.invoked",
    ]


def test_adapter_schema_exports_exist() -> None:
    raw_schema = json.loads((SCHEMA_DIR / "kalshi_raw_market_snapshot.schema.json").read_text(encoding="utf-8"))
    overlay_schema = json.loads((SCHEMA_DIR / "kalshi_case_overlay.schema.json").read_text(encoding="utf-8"))
    receipt_schema = json.loads((SCHEMA_DIR / "kalshi_ingestion_receipt.schema.json").read_text(encoding="utf-8"))

    assert raw_schema["properties"]["schema_version"]["const"] == INGESTION_SCHEMA_VERSION
    assert overlay_schema["properties"]["schema_version"]["const"] == INGESTION_SCHEMA_VERSION
    assert receipt_schema["properties"]["schema_version"]["const"] == INGESTION_SCHEMA_VERSION
