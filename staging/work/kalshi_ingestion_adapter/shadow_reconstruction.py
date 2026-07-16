"""Shadow outcome reconstruction for staging-only Kalshi smoke cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from staging.work.kalshi_artifact_models.models import PostResolutionReviewArtifact
from staging.work.kalshi_ingestion_adapter.models import AdapterReceipt, INGESTION_SCHEMA_VERSION


PUBLIC_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass(frozen=True)
class HypotheticalTradeResult:
    entry_price: float
    stake_dollars: float
    payout_dollars: float
    profit_loss_dollars: float
    tradable: bool
    note: str


def reconstruct_live_smoke_case(
    raw_snapshot_path: Path,
    normalized_case_path: Path,
    evaluated_bundle_path: Path,
    receipts_dir: Path,
    review_dir: Path,
    stake_dollars: float = 1.0,
) -> dict[str, object]:
    raw_snapshot = json.loads(raw_snapshot_path.read_text(encoding="utf-8"))
    normalized_case = json.loads(normalized_case_path.read_text(encoding="utf-8"))
    evaluated_bundle = json.loads(evaluated_bundle_path.read_text(encoding="utf-8"))

    ticker = normalized_case["market_id"]
    market_payload = _fetch_market_resolution(ticker)
    resolution_receipt_path = _write_resolution_receipt(
        receipts_dir=receipts_dir,
        case_id=normalized_case["case_id"],
        corr_id=normalized_case["corr_id"],
        ticker=ticker,
        market_payload=market_payload,
    )

    proposed_side = evaluated_bundle["trade_thesis_artifact"]["proposed_side"]
    price_context = evaluated_bundle["trade_thesis_artifact"]["price_context"]
    composite_score = evaluated_bundle["signal_score_record"]["composite_score"]
    confidence_signal = evaluated_bundle["signal_score_record"]["confidence_signal"]
    gate_outcome = evaluated_bundle["strategy_gate_result"]["gate_outcome"]

    entry_price = float(price_context["observed_price"])
    bid = float(price_context.get("best_bid") or 0.0)
    ask = float(price_context.get("best_ask") or 0.0)
    liquidity_zero = bid <= 0.0 and ask <= 0.0
    resolution = str(market_payload.get("result") or "unresolved")
    hypothetical = _construct_hypothetical_trade(
        proposed_side=proposed_side,
        resolved_outcome=resolution,
        entry_price=entry_price,
        stake_dollars=stake_dollars,
        liquidity_zero=liquidity_zero,
    )

    recommended_gate = (
        "abstain.market_not_suitable"
        if (liquidity_zero or entry_price <= 0.0)
        else "recommend.research_only"
    )

    decision_quality = "decision_quality.weak" if recommended_gate.startswith("abstain") else "decision_quality.acceptable"
    outcome_interpretation = (
        "outcome.false_positive_signal"
        if recommended_gate.startswith("abstain")
        else "outcome.variance_penalty"
    )
    policy_alignment = "policy.aligned"

    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "live_public_smoke__shadow_post_resolution_review.json"
    review = PostResolutionReviewArtifact.model_validate(
        {
            "schema_name": "kalshi.post_resolution_review_artifact",
            "schema_version": "1.0.0",
            "artifact_type": "post_resolution_review_artifact",
            "artifact_id": "live_public_smoke.shadow_review",
            "corr_id": normalized_case["corr_id"],
            "timestamp_utc": market_payload.get("settlement_ts") or market_payload.get("updated_time"),
            "market_id": ticker,
            "market_title": evaluated_bundle["trade_thesis_artifact"]["market_title"],
            "resolved_outcome": resolution,
            "position_taken": "none",
            "trade_executed": False,
            "thesis_ref": evaluated_bundle["post_resolution_review_artifact"]["thesis_ref"],
            "score_ref": evaluated_bundle["post_resolution_review_artifact"]["score_ref"],
            "gate_result_ref": evaluated_bundle["post_resolution_review_artifact"]["gate_result_ref"],
            "execution_ref": None,
            "original_composite_score": composite_score,
            "original_gate_outcome": gate_outcome,
            "thesis_quality_assessment": "The original smoke thesis was sufficient for staging validation, but it was not economically grounded enough for a live execution-ready posture.",
            "score_quality_assessment": "The score overstated tradability. The live snapshot had zero bid, zero ask, zero last price, and zero volume, so the candidate was not actually deployable.",
            "timing_quality_assessment": "Timing did not help because there was no actionable entry window in the captured quote state.",
            "governance_quality_assessment": "Governance held: no execution authority was introduced, and the reconstruction remained read-only and artifact-bound.",
            "decision_quality_classification": decision_quality,
            "outcome_interpretation_classification": outcome_interpretation,
            "policy_alignment_classification": policy_alignment,
            "profit_loss_result": {
                "currency": "USD",
                "amount": hypothetical.profit_loss_dollars,
                "note": hypothetical.note,
            },
            "attention_cost_estimate": "Low operator attention. Most of the signal came from artifact replay and public resolution fetch, not ongoing monitoring.",
            "abstention_counterfactual": "Abstention or at most research-only would have been the better governed posture because the snapshot was non-tradable.",
            "review_notes": (
                f"Original gate outcome was {gate_outcome}. Reconstructed judgment: {recommended_gate}. "
                "The decisive miss was tradability, not market resolution. This was noise around a non-actionable quote state, not live edge."
            ),
            "recommended_followup": "review_market_selection",
        }
    )
    review_path.write_text(json.dumps(review.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "ticker": ticker,
        "proposed_side": proposed_side,
        "price_context": price_context,
        "composite_score": composite_score,
        "confidence_signal": confidence_signal,
        "gate_outcome": gate_outcome,
        "resolved_outcome": resolution,
        "hypothetical_trade": hypothetical.__dict__,
        "recommended_gate": recommended_gate,
        "resolution_receipt_path": str(resolution_receipt_path),
        "review_path": str(review_path),
    }


def _fetch_market_resolution(ticker: str) -> dict[str, object]:
    response = httpx.get(
        f"{PUBLIC_BASE_URL}/markets",
        params={"tickers": ticker},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    markets = payload.get("markets") or []
    if not markets:
        raise ValueError(f"No market data returned for ticker {ticker}")
    return markets[0]


def _write_resolution_receipt(
    receipts_dir: Path,
    case_id: str,
    corr_id: str,
    ticker: str,
    market_payload: dict[str, object],
) -> Path:
    receipts_dir.mkdir(parents=True, exist_ok=True)
    path = receipts_dir / f"{case_id}__market_resolution_fetched.json"
    receipt = AdapterReceipt(
        schema_name="kalshi.ingestion.receipt",
        schema_version=INGESTION_SCHEMA_VERSION,
        receipt_type="kalshi.market.resolution.fetched",
        corr_id=corr_id,
        case_id=case_id,
        market_id=ticker,
        ts_utc=market_payload.get("updated_time") or market_payload.get("settlement_ts"),
        artifact_path=str(path),
        note=f"Public Kalshi resolution fetched with result={market_payload.get('result')}, status={market_payload.get('status')}.",
    )
    path.write_text(json.dumps(receipt.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _construct_hypothetical_trade(
    proposed_side: str,
    resolved_outcome: str,
    entry_price: float,
    stake_dollars: float,
    liquidity_zero: bool,
) -> HypotheticalTradeResult:
    if liquidity_zero or entry_price <= 0.0:
        return HypotheticalTradeResult(
            entry_price=entry_price,
            stake_dollars=stake_dollars,
            payout_dollars=0.0,
            profit_loss_dollars=0.0,
            tradable=False,
            note=(
                "Observed entry price was 0.0 with zero bid/ask liquidity. A literal $1 deployment was non-physical, "
                "so the shadow reconstruction records this as non-tradable and forces an abstention-oriented review."
            ),
        )

    contracts = stake_dollars / entry_price
    wins = (proposed_side == "yes" and resolved_outcome == "yes") or (proposed_side == "no" and resolved_outcome == "no")
    payout = contracts if wins else 0.0
    return HypotheticalTradeResult(
        entry_price=entry_price,
        stake_dollars=stake_dollars,
        payout_dollars=round(payout, 6),
        profit_loss_dollars=round(payout - stake_dollars, 6),
        tradable=True,
        note="Hypothetical payout uses a $1 standardized spend at the observed snapshot price.",
    )
