# -*- coding: utf-8 -*-
"""
Observation Yield Analysis v1
=============================

Station Calyx capability for detecting diminishing returns in continued observation.

PURPOSE:
- Compute observation yield (state changes / total observations)
- Detect when monitoring produces confirmations without state changes
- Report yield metrics without recommending actions

CONSTRAINTS (per HVD-1):
- Digest-only input: Does not access raw evidence
- No recommendations: Reports yield; does not suggest cadence changes
- No system alteration: Does not modify scheduler or observation frequency
- Deterministic: Same digest inputs produce same yield analysis
- Advisory-only: Reports state for human decision-making

INPUT CHAIN:
  Evidence ? Truth Digest ? Yield Analysis

GENERATION TRIGGERS:
- After each digest generation
- Scheduled (same cadence as digest)
- Human-initiated (CLI)
"""

from .analyzer import (
    analyze_node_yield,
    analyze_metric_yield,
    compute_yield,
    detect_diminishing_returns,
)
from .models import (
    YieldMetrics,
    DiminishingReturnsIndicator,
    YieldAnalysisResult,
)

__all__ = [
    "analyze_node_yield",
    "analyze_metric_yield",
    "compute_yield",
    "detect_diminishing_returns",
    "YieldMetrics",
    "DiminishingReturnsIndicator",
    "YieldAnalysisResult",
]
