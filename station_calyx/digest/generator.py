# -*- coding: utf-8 -*-
"""
Truth Digest Generator
======================

Generates Truth Digests from evidence.

GENERATION MODES:
- Per-node: All metrics for a single node
- Per-metric: Single metric across time

TRIGGERS:
- Fixed-interval (scheduler)
- State-change (event-driven)
- Human-initiated (CLI)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from ..core.evidence import load_recent_events
from .classifier import (
    StateChange,
    StateConfirmation,
    StateType,
    MetricState,
    classify_state,
    ChangeReason,
    ConfirmationReason,
)
from .thresholds import load_thresholds, learn_thresholds, get_all_thresholds
from .formatter import format_digest_markdown, format_digest_json


# Metrics tracked for digests
TRACKED_METRICS = [
    "cpu_percent",
    "memory_percent",
    "disk_percent_used",
]


def get_digests_dir(node_id: str) -> Path:
    """Get digest storage directory for a node."""
    config = get_config()
    digest_dir = config.data_dir / "digests" / node_id
    digest_dir.mkdir(parents=True, exist_ok=True)
    return digest_dir


def generate_node_digest(
    node_id: str,
    since: Optional[datetime] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Generate a Truth Digest for a node (all metrics).
    
    Args:
        node_id: Node identifier (use "local" for local evidence)
        since: Start of period (default: last 24 hours)
        persist: Whether to save as artifact
        
    Returns:
        Digest data structure
    """
    
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # Ensure since is timezone-aware
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    
    # Load evidence
    events = load_recent_events(5000)
    
    # Filter to period
    period_events = [
        e for e in events
        if e.get("ts", "") >= since.isoformat()
    ]
    
    # Extract snapshots for metrics
    snapshots = [
        e for e in period_events
        if e.get("event_type") == "SYSTEM_SNAPSHOT"
    ]
    
    # Extract trend/drift events
    trend_events = [
        e for e in period_events
        if e.get("event_type") in ("TREND_DETECTED", "DRIFT_WARNING")
    ]
    
    # Load or learn thresholds
    thresholds_obj = load_thresholds()
    thresholds = {k: {"high": v.high, "low": v.low} for k, v in thresholds_obj.thresholds.items()}
    
    # If we have snapshots, learn thresholds
    if len(snapshots) >= 10:
        snapshot_data = [e.get("data", {}) for e in snapshots]
        learn_thresholds(snapshot_data, TRACKED_METRICS)
        thresholds_obj = load_thresholds()
        thresholds = {k: {"high": v.high, "low": v.low} for k, v in thresholds_obj.thresholds.items()}
    
    # Classify each metric
    state_changes: list[StateChange] = []
    state_confirmations: list[StateConfirmation] = []
    
    # Track state per metric across observations
    metric_states: dict[str, MetricState] = {}
    metric_observations: dict[str, list[dict]] = {m: [] for m in TRACKED_METRICS}
    
    # Process trend events to extract state observations
    for event in trend_events:
        # Check both 'data' and 'payload' for compatibility
        payload = event.get("payload", event.get("data", {}))
        metric = payload.get("metric_name", payload.get("metric"))
        if metric not in TRACKED_METRICS:
            continue
        
        # Extract direction from payload
        direction = payload.get("direction")
        values_summary = payload.get("values_summary", {})
        
        observation = {
            "timestamp": event.get("ts"),
            "direction": direction,
            "classification": direction,  # Use direction as classification
            "value": values_summary.get("last", payload.get("current_value")),
            "evidence_count": 1,
        }
        metric_observations[metric].append(observation)
    
    # Also extract from snapshots
    for snapshot in snapshots:
        data = snapshot.get("data", snapshot.get("payload", {}))
        ts = snapshot.get("ts")
        
        for metric in TRACKED_METRICS:
            value = data.get(metric)
            if value is None and metric == "memory_percent":
                value = data.get("memory", {}).get("percent")
            if value is None and metric == "disk_percent_used":
                value = data.get("disk", {}).get("percent_used")
            
            if value is not None:
                metric_observations[metric].append({
                    "timestamp": ts,
                    "value": value,
                    "evidence_count": 1,
                })
    
    # Classify observations for each metric
    for metric in TRACKED_METRICS:
        observations = metric_observations[metric]
        if not observations:
            continue
        
        # Sort by timestamp
        observations.sort(key=lambda x: x.get("timestamp", ""))
        
        prior_state: Optional[MetricState] = None
        changes_for_metric: list[StateChange] = []
        confirmations_for_metric: list[StateConfirmation] = []
        
        for obs in observations:
            state_type, result = classify_state(metric, obs, prior_state, thresholds)
            
            if state_type == StateType.CHANGE:
                changes_for_metric.append(result)
                # Update prior state
                prior_state = MetricState(
                    metric=metric,
                    direction=obs.get("direction"),
                    classification=obs.get("classification"),
                    value=obs.get("value"),
                    last_updated=obs.get("timestamp"),
                    observation_count=1,
                )
            else:
                confirmations_for_metric.append(result)
                if prior_state:
                    prior_state.observation_count += 1
                    prior_state.last_updated = obs.get("timestamp")
        
        # Consolidate: only report first and last change if direction stable
        if changes_for_metric:
            # Keep first change (establishes state)
            state_changes.append(changes_for_metric[0])
            
            # Check if final state differs from first
            if len(changes_for_metric) > 1:
                first_state = changes_for_metric[0].current_state
                last_state = changes_for_metric[-1].current_state
                if first_state != last_state:
                    state_changes.append(changes_for_metric[-1])
        
        # Consolidate confirmations
        if confirmations_for_metric:
            total_obs = sum(c.observation_count for c in confirmations_for_metric)
            last_conf = confirmations_for_metric[-1]
            state_confirmations.append(StateConfirmation(
                metric=metric,
                state=last_conf.state,
                reason=ConfirmationReason.SAME_CLASSIFICATION,
                observation_count=total_obs,
                first_observed=confirmations_for_metric[0].first_observed,
                last_observed=last_conf.last_observed,
            ))
    
    # Determine period bounds
    if period_events:
        period_start = min(e.get("ts", "") for e in period_events)
        period_end = max(e.get("ts", "") for e in period_events)
    else:
        period_start = since.isoformat()
        period_end = datetime.now(timezone.utc).isoformat()
    
    # Calculate evidence basis
    window_hours = (datetime.now(timezone.utc) - since).total_seconds() / 3600
    evidence_basis = {
        "window_hours": round(window_hours, 1),
        "snapshot_count": len(snapshots),
        "events_analyzed": len(period_events),
        "trend_events": len(trend_events),
        "confidence": _calculate_confidence(len(snapshots), window_hours),
    }
    
    # Format outputs
    markdown = format_digest_markdown(
        node_id=node_id,
        period_start=period_start,
        period_end=period_end,
        state_changes=state_changes,
        state_confirmations=state_confirmations,
        open_observations=[],
        evidence_basis=evidence_basis,
    )
    
    json_output = format_digest_json(
        node_id=node_id,
        period_start=period_start,
        period_end=period_end,
        state_changes=state_changes,
        state_confirmations=state_confirmations,
        open_observations=[],
        evidence_basis=evidence_basis,
    )
    
    result = {
        "node_id": node_id,
        "period_start": period_start,
        "period_end": period_end,
        "state_changes": [sc.to_dict() for sc in state_changes],
        "state_confirmations": [sc.to_dict() for sc in state_confirmations],
        "evidence_basis": evidence_basis,
        "markdown": markdown,
        "json": json_output,
    }
    
    # Persist if requested
    if persist:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        digest_dir = get_digests_dir(node_id)
        
        md_path = digest_dir / f"truth_digest_node_{node_id}_{timestamp}.md"
        json_path = digest_dir / f"truth_digest_node_{node_id}_{timestamp}.json"
        
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json_output, encoding="utf-8")
        
        result["artifact_paths"] = {
            "markdown": str(md_path),
            "json": str(json_path),
        }
        
        # Log generation as evidence event
        _log_digest_generation(node_id, None, len(state_changes), len(state_confirmations))
    
    return result


def generate_metric_digest(
    node_id: str,
    metric: str,
    since: Optional[datetime] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Generate a Truth Digest for a single metric.
    
    Args:
        node_id: Node identifier
        metric: Metric name
        since: Start of period
        persist: Whether to save as artifact
        
    Returns:
        Digest data structure
    """
    
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # Ensure since is timezone-aware
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    
    # Load evidence
    events = load_recent_events(5000)
    
    # Filter to period
    period_events = [
        e for e in events
        if e.get("ts", "") >= since.isoformat()
    ]
    
    # Extract relevant events for this metric
    snapshots = [
        e for e in period_events
        if e.get("event_type") == "SYSTEM_SNAPSHOT"
    ]
    
    # Filter trend events for this metric (check both payload and data)
    trend_events = []
    for e in period_events:
        if e.get("event_type") not in ("TREND_DETECTED", "DRIFT_WARNING"):
            continue
        payload = e.get("payload", e.get("data", {}))
        metric_name = payload.get("metric_name", payload.get("metric"))
        if metric_name == metric:
            trend_events.append(e)
    
    # Load thresholds
    thresholds_obj = load_thresholds()
    thresholds = {k: {"high": v.high, "low": v.low} for k, v in thresholds_obj.thresholds.items()}
    
    # Collect observations
    observations = []
    
    for event in trend_events:
        payload = event.get("payload", event.get("data", {}))
        direction = payload.get("direction")
        values_summary = payload.get("values_summary", {})
        observations.append({
            "timestamp": event.get("ts"),
            "direction": direction,
            "classification": direction,
            "value": values_summary.get("last", payload.get("current_value")),
            "evidence_count": 1,
        })
    
    for snapshot in snapshots:
        data = snapshot.get("data", snapshot.get("payload", {}))
        value = data.get(metric)
        if value is None and metric == "memory_percent":
            value = data.get("memory", {}).get("percent")
        if value is None and metric == "disk_percent_used":
            value = data.get("disk", {}).get("percent_used")
        
        if value is not None:
            observations.append({
                "timestamp": snapshot.get("ts"),
                "value": value,
                "evidence_count": 1,
            })
    
    # Sort and classify
    observations.sort(key=lambda x: x.get("timestamp", ""))
    
    state_changes: list[StateChange] = []
    state_confirmations: list[StateConfirmation] = []
    prior_state: Optional[MetricState] = None
    
    for obs in observations:
        state_type, result = classify_state(metric, obs, prior_state, thresholds)
        
        if state_type == StateType.CHANGE:
            state_changes.append(result)
            prior_state = MetricState(
                metric=metric,
                direction=obs.get("direction"),
                classification=obs.get("classification"),
                value=obs.get("value"),
                last_updated=obs.get("timestamp"),
                observation_count=1,
            )
        else:
            if prior_state:
                prior_state.observation_count += 1
    
    # Create single consolidated confirmation if stable
    if prior_state and prior_state.observation_count > 1:
        state_confirmations.append(StateConfirmation(
            metric=metric,
            state={
                "direction": prior_state.direction,
                "classification": prior_state.classification,
                "value": prior_state.value,
            },
            reason=ConfirmationReason.SAME_CLASSIFICATION,
            observation_count=prior_state.observation_count,
            first_observed=observations[0].get("timestamp", "") if observations else "",
            last_observed=prior_state.last_updated or "",
        ))
    
    # Period bounds
    if observations:
        period_start = observations[0].get("timestamp", since.isoformat())
        period_end = observations[-1].get("timestamp", datetime.now(timezone.utc).isoformat())
    else:
        period_start = since.isoformat()
        period_end = datetime.now(timezone.utc).isoformat()
    
    # Evidence basis
    window_hours = (datetime.now(timezone.utc) - since).total_seconds() / 3600
    evidence_basis = {
        "window_hours": round(window_hours, 1),
        "snapshot_count": len(snapshots),
        "events_analyzed": len(observations),
        "trend_events": len(trend_events),
        "confidence": _calculate_confidence(len(observations), window_hours),
    }
    
    # Format
    markdown = format_digest_markdown(
        node_id=node_id,
        period_start=period_start,
        period_end=period_end,
        state_changes=state_changes,
        state_confirmations=state_confirmations,
        open_observations=[],
        evidence_basis=evidence_basis,
        metric_scope=metric,
    )
    
    json_output = format_digest_json(
        node_id=node_id,
        period_start=period_start,
        period_end=period_end,
        state_changes=state_changes,
        state_confirmations=state_confirmations,
        open_observations=[],
        evidence_basis=evidence_basis,
        metric_scope=metric,
    )
    
    result = {
        "node_id": node_id,
        "metric": metric,
        "period_start": period_start,
        "period_end": period_end,
        "state_changes": [sc.to_dict() for sc in state_changes],
        "state_confirmations": [sc.to_dict() for sc in state_confirmations],
        "evidence_basis": evidence_basis,
        "markdown": markdown,
        "json": json_output,
    }
    
    if persist:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        digest_dir = get_digests_dir(node_id)
        
        safe_metric = metric.replace(".", "_")
        md_path = digest_dir / f"truth_digest_metric_{safe_metric}_{node_id}_{timestamp}.md"
        json_path = digest_dir / f"truth_digest_metric_{safe_metric}_{node_id}_{timestamp}.json"
        
        md_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json_output, encoding="utf-8")
        
        result["artifact_paths"] = {
            "markdown": str(md_path),
            "json": str(json_path),
        }
        
        _log_digest_generation(node_id, metric, len(state_changes), len(state_confirmations))
    
    return result


def _calculate_confidence(observation_count: int, window_hours: float) -> str:
    """Calculate confidence level based on observation density."""
    if observation_count == 0:
        return "none"
    
    density = observation_count / max(window_hours, 1)
    
    if density >= 4:  # 4+ observations per hour
        return "high"
    elif density >= 1:  # 1-4 per hour
        return "medium"
    else:
        return "low"


def _log_digest_generation(
    node_id: str,
    metric: Optional[str],
    change_count: int,
    confirmation_count: int,
) -> None:
    """Log digest generation as evidence event."""
    try:
        from ..core.evidence import add_event
        
        scope = f"metric:{metric}" if metric else "node"
        add_event(
            event_type="TRUTH_DIGEST_GENERATED",
            component="digest_generator",
            summary=f"Truth Digest generated for {node_id} ({scope}): {change_count} changes, {confirmation_count} confirmations",
            data={
                "node_id": node_id,
                "metric": metric,
                "scope": scope,
                "state_changes": change_count,
                "state_confirmations": confirmation_count,
            },
        )
    except Exception:
        pass
