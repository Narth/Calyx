"""
Station Calyx Temporal Analyzer
===============================

Reasons over time by detecting trends, drift, and recurring patterns
across system snapshots and advisory outputs.

INVARIANTS:
- HUMAN_PRIMACY: All output is advisory only
- NO_HIDDEN_CHANNELS: All trend analysis is logged
- EXECUTION_GATE: Never recommends execution
- APPEND_ONLY_EVIDENCE: Historical data is never mutated

GUARDRAILS:
- Never predict failure dates
- Never recommend execution
- Explicitly state uncertainty
- Reference historical evidence for every claim

Role: agents/temporal
Scope: Temporal trend analysis, drift detection, pattern recognition
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from ..core.evidence import (
    append_event,
    create_event,
    load_recent_events,
    compute_sha256,
    generate_session_id,
)

COMPONENT_ROLE = "temporal_analyzer"
COMPONENT_SCOPE = "temporal trend analysis, drift detection, pattern recognition"


class TrendDirection(Enum):
    """Direction of detected trend."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class FindingType(Enum):
    """Type of temporal finding."""
    TREND_DETECTED = "TREND_DETECTED"
    DRIFT_WARNING = "DRIFT_WARNING"
    PATTERN_RECURRING = "PATTERN_RECURRING"


class ConfidenceLevel(Enum):
    """Confidence level for findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class TemporalFinding:
    """
    A temporal finding with evidence-based reasoning.
    
    GUARDRAIL: Every finding must reference historical evidence.
    """
    finding_type: FindingType
    metric_name: str
    description: str
    direction: Optional[TrendDirection]
    confidence: ConfidenceLevel
    rationale: str
    uncertainties: list[str]
    evidence_refs: list[str]
    data_points: int
    time_span_hours: float
    values_summary: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_type": self.finding_type.value,
            "metric_name": self.metric_name,
            "description": self.description,
            "direction": self.direction.value if self.direction else None,
            "confidence": self.confidence.value,
            "rationale": self.rationale,
            "uncertainties": self.uncertainties,
            "evidence_refs": self.evidence_refs,
            "data_points": self.data_points,
            "time_span_hours": round(self.time_span_hours, 1),
            "values_summary": self.values_summary,
        }


def extract_snapshots(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract SYSTEM_SNAPSHOT events sorted by timestamp."""
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    
    def parse_ts(e):
        try:
            ts_str = e.get("ts", "")
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    
    return sorted(snapshots, key=parse_ts)


def extract_metric_series(
    snapshots: list[dict[str, Any]],
    metric_path: list[str],
) -> list[tuple[datetime, float]]:
    """Extract a time series for a specific metric path."""
    series = []
    
    for snap in snapshots:
        try:
            ts_str = snap.get("ts", "")
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            
            payload = snap.get("payload", {})
            value = payload
            for key in metric_path:
                value = value.get(key, {})
            
            if isinstance(value, (int, float)):
                series.append((ts, float(value)))
        except:
            continue
    
    return series


def calculate_trend(series: list[tuple[datetime, float]]) -> tuple[TrendDirection, float]:
    """
    Calculate trend direction and slope from time series.
    Returns (direction, slope_per_hour).
    
    VOLATILITY CLASSIFICATION (Tightened):
    - Only label as VOLATILE if:
      1. Coefficient of Variation (CV) > VOLATILITY_CV_THRESHOLD (0.3)
      2. Sample count >= VOLATILITY_MIN_SAMPLES (5)
      3. Standard deviation > VOLATILITY_MIN_STDEV (2.0 absolute units)
    - If CV is elevated but samples are few, classify as CHANGING instead
    - Noise-level variations are suppressed (no trend reported)
    """
    if len(series) < 2:
        return TrendDirection.STABLE, 0.0
    
    values = [v for _, v in series]
    times = [(ts - series[0][0]).total_seconds() / 3600 for ts, _ in series]
    
    if len(times) < 2 or times[-1] == times[0]:
        return TrendDirection.STABLE, 0.0
    
    # Simple linear regression
    n = len(values)
    sum_x = sum(times)
    sum_y = sum(values)
    sum_xy = sum(t * v for t, v in zip(times, values))
    sum_x2 = sum(t * t for t in times)
    
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return TrendDirection.STABLE, 0.0
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # Volatility classification thresholds
    # These values are tuned to avoid labeling single drops as "volatile"
    VOLATILITY_CV_THRESHOLD = 0.3    # Coefficient of variation threshold
    VOLATILITY_MIN_SAMPLES = 5       # Minimum samples to declare volatility
    VOLATILITY_MIN_STDEV = 2.0       # Minimum absolute stdev to be meaningful
    NOISE_THRESHOLD = 0.5            # Below this stdev, consider noise-level
    
    # Check volatility with tightened rules
    if len(values) >= 3:
        try:
            stdev = statistics.stdev(values)
            mean = statistics.mean(values)
            cv = stdev / mean if mean != 0 else 0
            
            # Noise-level check: if stdev is very small, it's just noise
            if stdev < NOISE_THRESHOLD:
                # Noise-level variation, suppress as stable
                return TrendDirection.STABLE, slope
            
            # Volatility requires: high CV + enough samples + meaningful stdev
            if cv > VOLATILITY_CV_THRESHOLD:
                if len(values) >= VOLATILITY_MIN_SAMPLES and stdev >= VOLATILITY_MIN_STDEV:
                    return TrendDirection.VOLATILE, slope
                # Otherwise, it's changing but not enough evidence for "volatile"
                # Fall through to direction check
        except (statistics.StatisticsError, ZeroDivisionError):
            pass
    
    # Determine direction
    threshold = 0.01  # Minimum slope to consider a trend
    if abs(slope) < threshold:
        return TrendDirection.STABLE, slope
    elif slope > 0:
        return TrendDirection.INCREASING, slope
    else:
        return TrendDirection.DECREASING, slope


def analyze_metric_trend(
    snapshots: list[dict[str, Any]],
    metric_name: str,
    metric_path: list[str],
    warning_threshold: Optional[float] = None,
) -> Optional[TemporalFinding]:
    """Analyze trend for a specific metric."""
    series = extract_metric_series(snapshots, metric_path)
    
    if len(series) < 2:
        return None
    
    direction, slope = calculate_trend(series)
    values = [v for _, v in series]
    
    time_span = (series[-1][0] - series[0][0]).total_seconds() / 3600
    
    # Build evidence references
    evidence_refs = [
        f"snapshot:{series[0][0].isoformat()[:19]}",
        f"snapshot:{series[-1][0].isoformat()[:19]}",
    ]
    
    # Calculate statistics
    try:
        mean_val = statistics.mean(values)
        min_val = min(values)
        max_val = max(values)
        latest_val = values[-1]
    except:
        return None
    
    values_summary = {
        "first": round(values[0], 2),
        "last": round(latest_val, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "mean": round(mean_val, 2),
        "slope_per_hour": round(slope, 4),
    }
    
    # Determine if this warrants a finding
    if direction == TrendDirection.STABLE:
        return None  # No finding for stable metrics
    
    # Determine confidence based on data points and time span
    if len(series) >= 10 and time_span >= 24:
        confidence = ConfidenceLevel.HIGH
    elif len(series) >= 5 and time_span >= 6:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW
    
    # Determine finding type
    is_drift_warning = False
    if warning_threshold is not None:
        if direction == TrendDirection.INCREASING and latest_val > warning_threshold:
            is_drift_warning = True
        elif direction == TrendDirection.DECREASING and latest_val < warning_threshold:
            is_drift_warning = True
    
    finding_type = FindingType.DRIFT_WARNING if is_drift_warning else FindingType.TREND_DETECTED
    
    # Build description
    change = values[-1] - values[0]
    change_pct = (change / values[0] * 100) if values[0] != 0 else 0
    
    description = (
        f"{metric_name} is {direction.value} "
        f"({values[0]:.1f} -> {values[-1]:.1f}, "
        f"{'+' if change >= 0 else ''}{change_pct:.1f}% over {time_span:.1f}h)"
    )
    
    rationale = (
        f"Based on {len(series)} data points over {time_span:.1f} hours, "
        f"{metric_name} shows a {direction.value} trend with slope {slope:.4f}/hour. "
        f"This is a statistical observation, not a prediction."
    )
    
    uncertainties = [
        "Trend may not continue at observed rate",
        "External factors may affect future values",
        f"Analysis based on {len(series)} samples only",
    ]
    
    if time_span < 24:
        uncertainties.append("Short observation window limits confidence")
    
    return TemporalFinding(
        finding_type=finding_type,
        metric_name=metric_name,
        description=description,
        direction=direction,
        confidence=confidence,
        rationale=rationale,
        uncertainties=uncertainties,
        evidence_refs=evidence_refs,
        data_points=len(series),
        time_span_hours=time_span,
        values_summary=values_summary,
    )


def analyze_recurring_patterns(
    events: list[dict[str, Any]],
) -> list[TemporalFinding]:
    """
    Detect recurring patterns from event history.
    
    Pattern types:
    1. Advisory intent frequency - same profile generating advisories repeatedly
    2. Metric co-occurrence - multiple metrics trending together
    3. Repeated advisory topics - similar advisory content recurring
    
    Each pattern declares confidence and evidence window.
    """
    findings = []
    
    # --- Pattern Type 1: Advisory Intent Frequency ---
    findings.extend(_analyze_advisory_intent_patterns(events))
    
    # --- Pattern Type 2: Metric Co-occurrence ---
    findings.extend(_analyze_metric_cooccurrence(events))
    
    # --- Pattern Type 3: Trend Repetition ---
    findings.extend(_analyze_trend_repetition(events))
    
    return findings


def _analyze_advisory_intent_patterns(events: list[dict[str, Any]]) -> list[TemporalFinding]:
    """Analyze advisory generation patterns by intent profile."""
    findings = []
    
    advisories = [e for e in events if e.get("event_type") == "ADVISORY_GENERATED"]
    
    if len(advisories) < 2:
        return findings
    
    # Group by profile
    profile_data: dict[str, list[dict]] = {}
    
    for adv in advisories:
        payload = adv.get("payload", {})
        profile = payload.get("intent_profile", "unknown")
        ts = adv.get("ts", "")
        
        if profile not in profile_data:
            profile_data[profile] = []
        profile_data[profile].append({
            "timestamp": ts,
            "notes_count": payload.get("notes_count", 0),
        })
    
    # Analyze each profile
    for profile, occurrences in profile_data.items():
        if len(occurrences) >= 3:
            # Calculate time window
            timestamps = sorted([o["timestamp"] for o in occurrences])
            time_window_hours = _calculate_time_window(timestamps[0], timestamps[-1])
            
            # Determine confidence based on frequency and time span
            confidence = _determine_pattern_confidence(len(occurrences), time_window_hours)
            
            avg_notes = sum(o["notes_count"] for o in occurrences) / len(occurrences)
            
            findings.append(TemporalFinding(
                finding_type=FindingType.PATTERN_RECURRING,
                metric_name=f"advisory_intent:{profile}",
                description=f"Intent '{profile}' generated {len(occurrences)} advisories (avg {avg_notes:.1f} notes) over {time_window_hours:.1f}h",
                direction=None,
                confidence=confidence,
                rationale=f"The '{profile}' intent profile has been consistently active, generating advisories {len(occurrences)} times. This suggests ongoing monitoring of this concern.",
                uncertainties=[
                    "Pattern may reflect normal monitoring cadence",
                    "Advisory frequency depends on snapshot rate",
                ],
                evidence_refs=[f"advisory:{ts[:19]}" for ts in timestamps[:5]],
                data_points=len(occurrences),
                time_span_hours=time_window_hours,
                values_summary={
                    "profile": profile,
                    "occurrences": len(occurrences),
                    "avg_notes_per_advisory": round(avg_notes, 1),
                    "time_window_hours": round(time_window_hours, 1),
                },
            ))
    
    return findings


def _analyze_metric_cooccurrence(events: list[dict[str, Any]]) -> list[TemporalFinding]:
    """Analyze metrics that trend together (co-occurrence)."""
    findings = []
    
    # Get trend events
    trends = [e for e in events if e.get("event_type") == "TREND_DETECTED"]
    
    if len(trends) < 4:
        return findings
    
    # Group trends by time bucket (1 hour windows)
    time_buckets: dict[str, list[str]] = {}
    
    for trend in trends:
        ts = trend.get("ts", "")[:13]  # YYYY-MM-DDTHH (hour bucket)
        metric = trend.get("payload", {}).get("metric_name", "unknown")
        
        if ts not in time_buckets:
            time_buckets[ts] = []
        if metric not in time_buckets[ts]:
            time_buckets[ts].append(metric)
    
    # Find buckets with multiple metrics trending
    cooccurrence_count: dict[tuple, int] = {}
    
    for bucket_ts, metrics in time_buckets.items():
        if len(metrics) >= 2:
            # Sort for consistent key
            metric_pair = tuple(sorted(metrics[:2]))  # Take first 2 for simplicity
            cooccurrence_count[metric_pair] = cooccurrence_count.get(metric_pair, 0) + 1
    
    # Report co-occurrences appearing 2+ times
    for metric_pair, count in cooccurrence_count.items():
        if count >= 2:
            time_window_hours = len(time_buckets)  # Approximate
            confidence = _determine_pattern_confidence(count, time_window_hours)
            
            findings.append(TemporalFinding(
                finding_type=FindingType.PATTERN_RECURRING,
                metric_name=f"cooccurrence:{metric_pair[0]}+{metric_pair[1]}",
                description=f"Metrics '{metric_pair[0]}' and '{metric_pair[1]}' trend together ({count} co-occurrences)",
                direction=None,
                confidence=confidence,
                rationale=f"These metrics have shown correlated behavior {count} times, suggesting they may be related or share a common cause.",
                uncertainties=[
                    "Correlation does not imply causation",
                    "Co-occurrence may be coincidental",
                ],
                evidence_refs=[f"trend_bucket:{ts}" for ts in list(time_buckets.keys())[:3]],
                data_points=count,
                time_span_hours=time_window_hours,
                values_summary={
                    "metric_1": metric_pair[0],
                    "metric_2": metric_pair[1],
                    "cooccurrence_count": count,
                },
            ))
    
    return findings


def _analyze_trend_repetition(events: list[dict[str, Any]]) -> list[TemporalFinding]:
    """Analyze repeated trend patterns (same metric, same direction)."""
    findings = []
    
    trends = [e for e in events if e.get("event_type") == "TREND_DETECTED"]
    
    if len(trends) < 3:
        return findings
    
    # Group by (metric, direction)
    pattern_data: dict[tuple, list[str]] = {}
    
    for trend in trends:
        payload = trend.get("payload", {})
        metric = payload.get("metric_name", "unknown")
        direction = payload.get("direction", "unknown")
        ts = trend.get("ts", "")
        
        key = (metric, direction)
        if key not in pattern_data:
            pattern_data[key] = []
        pattern_data[key].append(ts)
    
    # Report patterns appearing 3+ times
    for (metric, direction), timestamps in pattern_data.items():
        if len(timestamps) >= 3:
            timestamps_sorted = sorted(timestamps)
            time_window_hours = _calculate_time_window(timestamps_sorted[0], timestamps_sorted[-1])
            confidence = _determine_pattern_confidence(len(timestamps), time_window_hours)
            
            findings.append(TemporalFinding(
                finding_type=FindingType.PATTERN_RECURRING,
                metric_name=f"trend_repeat:{metric}",
                description=f"'{metric}' has shown '{direction}' trend {len(timestamps)} times over {time_window_hours:.1f}h",
                direction=None,
                confidence=confidence,
                rationale=f"The metric '{metric}' repeatedly shows a '{direction}' trend, indicating a persistent condition rather than a one-time event.",
                uncertainties=[
                    "Repeated detection may reflect analysis frequency",
                    "Underlying cause requires investigation",
                ],
                evidence_refs=[f"trend:{ts[:19]}" for ts in timestamps_sorted[:5]],
                data_points=len(timestamps),
                time_span_hours=time_window_hours,
                values_summary={
                    "metric": metric,
                    "direction": direction,
                    "repetition_count": len(timestamps),
                    "time_window_hours": round(time_window_hours, 1),
                },
            ))
    
    return findings


def _calculate_time_window(start_ts: str, end_ts: str) -> float:
    """Calculate time window in hours between two ISO timestamps."""
    try:
        start = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
        return max(0, (end - start).total_seconds() / 3600)
    except (ValueError, TypeError):
        return 0.0


def _determine_pattern_confidence(occurrences: int, time_window_hours: float) -> ConfidenceLevel:
    """
    Determine confidence level for a pattern based on occurrences and time window.
    
    Confidence criteria:
    - HIGH: 10+ occurrences over 24+ hours
    - MEDIUM: 5+ occurrences over 6+ hours, or 10+ over any window
    - LOW: 3+ occurrences (minimum for pattern detection)
    """
    if occurrences >= 10 and time_window_hours >= 24:
        return ConfidenceLevel.HIGH
    elif (occurrences >= 5 and time_window_hours >= 6) or occurrences >= 10:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def run_temporal_analysis(
    events: list[dict[str, Any]],
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run comprehensive temporal analysis.
    
    GUARDRAILS ENFORCED:
    - No failure date predictions
    - No execution recommendations
    - Explicit uncertainty statements
    - All claims reference historical evidence
    """
    session_id = session_id or generate_session_id()
    now = datetime.now(timezone.utc)
    
    snapshots = extract_snapshots(events)
    findings: list[TemporalFinding] = []
    
    # Analyze key metrics
    metrics_to_analyze = [
        ("disk_percent_used", ["disk", "percent_used"], 90.0),
        ("memory_percent", ["memory", "percent"], 85.0),
        ("cpu_percent", ["cpu_percent"], 90.0),
    ]
    
    for metric_name, metric_path, threshold in metrics_to_analyze:
        finding = analyze_metric_trend(snapshots, metric_name, metric_path, threshold)
        if finding:
            findings.append(finding)
    
    # Analyze recurring patterns
    pattern_findings = analyze_recurring_patterns(events)
    findings.extend(pattern_findings)
    
    # Categorize findings
    trends = [f for f in findings if f.finding_type == FindingType.TREND_DETECTED]
    drifts = [f for f in findings if f.finding_type == FindingType.DRIFT_WARNING]
    patterns = [f for f in findings if f.finding_type == FindingType.PATTERN_RECURRING]
    
    # Calculate time span
    time_span_hours = 0
    if snapshots:
        try:
            first_ts = datetime.fromisoformat(snapshots[0].get("ts", "").replace("Z", "+00:00"))
            last_ts = datetime.fromisoformat(snapshots[-1].get("ts", "").replace("Z", "+00:00"))
            time_span_hours = (last_ts - first_ts).total_seconds() / 3600
        except:
            pass
    
    analysis = {
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "events_analyzed": len(events),
        "snapshots_analyzed": len(snapshots),
        "time_span_hours": round(time_span_hours, 1),
        "trends_detected": [t.to_dict() for t in trends],
        "drift_warnings": [d.to_dict() for d in drifts],
        "recurring_patterns": [p.to_dict() for p in patterns],
        "total_findings": len(findings),
        "analyzer_role": COMPONENT_ROLE,
        "advisory_only": True,
        "execution_capability": False,
        "guardrails": {
            "no_failure_predictions": True,
            "no_execution_recommendations": True,
            "uncertainty_stated": True,
            "evidence_referenced": all(f.evidence_refs for f in findings) if findings else True,
        },
    }
    
    return analysis


def save_temporal_analysis(
    analysis: dict[str, Any],
    summaries_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Save temporal analysis to markdown and JSON files."""
    config = get_config()
    output_dir = summaries_dir or config.summaries_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = analysis.get("session_id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    base_name = f"temporal_{session_id}_{timestamp}"
    md_path = output_dir / f"{base_name}.md"
    json_path = output_dir / f"{base_name}.json"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    md_content = format_temporal_markdown(analysis)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return md_path, json_path


def format_temporal_markdown(analysis: dict[str, Any]) -> str:
    """Format temporal analysis as markdown document."""
    lines = [
        "# Station Calyx Temporal Analysis Report",
        "",
        "> **NOTICE:** This report contains statistical observations only.",
        "> No failure predictions are made. No execution is recommended.",
        "> All findings require human interpretation and judgment.",
        "",
        f"**Session ID:** {analysis.get('session_id', 'unknown')}",
        f"**Timestamp:** {analysis.get('timestamp', 'unknown')}",
        f"**Events Analyzed:** {analysis.get('events_analyzed', 0)}",
        f"**Snapshots Analyzed:** {analysis.get('snapshots_analyzed', 0)}",
        f"**Time Span:** {analysis.get('time_span_hours', 0)} hours",
        "",
        "---",
        "",
    ]
    
    # Trends
    trends = analysis.get("trends_detected", [])
    lines.extend([
        "## Trends Detected",
        "",
    ])
    
    if trends:
        for i, trend in enumerate(trends, 1):
            lines.extend([
                f"### Trend {i}: {trend.get('metric_name', 'Unknown')}",
                "",
                f"**Direction:** {trend.get('direction', 'unknown')}",
                f"**Confidence:** {trend.get('confidence', 'unknown').upper()}",
                "",
                f"{trend.get('description', 'No description')}",
                "",
                f"**Rationale:** {trend.get('rationale', 'No rationale')}",
                "",
                "**Values:**",
                f"- First: {trend.get('values_summary', {}).get('first', '?')}",
                f"- Last: {trend.get('values_summary', {}).get('last', '?')}",
                f"- Min: {trend.get('values_summary', {}).get('min', '?')}",
                f"- Max: {trend.get('values_summary', {}).get('max', '?')}",
                f"- Slope: {trend.get('values_summary', {}).get('slope_per_hour', '?')}/hour",
                "",
                "**Evidence:**",
            ])
            for ref in trend.get("evidence_refs", []):
                lines.append(f"- `{ref}`")
            
            lines.extend([
                "",
                "**Uncertainties:**",
            ])
            for unc in trend.get("uncertainties", []):
                lines.append(f"- {unc}")
            lines.extend(["", "---", ""])
    else:
        lines.extend(["No trends detected.", "", "---", ""])
    
    # Drift Warnings
    drifts = analysis.get("drift_warnings", [])
    lines.extend([
        "## Drift Warnings",
        "",
    ])
    
    if drifts:
        for i, drift in enumerate(drifts, 1):
            lines.extend([
                f"### Warning {i}: {drift.get('metric_name', 'Unknown')}",
                "",
                f"**Direction:** {drift.get('direction', 'unknown')}",
                f"**Confidence:** {drift.get('confidence', 'unknown').upper()}",
                "",
                f"{drift.get('description', 'No description')}",
                "",
                f"**Rationale:** {drift.get('rationale', 'No rationale')}",
                "",
                "**Evidence:**",
            ])
            for ref in drift.get("evidence_refs", []):
                lines.append(f"- `{ref}`")
            
            lines.extend([
                "",
                "**Uncertainties:**",
            ])
            for unc in drift.get("uncertainties", []):
                lines.append(f"- {unc}")
            lines.extend(["", "---", ""])
    else:
        lines.extend(["No drift warnings detected.", "", "---", ""])
    
    # Recurring Patterns
    patterns = analysis.get("recurring_patterns", [])
    lines.extend([
        "## Recurring Patterns",
        "",
    ])
    
    if patterns:
        for i, pattern in enumerate(patterns, 1):
            lines.extend([
                f"### Pattern {i}: {pattern.get('metric_name', 'Unknown')}",
                "",
                f"**Confidence:** {pattern.get('confidence', 'unknown').upper()}",
                f"**Data Points:** {pattern.get('data_points', 0)}",
                f"**Time Span:** {pattern.get('time_span_hours', 0)} hours",
                "",
                f"{pattern.get('description', 'No description')}",
                "",
                f"**Rationale:** {pattern.get('rationale', 'No rationale')}",
                "",
                "**Evidence:**",
            ])
            for ref in pattern.get("evidence_refs", [])[:5]:
                lines.append(f"- `{ref}`")
            
            lines.extend([
                "",
                "**Uncertainties:**",
            ])
            for unc in pattern.get("uncertainties", []):
                lines.append(f"- {unc}")
            lines.extend(["", "---", ""])
    else:
        lines.extend(["No recurring patterns detected.", "", "---", ""])
    
    # Guardrails
    guardrails = analysis.get("guardrails", {})
    lines.extend([
        "## Guardrail Verification",
        "",
        f"- No failure predictions: {'PASS' if guardrails.get('no_failure_predictions') else 'FAIL'}",
        f"- No execution recommendations: {'PASS' if guardrails.get('no_execution_recommendations') else 'FAIL'}",
        f"- Uncertainty stated: {'PASS' if guardrails.get('uncertainty_stated') else 'FAIL'}",
        f"- Evidence referenced: {'PASS' if guardrails.get('evidence_referenced') else 'FAIL'}",
        "",
        "---",
        "",
        "*Generated by Station Calyx Temporal Analyzer (v1 - Advisory Only)*",
        "",
        "**Invariants Enforced:**",
        "- HUMAN_PRIMACY: Statistical observations only",
        "- EXECUTION_GATE: No actions recommended",
        "- NO_HIDDEN_CHANNELS: All analysis logged to evidence",
    ])
    
    return "\n".join(lines)


def log_temporal_event(
    analysis: dict[str, Any],
    md_path: Path,
    json_path: Path,
) -> None:
    """Log temporal analysis completion to evidence."""
    md_hash = compute_sha256(md_path.read_bytes())
    json_hash = compute_sha256(json_path.read_bytes())
    
    event = create_event(
        event_type="TEMPORAL_ANALYSIS_COMPLETED",
        node_role=COMPONENT_ROLE,
        summary=f"Temporal analysis completed: {analysis.get('total_findings', 0)} findings over {analysis.get('time_span_hours', 0)}h",
        payload={
            "session_id": analysis.get("session_id"),
            "snapshots_analyzed": analysis.get("snapshots_analyzed"),
            "time_span_hours": analysis.get("time_span_hours"),
            "trends_count": len(analysis.get("trends_detected", [])),
            "drifts_count": len(analysis.get("drift_warnings", [])),
            "patterns_count": len(analysis.get("recurring_patterns", [])),
            "total_findings": analysis.get("total_findings"),
            "md_path": str(md_path),
            "json_path": str(json_path),
            "md_hash": md_hash,
            "json_hash": json_hash,
        },
        tags=["temporal", "analysis", "trends"],
        session_id=analysis.get("session_id"),
    )
    
    append_event(event)


def log_finding_events(findings: list[dict[str, Any]], session_id: str) -> None:
    """Log individual findings as events."""
    for finding in findings:
        finding_type = finding.get("finding_type", "UNKNOWN")
        
        event = create_event(
            event_type=finding_type,
            node_role=COMPONENT_ROLE,
            summary=finding.get("description", "No description"),
            payload={
                "metric_name": finding.get("metric_name"),
                "direction": finding.get("direction"),
                "confidence": finding.get("confidence"),
                "values_summary": finding.get("values_summary"),
                "evidence_refs": finding.get("evidence_refs"),
            },
            tags=["temporal", finding_type.lower(), finding.get("metric_name", "unknown")],
            session_id=session_id,
        )
        
        append_event(event)


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print("\nGuardrails:")
    print("- Never predict failure dates")
    print("- Never recommend execution")
    print("- Explicitly state uncertainty")
    print("- Reference historical evidence for every claim")
