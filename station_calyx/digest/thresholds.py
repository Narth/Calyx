# -*- coding: utf-8 -*-
"""
Threshold Learning and Management
=================================

Learns thresholds from observed system behavior.
Supports human override without silent inference.

CONSTRAINTS:
- Thresholds learned from evidence only
- Human overrides logged as evidence events
- No autonomous tightening/loosening
- Changes are transparent and queryable
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config


@dataclass
class ThresholdDefinition:
    """Definition of a threshold for a metric."""
    metric: str
    high: Optional[float] = None
    low: Optional[float] = None
    source: str = "learned"  # learned, human_override, default
    learned_from_samples: int = 0
    last_updated: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThresholdDefinition":
        return cls(**data)


@dataclass
class LearnedThresholds:
    """Collection of learned thresholds."""
    thresholds: dict[str, ThresholdDefinition] = field(default_factory=dict)
    last_learning_run: Optional[str] = None
    total_samples_analyzed: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "thresholds": {k: v.to_dict() for k, v in self.thresholds.items()},
            "last_learning_run": self.last_learning_run,
            "total_samples_analyzed": self.total_samples_analyzed,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnedThresholds":
        thresholds = {
            k: ThresholdDefinition.from_dict(v)
            for k, v in data.get("thresholds", {}).items()
        }
        return cls(
            thresholds=thresholds,
            last_learning_run=data.get("last_learning_run"),
            total_samples_analyzed=data.get("total_samples_analyzed", 0),
        )


def get_thresholds_path() -> Path:
    """Get path to thresholds file."""
    config = get_config()
    thresholds_dir = config.data_dir / "digests" / "thresholds"
    thresholds_dir.mkdir(parents=True, exist_ok=True)
    return thresholds_dir / "learned_thresholds.json"


def load_thresholds() -> LearnedThresholds:
    """Load thresholds from storage."""
    path = get_thresholds_path()
    
    if not path.exists():
        return LearnedThresholds()
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return LearnedThresholds.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return LearnedThresholds()


def save_thresholds(thresholds: LearnedThresholds) -> None:
    """Save thresholds to storage."""
    path = get_thresholds_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(thresholds.to_dict(), f, indent=2)


def learn_thresholds(
    observations: list[dict[str, Any]],
    metrics: list[str],
    percentile_low: float = 10.0,
    percentile_high: float = 90.0,
) -> LearnedThresholds:
    """
    Learn thresholds from observed data using percentiles.
    
    Args:
        observations: List of observation dicts with metric values
        metrics: List of metric names to learn thresholds for
        percentile_low: Percentile for low threshold (default 10th)
        percentile_high: Percentile for high threshold (default 90th)
        
    Returns:
        LearnedThresholds with computed boundaries
    """
    from statistics import quantiles
    
    current = load_thresholds()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for metric in metrics:
        # Extract values for this metric
        values = []
        for obs in observations:
            value = obs.get(metric)
            if value is not None and isinstance(value, (int, float)):
                values.append(float(value))
        
        if len(values) < 10:
            # Not enough data to learn meaningful thresholds
            continue
        
        # Compute percentiles
        try:
            # quantiles returns n-1 cut points for n quantiles
            cuts = quantiles(values, n=100)
            low_idx = int(percentile_low) - 1
            high_idx = int(percentile_high) - 1
            
            low_threshold = cuts[max(0, low_idx)]
            high_threshold = cuts[min(len(cuts) - 1, high_idx)]
        except Exception:
            continue
        
        # Check if this is an update or new
        existing = current.thresholds.get(metric)
        
        # Only update if source is "learned" (don't override human)
        if existing and existing.source == "human_override":
            continue
        
        current.thresholds[metric] = ThresholdDefinition(
            metric=metric,
            high=high_threshold,
            low=low_threshold,
            source="learned",
            learned_from_samples=len(values),
            last_updated=timestamp,
            notes=f"Learned from {len(values)} samples, P{percentile_low}/P{percentile_high}",
        )
    
    current.last_learning_run = timestamp
    current.total_samples_analyzed = len(observations)
    
    save_thresholds(current)
    
    # Log threshold learning as evidence event
    _log_threshold_learning_event(current, metrics)
    
    return current


def set_threshold_override(
    metric: str,
    boundary: str,  # "high" or "low"
    value: float,
    notes: Optional[str] = None,
) -> ThresholdDefinition:
    """
    Set a human override for a threshold.
    
    This is logged as an evidence event for auditability.
    
    Args:
        metric: Metric name
        boundary: "high" or "low"
        value: Threshold value
        notes: Optional human notes
        
    Returns:
        Updated ThresholdDefinition
    """
    current = load_thresholds()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    existing = current.thresholds.get(metric, ThresholdDefinition(metric=metric))
    
    # Update the specified boundary
    if boundary == "high":
        existing.high = value
    elif boundary == "low":
        existing.low = value
    else:
        raise ValueError(f"Invalid boundary: {boundary}. Must be 'high' or 'low'.")
    
    existing.source = "human_override"
    existing.last_updated = timestamp
    existing.notes = notes or f"Human override: {boundary}={value}"
    
    current.thresholds[metric] = existing
    save_thresholds(current)
    
    # Log override as evidence event
    _log_threshold_override_event(metric, boundary, value, notes)
    
    return existing


def get_threshold_for_metric(metric: str) -> Optional[ThresholdDefinition]:
    """Get threshold definition for a specific metric."""
    current = load_thresholds()
    return current.thresholds.get(metric)


def get_all_thresholds() -> dict[str, ThresholdDefinition]:
    """Get all threshold definitions."""
    current = load_thresholds()
    return current.thresholds


def _log_threshold_learning_event(
    thresholds: LearnedThresholds,
    metrics: list[str],
) -> None:
    """Log threshold learning as evidence event."""
    try:
        from ..core.evidence import add_event
        
        add_event(
            event_type="THRESHOLD_LEARNING",
            component="digest_thresholds",
            summary=f"Learned thresholds for {len(metrics)} metrics from {thresholds.total_samples_analyzed} samples",
            data={
                "metrics": metrics,
                "samples_analyzed": thresholds.total_samples_analyzed,
                "thresholds_updated": [
                    m for m in metrics if m in thresholds.thresholds
                ],
            },
        )
    except Exception:
        pass  # Don't fail threshold learning if logging fails


def _log_threshold_override_event(
    metric: str,
    boundary: str,
    value: float,
    notes: Optional[str],
) -> None:
    """Log human threshold override as evidence event."""
    try:
        from ..core.evidence import add_event
        
        add_event(
            event_type="THRESHOLD_OVERRIDE",
            component="digest_thresholds",
            summary=f"Human override: {metric}.{boundary} = {value}",
            data={
                "metric": metric,
                "boundary": boundary,
                "value": value,
                "notes": notes,
                "source": "human_override",
            },
        )
    except Exception:
        pass
