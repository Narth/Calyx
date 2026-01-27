# -*- coding: utf-8 -*-
"""Truth Digest Formatter - formats digests as Markdown and JSON."""

from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from .classifier import StateChange, StateConfirmation


def format_digest_markdown(
    node_id: str,
    period_start: str,
    period_end: str,
    state_changes: list,
    state_confirmations: list,
    open_observations: list,
    evidence_basis: dict,
    metric_scope: str = None,
) -> str:
    """Format a Truth Digest as Markdown."""
    scope_label = f"Metric: {metric_scope}" if metric_scope else "Node"
    lines = [
        f"# TRUTH DIGEST - {scope_label} - {node_id}",
        "",
        f"**Period:** {period_start} to {period_end}",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        f"## STATE CHANGES ({len(state_changes)})",
        "",
    ]
    
    if state_changes:
        for sc in state_changes:
            prior = str(sc.prior_state) if sc.prior_state is not None else "(none)"
            lines.append(f"- **{sc.metric}**: {prior} -> {sc.current_state} ({sc.evidence_count} obs, {sc.reason.value})")
    else:
        lines.append("*No state changes detected in this period.*")
    
    lines.append("")
    total_obs = sum(sc.observation_count for sc in state_confirmations)
    lines.append(f"## STATE CONFIRMATIONS ({total_obs} observations, {len(state_confirmations)} metrics)")
    lines.append("")
    
    if state_confirmations:
        for sc in state_confirmations:
            lines.append(f"- **{sc.metric}**: {sc.state} ({sc.observation_count} obs)")
    else:
        lines.append("*No confirmations.*")
    
    lines.extend([
        "",
        f"## OPEN OBSERVATIONS ({len(open_observations)})",
        "",
        "*None.*" if not open_observations else str(open_observations),
        "",
        "## EVIDENCE BASIS",
        "",
        f"- **Window:** {evidence_basis.get('window_hours', '?')} hours",
        f"- **Snapshots:** {evidence_basis.get('snapshot_count', 0)}",
        f"- **Confidence:** {evidence_basis.get('confidence', '?')}",
        "",
        "---",
        "",
        "*This digest describes observed state. It does not recommend actions.*",
    ])
    
    return "\n".join(lines)


def format_digest_json(
    node_id: str,
    period_start: str,
    period_end: str,
    state_changes: list,
    state_confirmations: list,
    open_observations: list,
    evidence_basis: dict,
    metric_scope: str = None,
) -> str:
    """Format a Truth Digest as JSON."""
    digest = {
        "digest_version": "v1",
        "node_id": node_id,
        "metric_scope": metric_scope,
        "period": {"start": period_start, "end": period_end},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "state_changes": [sc.to_dict() for sc in state_changes],
        "state_confirmations": [sc.to_dict() for sc in state_confirmations],
        "open_observations": open_observations,
        "evidence_basis": evidence_basis,
        "constraints": {
            "advisory_only": True,
            "no_recommendations": True,
            "no_suppression": True,
            "deterministic": True,
        },
    }
    return json.dumps(digest, indent=2, sort_keys=True)


def format_threshold_report(thresholds: dict) -> str:
    """Format current thresholds as a report."""
    lines = [
        "# Current Learned Thresholds",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    
    for metric, thresh in sorted(thresholds.items()):
        if isinstance(thresh, dict):
            low = thresh.get("low", "-")
            high = thresh.get("high", "-")
            source = thresh.get("source", "unknown")
        else:
            low = getattr(thresh, "low", "-")
            high = getattr(thresh, "high", "-")
            source = getattr(thresh, "source", "unknown")
        
        lines.append(f"- **{metric}**: low={low}, high={high} ({source})")
    
    if len(lines) == 4:
        lines.append("*No thresholds learned yet.*")
    
    return "\n".join(lines)