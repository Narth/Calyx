# -*- coding: utf-8 -*-
"""
Observation Yield Analyzer
==========================

Core analysis logic for computing observation yield from Truth Digest artifacts.

INPUT CONSTRAINT (CRITICAL):
This module reads ONLY from truth_digest_*.json files.
It does NOT access raw evidence directly.
All calculations derive strictly from digest artifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from .models import (
    YieldMetrics,
    MetricYield,
    DiminishingReturnsIndicator,
    DiminishingReturnsStatus,
    YieldAnalysisResult,
    YieldTrend,
)


# Default threshold for diminishing returns detection
DEFAULT_CONSECUTIVE_WINDOWS_THRESHOLD = 3


def get_digests_dir(node_id: str) -> Path:
    """Get digest storage directory for a node."""
    config = get_config()
    return config.data_dir / "digests" / node_id


def get_yield_dir(node_id: str) -> Path:
    """Get yield analysis storage directory for a node."""
    config = get_config()
    yield_dir = config.data_dir / "yield" / node_id
    yield_dir.mkdir(parents=True, exist_ok=True)
    return yield_dir


def load_digest_artifacts(node_id: str, metric_scope: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Load Truth Digest JSON artifacts for a node.
    
    CONSTRAINT: This is the ONLY function that reads digest files.
    All yield calculations flow through this.
    
    Args:
        node_id: Node identifier
        metric_scope: If set, filter to metric-specific digests
        
    Returns:
        List of digest data dictionaries, sorted by period start
    """
    digests_dir = get_digests_dir(node_id)
    
    if not digests_dir.exists():
        return []
    
    digests = []
    
    for path in digests_dir.glob("truth_digest_*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Filter by scope if specified
            if metric_scope:
                if data.get("metric_scope") != metric_scope:
                    continue
            else:
                # Node-level: exclude metric-specific digests
                if data.get("metric_scope") is not None:
                    continue
            
            data["_artifact_path"] = str(path)
            data["_artifact_id"] = path.stem
            digests.append(data)
            
        except (json.JSONDecodeError, IOError):
            continue
    
    # Sort by period start
    digests.sort(key=lambda d: d.get("period", {}).get("start", ""))
    
    return digests


def compute_yield(state_changes: int, confirmations: int) -> tuple[float, float]:
    """
    Compute yield ratio and percentage.
    
    Args:
        state_changes: Number of state changes
        confirmations: Number of confirmations
        
    Returns:
        Tuple of (yield_ratio 0-1, yield_percent 0-100)
    """
    total = state_changes + confirmations
    
    if total == 0:
        return 0.0, 0.0
    
    ratio = state_changes / total
    percent = ratio * 100.0
    
    return ratio, percent


def extract_yield_from_digest(digest: dict[str, Any]) -> YieldMetrics:
    """
    Extract yield metrics from a single digest artifact.
    
    Args:
        digest: Digest data dictionary
        
    Returns:
        YieldMetrics for this digest window
    """
    state_changes = len(digest.get("state_changes", []))
    
    # Sum confirmation observation counts
    confirmations = sum(
        sc.get("observation_count", 1)
        for sc in digest.get("state_confirmations", [])
    )
    
    total = state_changes + confirmations
    ratio, percent = compute_yield(state_changes, confirmations)
    
    period = digest.get("period", {})
    
    return YieldMetrics(
        state_changes=state_changes,
        confirmations=confirmations,
        total_observations=total,
        yield_ratio=ratio,
        yield_percent=round(percent, 2),
        window_start=period.get("start", ""),
        window_end=period.get("end", ""),
        digest_id=digest.get("_artifact_id", "unknown"),
    )


def extract_metric_breakdown(digest: dict[str, Any]) -> list[MetricYield]:
    """
    Extract per-metric yield breakdown from a digest.
    
    Args:
        digest: Digest data dictionary
        
    Returns:
        List of MetricYield for each metric
    """
    metrics: dict[str, dict[str, int]] = {}
    
    # Count state changes per metric
    for sc in digest.get("state_changes", []):
        metric = sc.get("metric", "unknown")
        if metric not in metrics:
            metrics[metric] = {"changes": 0, "confirmations": 0}
        metrics[metric]["changes"] += 1
    
    # Count confirmations per metric
    for sc in digest.get("state_confirmations", []):
        metric = sc.get("metric", "unknown")
        if metric not in metrics:
            metrics[metric] = {"changes": 0, "confirmations": 0}
        metrics[metric]["confirmations"] += sc.get("observation_count", 1)
    
    # Build breakdown
    breakdown = []
    for metric, counts in sorted(metrics.items()):
        ratio, percent = compute_yield(counts["changes"], counts["confirmations"])
        breakdown.append(MetricYield(
            metric=metric,
            state_changes=counts["changes"],
            confirmations=counts["confirmations"],
            yield_ratio=ratio,
            yield_percent=round(percent, 2),
        ))
    
    return breakdown


def determine_yield_trend(
    current: Optional[YieldMetrics],
    prior: Optional[YieldMetrics],
) -> YieldTrend:
    """
    Determine yield trend between two windows.
    
    Args:
        current: Current window metrics
        prior: Prior window metrics
        
    Returns:
        YieldTrend classification
    """
    if current is None or prior is None:
        return YieldTrend.UNKNOWN
    
    diff = current.yield_ratio - prior.yield_ratio
    
    # Use small epsilon for "stable" classification
    epsilon = 0.01
    
    if diff > epsilon:
        return YieldTrend.INCREASING
    elif diff < -epsilon:
        return YieldTrend.DECREASING
    else:
        return YieldTrend.STABLE


def detect_new_entity(digests: list[dict[str, Any]]) -> bool:
    """
    Detect if a new metric/entity appeared in the most recent digest.
    
    A new entity is a state change with reason "first_observation" or "new_entity".
    """
    if not digests:
        return False
    
    latest = digests[-1]
    
    for sc in latest.get("state_changes", []):
        reason = sc.get("reason", "")
        if reason in ("first_observation", "new_entity"):
            return True
    
    return False


def detect_diminishing_returns(
    digests: list[dict[str, Any]],
    threshold_n: int = DEFAULT_CONSECUTIVE_WINDOWS_THRESHOLD,
) -> DiminishingReturnsIndicator:
    """
    Detect diminishing returns across digest windows.
    
    DETECTION CRITERIA:
    - Yield = 0 for N consecutive windows ? detected
    - Exception: If new entity appears, do not flag for that window
    
    Args:
        digests: List of digest artifacts (sorted by time)
        threshold_n: Consecutive zero-yield windows required for detection
        
    Returns:
        DiminishingReturnsIndicator
    """
    if len(digests) < threshold_n:
        return DiminishingReturnsIndicator(
            status=DiminishingReturnsStatus.INSUFFICIENT_DATA,
            consecutive_zero_yield_windows=0,
            windows_analyzed=len(digests),
            threshold_n=threshold_n,
            new_entity_in_window=False,
        )
    
    # Check for new entity in most recent window
    new_entity = detect_new_entity(digests)
    
    if new_entity:
        # Exception: new entity appeared, do not flag diminishing returns
        return DiminishingReturnsIndicator(
            status=DiminishingReturnsStatus.NOT_DETECTED,
            consecutive_zero_yield_windows=0,
            windows_analyzed=len(digests),
            threshold_n=threshold_n,
            new_entity_in_window=True,
        )
    
    # Count consecutive zero-yield windows from most recent
    consecutive_zero = 0
    
    for digest in reversed(digests):
        metrics = extract_yield_from_digest(digest)
        
        if metrics.state_changes == 0:
            consecutive_zero += 1
        else:
            break  # Chain broken
    
    # Determine status
    if consecutive_zero >= threshold_n:
        status = DiminishingReturnsStatus.DETECTED
    else:
        status = DiminishingReturnsStatus.NOT_DETECTED
    
    return DiminishingReturnsIndicator(
        status=status,
        consecutive_zero_yield_windows=consecutive_zero,
        windows_analyzed=len(digests),
        threshold_n=threshold_n,
        new_entity_in_window=False,
    )


def analyze_node_yield(
    node_id: str,
    persist: bool = True,
) -> YieldAnalysisResult:
    """
    Analyze observation yield for a node from its digest artifacts.
    
    CONSTRAINT: Reads ONLY from truth_digest_*.json files.
    
    Args:
        node_id: Node identifier
        persist: Whether to save as artifact
        
    Returns:
        YieldAnalysisResult
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Load digests (node-level only)
    digests = load_digest_artifacts(node_id, metric_scope=None)
    
    if not digests:
        result = YieldAnalysisResult(
            node_id=node_id,
            metric_scope=None,
            analysis_timestamp=timestamp,
            current_window=None,
            prior_window=None,
            yield_trend=YieldTrend.UNKNOWN,
            diminishing_returns=DiminishingReturnsIndicator(
                status=DiminishingReturnsStatus.INSUFFICIENT_DATA,
                consecutive_zero_yield_windows=0,
                windows_analyzed=0,
                threshold_n=DEFAULT_CONSECUTIVE_WINDOWS_THRESHOLD,
                new_entity_in_window=False,
            ),
            confidence="none",
        )
        
        if persist:
            _persist_yield_analysis(result, node_id)
        
        return result
    
    # Extract metrics from most recent digests
    current_digest = digests[-1]
    current_window = extract_yield_from_digest(current_digest)
    
    prior_window = None
    if len(digests) >= 2:
        prior_window = extract_yield_from_digest(digests[-2])
    
    # Determine trend
    yield_trend = determine_yield_trend(current_window, prior_window)
    
    # Detect diminishing returns
    diminishing_returns = detect_diminishing_returns(digests)
    
    # Extract metric breakdown from current window
    metric_breakdown = extract_metric_breakdown(current_digest)
    
    # Determine period bounds
    period_start = digests[0].get("period", {}).get("start")
    period_end = digests[-1].get("period", {}).get("end")
    
    # Build result
    result = YieldAnalysisResult(
        node_id=node_id,
        metric_scope=None,
        analysis_timestamp=timestamp,
        current_window=current_window,
        prior_window=prior_window,
        yield_trend=yield_trend,
        diminishing_returns=diminishing_returns,
        metric_breakdown=metric_breakdown,
        digests_analyzed=[d.get("_artifact_id", "unknown") for d in digests],
        period_start=period_start,
        period_end=period_end,
        confidence=_calculate_confidence(len(digests)),
    )
    
    if persist:
        _persist_yield_analysis(result, node_id)
    
    # Log analysis event
    _log_yield_analysis_event(result)
    
    return result


def analyze_metric_yield(
    node_id: str,
    metric: str,
    persist: bool = True,
) -> YieldAnalysisResult:
    """
    Analyze observation yield for a specific metric.
    
    CONSTRAINT: Reads ONLY from truth_digest_*.json files.
    
    Args:
        node_id: Node identifier
        metric: Metric name
        persist: Whether to save as artifact
        
    Returns:
        YieldAnalysisResult
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Load metric-specific digests
    digests = load_digest_artifacts(node_id, metric_scope=metric)
    
    if not digests:
        result = YieldAnalysisResult(
            node_id=node_id,
            metric_scope=metric,
            analysis_timestamp=timestamp,
            current_window=None,
            prior_window=None,
            yield_trend=YieldTrend.UNKNOWN,
            diminishing_returns=DiminishingReturnsIndicator(
                status=DiminishingReturnsStatus.INSUFFICIENT_DATA,
                consecutive_zero_yield_windows=0,
                windows_analyzed=0,
                threshold_n=DEFAULT_CONSECUTIVE_WINDOWS_THRESHOLD,
                new_entity_in_window=False,
            ),
            confidence="none",
        )
        
        if persist:
            _persist_yield_analysis(result, node_id, metric)
        
        return result
    
    # Extract metrics
    current_window = extract_yield_from_digest(digests[-1])
    
    prior_window = None
    if len(digests) >= 2:
        prior_window = extract_yield_from_digest(digests[-2])
    
    yield_trend = determine_yield_trend(current_window, prior_window)
    diminishing_returns = detect_diminishing_returns(digests)
    
    period_start = digests[0].get("period", {}).get("start")
    period_end = digests[-1].get("period", {}).get("end")
    
    result = YieldAnalysisResult(
        node_id=node_id,
        metric_scope=metric,
        analysis_timestamp=timestamp,
        current_window=current_window,
        prior_window=prior_window,
        yield_trend=yield_trend,
        diminishing_returns=diminishing_returns,
        metric_breakdown=[],  # Not applicable for metric-level
        digests_analyzed=[d.get("_artifact_id", "unknown") for d in digests],
        period_start=period_start,
        period_end=period_end,
        confidence=_calculate_confidence(len(digests)),
    )
    
    if persist:
        _persist_yield_analysis(result, node_id, metric)
    
    _log_yield_analysis_event(result)
    
    return result


def _calculate_confidence(digest_count: int) -> str:
    """Calculate confidence level based on digest count."""
    if digest_count >= 5:
        return "high"
    elif digest_count >= 3:
        return "medium"
    elif digest_count >= 1:
        return "low"
    else:
        return "none"


def _persist_yield_analysis(
    result: YieldAnalysisResult,
    node_id: str,
    metric: Optional[str] = None,
) -> Path:
    """Persist yield analysis as append-only artifact."""
    yield_dir = get_yield_dir(node_id)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if metric:
        safe_metric = metric.replace(".", "_")
        filename = f"yield_analysis_metric_{safe_metric}_{node_id}_{timestamp}.json"
    else:
        filename = f"yield_analysis_node_{node_id}_{timestamp}.json"
    
    path = yield_dir / filename
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, sort_keys=True)
    
    return path


def _log_yield_analysis_event(result: YieldAnalysisResult) -> None:
    """Log yield analysis as evidence event."""
    try:
        from ..core.evidence import add_event
        
        scope = f"metric:{result.metric_scope}" if result.metric_scope else "node"
        status = result.diminishing_returns.status.value
        
        add_event(
            event_type="YIELD_ANALYSIS_COMPLETED",
            component="yield_analyzer",
            summary=f"Yield analysis for {result.node_id} ({scope}): {status}",
            data={
                "node_id": result.node_id,
                "scope": scope,
                "diminishing_returns_status": status,
                "consecutive_zero_windows": result.diminishing_returns.consecutive_zero_yield_windows,
                "digests_analyzed": len(result.digests_analyzed),
                "current_yield_percent": result.current_window.yield_percent if result.current_window else None,
            },
        )
    except Exception:
        pass
