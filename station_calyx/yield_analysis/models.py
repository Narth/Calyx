# -*- coding: utf-8 -*-
"""
Yield Analysis Data Models
==========================

Data structures for observation yield analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class YieldTrend(Enum):
    """Direction of yield change."""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    UNKNOWN = "unknown"


class DiminishingReturnsStatus(Enum):
    """Status of diminishing returns detection."""
    DETECTED = "detected"
    NOT_DETECTED = "not_detected"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class YieldMetrics:
    """Yield metrics for a single window."""
    state_changes: int
    confirmations: int
    total_observations: int
    yield_ratio: float  # 0.0 to 1.0
    yield_percent: float  # 0.0 to 100.0
    window_start: str
    window_end: str
    digest_id: str  # Reference to source digest
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "YieldMetrics":
        return cls(**data)


@dataclass
class MetricYield:
    """Yield breakdown for a single metric."""
    metric: str
    state_changes: int
    confirmations: int
    yield_ratio: float
    yield_percent: float
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DiminishingReturnsIndicator:
    """Indicator for diminishing returns detection."""
    status: DiminishingReturnsStatus
    consecutive_zero_yield_windows: int
    windows_analyzed: int
    threshold_n: int  # Number of consecutive windows required for detection
    new_entity_in_window: bool  # Exception: new metric appeared
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "consecutive_zero_yield_windows": self.consecutive_zero_yield_windows,
            "windows_analyzed": self.windows_analyzed,
            "threshold_n": self.threshold_n,
            "new_entity_in_window": self.new_entity_in_window,
        }


@dataclass
class YieldAnalysisResult:
    """Complete yield analysis result."""
    node_id: str
    metric_scope: Optional[str]  # None for node-level, metric name for metric-level
    analysis_timestamp: str
    
    # Current and prior window metrics
    current_window: Optional[YieldMetrics]
    prior_window: Optional[YieldMetrics]
    yield_trend: YieldTrend
    
    # Diminishing returns
    diminishing_returns: DiminishingReturnsIndicator
    
    # Per-metric breakdown (node-level only)
    metric_breakdown: list[MetricYield] = field(default_factory=list)
    
    # Evidence basis
    digests_analyzed: list[str] = field(default_factory=list)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    confidence: str = "unknown"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_version": "v1",
            "node_id": self.node_id,
            "metric_scope": self.metric_scope,
            "analysis_timestamp": self.analysis_timestamp,
            "current_window": self.current_window.to_dict() if self.current_window else None,
            "prior_window": self.prior_window.to_dict() if self.prior_window else None,
            "yield_trend": self.yield_trend.value,
            "diminishing_returns": self.diminishing_returns.to_dict(),
            "metric_breakdown": [m.to_dict() for m in self.metric_breakdown],
            "evidence_basis": {
                "digests_analyzed": self.digests_analyzed,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "confidence": self.confidence,
            },
            "constraints": {
                "digest_only_input": True,
                "no_recommendations": True,
                "no_system_alteration": True,
            },
        }
