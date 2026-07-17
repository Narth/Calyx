"""Read-only staging adapter from Kalshi market snapshots to simulation cases."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx

from staging.work.kalshi_decision_simulation.case_models import (
    DecisionHorizonInput,
    SimulatedKalshiCase,
)
from staging.work.kalshi_decision_simulation.pipeline import generate_resolved_bundle
from staging.work.kalshi_ingestion_adapter.models import (
    AdapterIngestionResult,
    AdapterReceipt,
    KalshiCaseOverlay,
    KalshiRawMarketSnapshot,
    INGESTION_SCHEMA_VERSION,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
ARTIFACT_ROOT = PACKAGE_ROOT / "artifacts"
RAW_DIR = ARTIFACT_ROOT / "raw"
NORMALIZED_DIR = ARTIFACT_ROOT / "normalized"
EVALUATED_DIR = ARTIFACT_ROOT / "evaluated"
RECEIPTS_DIR = ARTIFACT_ROOT / "receipts"
PUBLIC_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


class KalshiReadOnlyClient:
    """Public, read-only Kalshi market data client for staging."""

    def __init__(self, base_url: str = PUBLIC_BASE_URL, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_market_snapshot(self, ticker: str, include_orderbook: bool = True) -> KalshiRawMarketSnapshot:
        market_payload = self._get_market_payload(ticker)
        orderbook_payload = None
        if include_orderbook:
            try:
                orderbook_payload = self._get_orderbook_payload(ticker)
            except httpx.HTTPError:
                orderbook_payload = None
        return KalshiRawMarketSnapshot(
            schema_name="kalshi.raw_market_snapshot",
            schema_version=INGESTION_SCHEMA_VERSION,
            source_type="live_public_api",
            captured_at_utc=_utcnow(),
            requested_ticker=ticker,
            base_url=self.base_url,
            include_orderbook=include_orderbook,
            raw_market_payload=market_payload,
            raw_orderbook_payload=orderbook_payload,
        )

    def _get_market_payload(self, ticker: str) -> dict[str, Any]:
        url = f"{self.base_url}/markets"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params={"tickers": ticker})
            response.raise_for_status()
            payload = response.json()
        markets = payload.get("markets") or []
        if not markets:
            raise ValueError(f"No market returned for ticker {ticker}")
        return markets[0]

    def _get_orderbook_payload(self, ticker: str) -> dict[str, Any]:
        url = f"{self.base_url}/markets/{ticker}/orderbook"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()


def ingest_manual_snapshot(
    snapshot_path: Path,
    overlay_path: Path,
    output_root: Path | None = None,
) -> AdapterIngestionResult:
    snapshot = KalshiRawMarketSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))
    overlay = KalshiCaseOverlay.model_validate_json(overlay_path.read_text(encoding="utf-8"))
    return _persist_and_evaluate(snapshot, overlay, output_root=output_root)


def ingest_live_market(
    ticker: str,
    overlay: KalshiCaseOverlay,
    output_root: Path | None = None,
    include_orderbook: bool = True,
    client: KalshiReadOnlyClient | None = None,
) -> AdapterIngestionResult:
    read_client = client or KalshiReadOnlyClient()
    snapshot = read_client.fetch_market_snapshot(ticker=ticker, include_orderbook=include_orderbook)
    return _persist_and_evaluate(snapshot, overlay, output_root=output_root)


def normalize_snapshot_to_case(snapshot: KalshiRawMarketSnapshot, overlay: KalshiCaseOverlay) -> SimulatedKalshiCase:
    market = snapshot.raw_market_payload
    market_id = str(market.get("ticker") or market.get("market_ticker") or snapshot.requested_ticker)
    title = str(market.get("title") or market.get("market_title") or market_id)
    resolution_rule_summary = _build_resolution_summary(market)
    observed_price = _coerce_probability(
        market.get("last_price_dollars")
        or market.get("yes_ask_dollars")
        or market.get("yes_bid_dollars")
        or market.get("last_price")
    )
    best_bid = _coerce_probability(market.get("yes_bid_dollars") or market.get("yes_bid"))
    best_ask = _coerce_probability(market.get("yes_ask_dollars") or market.get("yes_ask"))
    decision_horizon = DecisionHorizonInput(
        horizon_hours=overlay.decision_horizon_hours,
        thesis_valid_until_utc=snapshot.captured_at_utc + timedelta(hours=overlay.thesis_valid_for_hours),
        rationale=overlay.decision_horizon_rationale,
    )
    return SimulatedKalshiCase(
        schema_name="kalshi.mock_candidate_market_case",
        schema_version="1.0.0",
        artifact_schema_version="1.0.0",
        case_id=overlay.case_id,
        scenario_name=overlay.scenario_name,
        description=overlay.description,
        corr_id=f"kalshi-ingest-{overlay.case_id}",
        market_id=market_id,
        market_title=title,
        resolution_rule_summary=resolution_rule_summary,
        initial_timestamp_utc=snapshot.captured_at_utc,
        score_timestamp_utc=snapshot.captured_at_utc + timedelta(minutes=1),
        gate_timestamp_utc=snapshot.captured_at_utc + timedelta(minutes=2),
        readiness_timestamp_utc=(snapshot.captured_at_utc + timedelta(minutes=3))
        if overlay.gate_outcome.startswith("recommend.execution_ready")
        else None,
        execution_timestamp_utc=(snapshot.captured_at_utc + timedelta(minutes=4))
        if overlay.trade_executed
        else None,
        resolution_timestamp_utc=overlay.resolution_timestamp_utc,
        proposed_side=overlay.proposed_side,
        expected_edge_source=overlay.expected_edge_source,
        operator_engagement_state=overlay.operator_engagement_state,
        market_observation={
            "observed_price": observed_price,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "market_note": market.get("subtitle") or market.get("status") or market.get("category")
            or overlay.description,
            "price_unit": "probability",
        },
        entry_rationale=overlay.entry_rationale,
        decision_horizon=decision_horizon,
        invalidation_condition=overlay.invalidation_condition,
        abstention_alternative=overlay.abstention_alternative,
        evidence_summary=overlay.evidence_summary,
        evidence_signal=overlay.evidence_signal,
        confidence_signal=overlay.confidence_signal,
        score_dimensions=overlay.score_dimensions,
        downgrade_flags=overlay.downgrade_flags,
        decay_state=overlay.decay_state,
        scoring_notes=overlay.scoring_notes,
        classification_band=overlay.classification_band,
        gate_outcome=overlay.gate_outcome,
        gate_reasons=overlay.gate_reasons,
        operator_legibility_status=overlay.operator_legibility_status,
        wallet_policy_fit=overlay.wallet_policy_fit,
        resolved_outcome=overlay.resolved_outcome,
        trade_executed=overlay.trade_executed,
        execution_status=overlay.execution_status,
        position_taken=overlay.position_taken,
        review_plan=overlay.review_plan,
    )


def _persist_and_evaluate(
    snapshot: KalshiRawMarketSnapshot,
    overlay: KalshiCaseOverlay,
    output_root: Path | None = None,
) -> AdapterIngestionResult:
    root = output_root or PACKAGE_ROOT / "artifacts"
    raw_dir = root / "raw"
    normalized_dir = root / "normalized"
    evaluated_dir = root / "evaluated"
    receipts_dir = root / "receipts"
    for directory in (raw_dir, normalized_dir, evaluated_dir, receipts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    snapshot_path = raw_dir / f"{overlay.case_id}__raw_snapshot.json"
    _write_json(snapshot_path, snapshot.model_dump(mode="json"))
    capture_receipt_path = receipts_dir / f"{overlay.case_id}__raw_market_snapshot_captured.json"
    _write_receipt(
        capture_receipt_path,
        AdapterReceipt(
            schema_name="kalshi.ingestion.receipt",
            schema_version=INGESTION_SCHEMA_VERSION,
            receipt_type="kalshi.market.snapshot.captured",
            corr_id=f"kalshi-ingest-{overlay.case_id}",
            case_id=overlay.case_id,
            market_id=snapshot.requested_ticker,
            ts_utc=snapshot.captured_at_utc,
            artifact_path=str(snapshot_path),
            note="Raw market snapshot preserved before normalization.",
        ),
    )

    case = normalize_snapshot_to_case(snapshot, overlay)
    normalized_case_path = normalized_dir / f"{overlay.case_id}__normalized_case.json"
    _write_json(normalized_case_path, case.model_dump(mode="json"))
    normalization_receipt_path = receipts_dir / f"{overlay.case_id}__normalization_completed.json"
    _write_receipt(
        normalization_receipt_path,
        AdapterReceipt(
            schema_name="kalshi.ingestion.receipt",
            schema_version=INGESTION_SCHEMA_VERSION,
            receipt_type="kalshi.market.normalization.completed",
            corr_id=case.corr_id,
            case_id=case.case_id,
            market_id=case.market_id,
            ts_utc=case.score_timestamp_utc,
            artifact_path=str(normalized_case_path),
            note="Raw snapshot normalized into canonical simulation case format.",
        ),
    )

    bundle = generate_resolved_bundle(case)
    evaluated_bundle_path = evaluated_dir / f"{overlay.case_id}__evaluated_bundle.json"
    _write_json(evaluated_bundle_path, bundle.model_dump(mode="json"))
    pipeline_receipt_path = receipts_dir / f"{overlay.case_id}__decision_pipeline_invoked.json"
    _write_receipt(
        pipeline_receipt_path,
        AdapterReceipt(
            schema_name="kalshi.ingestion.receipt",
            schema_version=INGESTION_SCHEMA_VERSION,
            receipt_type="kalshi.market.decision_pipeline.invoked",
            corr_id=case.corr_id,
            case_id=case.case_id,
            market_id=case.market_id,
            ts_utc=case.resolution_timestamp_utc,
            artifact_path=str(evaluated_bundle_path),
            note="Normalized case traversed thesis, score, gate, and post-resolution review.",
        ),
    )

    return AdapterIngestionResult(
        snapshot_path=str(snapshot_path),
        normalized_case_path=str(normalized_case_path),
        evaluated_bundle_path=str(evaluated_bundle_path),
        receipt_paths=[
            str(capture_receipt_path),
            str(normalization_receipt_path),
            str(pipeline_receipt_path),
        ],
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_receipt(path: Path, receipt: AdapterReceipt) -> None:
    _write_json(path, receipt.model_dump(mode="json"))


def _coerce_probability(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        numeric = float(str(value))
    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, numeric))


def _build_resolution_summary(market: dict[str, Any]) -> str:
    primary = market.get("rules_primary")
    secondary = market.get("rules_secondary")
    if primary and secondary:
        return f"{primary} {secondary}"
    if primary:
        return str(primary)
    if secondary:
        return str(secondary)
    return str(market.get("subtitle") or market.get("title") or market.get("ticker") or "Kalshi market")


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
