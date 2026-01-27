# -*- coding: utf-8 -*-
"""
State Classifier for Truth Digest
=================================

Classifies observations as state changes or state confirmations.

CLASSIFICATION CRITERIA:

State Change:
- Direction reversal (increasing ? decreasing)
- Classification transition (stable ? volatile)
- Threshold crossing
- First observation
- Pattern emergence/cessation

State Confirmation:
- Same direction as prior
- Same classification as prior
- Within threshold band
- Pattern continuation
- Absence persistence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class StateType(Enum):
    """Types of state classification."""
    CHANGE = "change"
    CONFIRMATION = "confirmation"


class ChangeReason(Enum):
    """Reasons for state change classification."""
    DIRECTION_REVERSAL = "direction_reversal"
    CLASSIFICATION_TRANSITION = "classification_transition"
    THRESHOLD_CROSSING = "threshold_crossing"
    FIRST_OBSERVATION = "first_observation"
    PATTERN_EMERGENCE = "pattern_emergence"
    PATTERN_CESSATION = "pattern_cessation"
    NEW_ENTITY = "new_entity"


class ConfirmationReason(Enum):
    """Reasons for state confirmation classification."""
    SAME_DIRECTION = "same_direction"
    SAME_CLASSIFICATION = "same_classification"
    WITHIN_THRESHOLD = "within_threshold"
    PATTERN_CONTINUATION = "pattern_continuation"
    ABSENCE_PERSISTENCE = "absence_persistence"
    COUNT_INCREMENT = "count_increment"


@dataclass
class StateChange:
    """Represents a state change observation."""
    metric: str
    prior_state: Any
    current_state: Any
    reason: ChangeReason
    evidence_count: int
    first_observed: str  # ISO timestamp
    last_observed: str   # ISO timestamp
    evidence_refs: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "state_change",
            "metric": self.metric,
            "prior_state": self.prior_state,
            "current_state": self.current_state,
            "reason": self.reason.value,
            "evidence_count": self.evidence_count,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
            "evidence_refs": self.evidence_refs[:10],  # Bounded
        }


@dataclass
class StateConfirmation:
    """Represents a state confirmation (unchanged condition)."""
    metric: str
    state: Any
    reason: ConfirmationReason
    observation_count: int
    first_observed: str
    last_observed: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "state_confirmation",
            "metric": self.metric,
            "state": self.state,
            "reason": self.reason.value,
            "observation_count": self.observation_count,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
        }


@dataclass
class MetricState:
    """Tracks the current known state of a metric."""
    metric: str
    direction: Optional[str] = None  # increasing, decreasing, stable, volatile
    classification: Optional[str] = None  # stable, volatile, constrained, etc.
    value: Optional[float] = None
    threshold_band: Optional[str] = None  # above_high, below_low, normal
    last_updated: Optional[str] = None
    observation_count: int = 0


def classify_direction_change(
    prior_direction: Optional[str],
    current_direction: str,
) -> tuple[StateType, ChangeReason | ConfirmationReason]:
    """Classify whether a direction observation is a change or confirmation."""
    
    if prior_direction is None:
        return StateType.CHANGE, ChangeReason.FIRST_OBSERVATION
    
    if prior_direction != current_direction:
        return StateType.CHANGE, ChangeReason.DIRECTION_REVERSAL
    
    return StateType.CONFIRMATION, ConfirmationReason.SAME_DIRECTION


def classify_classification_change(
    prior_class: Optional[str],
    current_class: str,
) -> tuple[StateType, ChangeReason | ConfirmationReason]:
    """Classify whether a classification observation is a change or confirmation."""
    
    if prior_class is None:
        return StateType.CHANGE, ChangeReason.FIRST_OBSERVATION
    
    if prior_class != current_class:
        return StateType.CHANGE, ChangeReason.CLASSIFICATION_TRANSITION
    
    return StateType.CONFIRMATION, ConfirmationReason.SAME_CLASSIFICATION


def classify_threshold_crossing(
    prior_band: Optional[str],
    current_band: str,
    value: float,
    thresholds: dict[str, float],
) -> tuple[StateType, ChangeReason | ConfirmationReason]:
    """Classify whether a value crossed a threshold boundary."""
    
    if prior_band is None:
        return StateType.CHANGE, ChangeReason.FIRST_OBSERVATION
    
    if prior_band != current_band:
        return StateType.CHANGE, ChangeReason.THRESHOLD_CROSSING
    
    return StateType.CONFIRMATION, ConfirmationReason.WITHIN_THRESHOLD


def determine_threshold_band(
    value: float,
    thresholds: dict[str, float],
) -> str:
    """Determine which threshold band a value falls into."""
    
    high = thresholds.get("high")
    low = thresholds.get("low")
    
    if high is not None and value >= high:
        return "above_high"
    if low is not None and value <= low:
        return "below_low"
    return "normal"


def classify_state(
    metric: str,
    observation: dict[str, Any],
    prior_state: Optional[MetricState],
    thresholds: dict[str, dict[str, float]],
) -> tuple[StateType, StateChange | StateConfirmation]:
    """
    Classify an observation as state change or confirmation.
    
    Args:
        metric: Name of the metric
        observation: Current observation data
        prior_state: Previous known state (None if first)
        thresholds: Threshold definitions per metric
        
    Returns:
        Tuple of (state_type, change_or_confirmation_object)
    """
    
    current_direction = observation.get("direction")
    current_classification = observation.get("classification")
    current_value = observation.get("value")
    timestamp = observation.get("timestamp", datetime.now().isoformat())
    evidence_count = observation.get("evidence_count", 1)
    
    metric_thresholds = thresholds.get(metric, {})
    
    # Determine current threshold band if value present
    current_band = None
    if current_value is not None and metric_thresholds:
        current_band = determine_threshold_band(current_value, metric_thresholds)
    
    # Check for first observation
    if prior_state is None or prior_state.observation_count == 0:
        return StateType.CHANGE, StateChange(
            metric=metric,
            prior_state=None,
            current_state={
                "direction": current_direction,
                "classification": current_classification,
                "value": current_value,
                "band": current_band,
            },
            reason=ChangeReason.FIRST_OBSERVATION,
            evidence_count=evidence_count,
            first_observed=timestamp,
            last_observed=timestamp,
        )
    
    # Check direction change
    if current_direction and prior_state.direction:
        state_type, reason = classify_direction_change(
            prior_state.direction, current_direction
        )
        if state_type == StateType.CHANGE:
            return StateType.CHANGE, StateChange(
                metric=metric,
                prior_state=prior_state.direction,
                current_state=current_direction,
                reason=reason,
                evidence_count=evidence_count,
                first_observed=prior_state.last_updated or timestamp,
                last_observed=timestamp,
            )
    
    # Check classification change
    if current_classification and prior_state.classification:
        state_type, reason = classify_classification_change(
            prior_state.classification, current_classification
        )
        if state_type == StateType.CHANGE:
            return StateType.CHANGE, StateChange(
                metric=metric,
                prior_state=prior_state.classification,
                current_state=current_classification,
                reason=reason,
                evidence_count=evidence_count,
                first_observed=prior_state.last_updated or timestamp,
                last_observed=timestamp,
            )
    
    # Check threshold crossing
    if current_band and prior_state.threshold_band:
        state_type, reason = classify_threshold_crossing(
            prior_state.threshold_band, current_band, current_value, metric_thresholds
        )
        if state_type == StateType.CHANGE:
            return StateType.CHANGE, StateChange(
                metric=metric,
                prior_state=f"{prior_state.value} ({prior_state.threshold_band})",
                current_state=f"{current_value} ({current_band})",
                reason=reason,
                evidence_count=evidence_count,
                first_observed=prior_state.last_updated or timestamp,
                last_observed=timestamp,
            )
    
    # No change detected - this is a confirmation
    return StateType.CONFIRMATION, StateConfirmation(
        metric=metric,
        state={
            "direction": current_direction or prior_state.direction,
            "classification": current_classification or prior_state.classification,
            "value": current_value,
        },
        reason=ConfirmationReason.SAME_CLASSIFICATION,
        observation_count=prior_state.observation_count + 1,
        first_observed=prior_state.last_updated or timestamp,
        last_observed=timestamp,
    )
