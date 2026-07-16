"""Models for staging-only Kalshi snapshot ingestion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from staging.work.kalshi_artifact_models.models import (
    ARTIFACT_SCHEMA_VERSION,
    ConfidenceValue,
    DowngradeFlag,
    ExpectedEdgeSource,
    GateOutcome,
    OperatorEngagementState,
    OperatorLegibilityStatus,
    ProposedSide,
    ScoreDimensions,
    SignalClassificationBand,
    WalletPolicyFit,
)
from staging.work.kalshi_decision_simulation.case_models import CASE_SCHEMA_VERSION, ReviewPlan

INGESTION_SCHEMA_VERSION = "1.0.0"


class StrictIngestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KalshiRawMarketSnapshot(StrictIngestionModel):
    schema_name: Literal["kalshi.raw_market_snapshot"]
    schema_version: Literal[INGESTION_SCHEMA_VERSION]
    source_type: Literal["live_public_api", "manual_capture"]
    captured_at_utc: AwareDatetime
    requested_ticker: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    include_orderbook: bool = True
    raw_market_payload: dict[str, Any]
    raw_orderbook_payload: dict[str, Any] | None = None


class KalshiCaseOverlay(StrictIngestionModel):
    schema_name: Literal["kalshi.case_overlay"]
    schema_version: Literal[INGESTION_SCHEMA_VERSION]
    artifact_schema_version: Literal[ARTIFACT_SCHEMA_VERSION]
    case_schema_version: Literal[CASE_SCHEMA_VERSION]
    case_id: str = Field(min_length=3, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    scenario_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    proposed_side: ProposedSide
    expected_edge_source: ExpectedEdgeSource
    operator_engagement_state: OperatorEngagementState
    entry_rationale: str = Field(min_length=1)
    decision_horizon_hours: float = Field(gt=0.0)
    thesis_valid_for_hours: float = Field(gt=0.0)
    decision_horizon_rationale: str = Field(min_length=1)
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
    resolved_outcome: Literal["yes", "no", "void", "unresolved"]
    trade_executed: bool
    execution_status: Literal["attempted", "success", "failed"] | None = None
    position_taken: ProposedSide
    resolution_timestamp_utc: AwareDatetime
    review_plan: ReviewPlan


class AdapterReceipt(StrictIngestionModel):
    schema_name: Literal["kalshi.ingestion.receipt"]
    schema_version: Literal[INGESTION_SCHEMA_VERSION]
    receipt_type: Literal[
        "kalshi.market.snapshot.captured",
        "kalshi.market.resolution.fetched",
        "kalshi.market.normalization.completed",
        "kalshi.market.decision_pipeline.invoked",
    ]
    corr_id: str = Field(min_length=3)
    case_id: str = Field(min_length=3)
    market_id: str = Field(min_length=1)
    ts_utc: AwareDatetime
    artifact_path: str = Field(min_length=1)
    note: str = Field(min_length=1)


class AdapterIngestionResult(StrictIngestionModel):
    snapshot_path: str = Field(min_length=1)
    normalized_case_path: str = Field(min_length=1)
    evaluated_bundle_path: str = Field(min_length=1)
    receipt_paths: list[str] = Field(min_length=3)


def export_adapter_json_schemas(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    models: dict[str, type[BaseModel]] = {
        "kalshi.raw_market_snapshot": KalshiRawMarketSnapshot,
        "kalshi.case_overlay": KalshiCaseOverlay,
        "kalshi.ingestion.receipt": AdapterReceipt,
    }
    written: dict[str, Path] = {}
    for name, model in models.items():
        filename = f"{name.replace('.', '_')}.schema.json"
        destination = output_dir / filename
        destination.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written[name] = destination
    return written
