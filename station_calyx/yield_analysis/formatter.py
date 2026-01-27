# -*- coding: utf-8 -*-
"""
Yield Analysis Formatter
========================

Formats yield analysis results as Markdown and JSON.

OUTPUT CONSTRAINT:
- No recommendations
- No cadence suggestions
- No implied "bad/good"
- Report yield and classification only
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .models import YieldAnalysisResult, DiminishingReturnsStatus


def format_yield_markdown(result: YieldAnalysisResult) -> str:
    """Format yield analysis as Markdown."""
    
    scope_label = f"Metric: {result.metric_scope}" if result.metric_scope else "Node"
    
    lines = [
        f"# OBSERVATION YIELD ANALYSIS - {scope_label} - {result.node_id}",
        "",
        f"**Analysis Timestamp:** {result.analysis_timestamp}",
        "",
        "---",
        "",
        "## YIELD METRICS",
        "",
    ]
    
    # Current window
    if result.current_window:
        cw = result.current_window
        lines.append(
            f"- **Current window:** {cw.state_changes} state changes / "
            f"{cw.total_observations} total observations (yield: {cw.yield_percent}%)"
        )
    else:
        lines.append("- **Current window:** No data")
    
    # Prior window
    if result.prior_window:
        pw = result.prior_window
        lines.append(
            f"- **Prior window:** {pw.state_changes} state changes / "
            f"{pw.total_observations} total observations (yield: {pw.yield_percent}%)"
        )
    else:
        lines.append("- **Prior window:** No data")
    
    lines.append(f"- **Trend:** {result.yield_trend.value}")
    
    lines.extend([
        "",
        "## DIMINISHING RETURNS INDICATOR",
        "",
    ])
    
    dr = result.diminishing_returns
    lines.append(f"- **Status:** {dr.status.value}")
    lines.append(f"- **Windows without state change:** {dr.consecutive_zero_yield_windows}")
    lines.append(f"- **Windows analyzed:** {dr.windows_analyzed}")
    lines.append(f"- **Detection threshold:** {dr.threshold_n} consecutive windows")
    
    if dr.new_entity_in_window:
        lines.append("- **Note:** New entity detected in current window (exception applied)")
    
    # Per-metric breakdown (node-level only)
    if result.metric_breakdown:
        lines.extend([
            "",
            "## PER-METRIC BREAKDOWN",
            "",
        ])
        
        for m in result.metric_breakdown:
            lines.append(
                f"- **{m.metric}:** {m.state_changes} changes, "
                f"{m.confirmations} confirmations (yield: {m.yield_percent}%)"
            )
    
    # Evidence basis
    lines.extend([
        "",
        "## EVIDENCE BASIS",
        "",
        f"- **Digests analyzed:** {len(result.digests_analyzed)}",
        f"- **Period:** {result.period_start or 'unknown'} to {result.period_end or 'unknown'}",
        f"- **Confidence:** {result.confidence}",
        "",
        "### Digest Artifacts Analyzed",
        "",
    ])
    
    for digest_id in result.digests_analyzed[-10:]:  # Show last 10
        lines.append(f"- `{digest_id}`")
    
    if len(result.digests_analyzed) > 10:
        lines.append(f"- ... and {len(result.digests_analyzed) - 10} more")
    
    lines.extend([
        "",
        "---",
        "",
        "*This analysis reports observation yield. It does not recommend actions or cadence changes.*",
    ])
    
    return "\n".join(lines)


def format_yield_json(result: YieldAnalysisResult) -> str:
    """Format yield analysis as JSON."""
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
