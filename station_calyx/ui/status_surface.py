"""
Station Calyx Status Surface
============================

Generates human-friendly summaries of current system state,
exposing reflections, advisories, and temporal findings.

INVARIANTS:
- HUMAN_PRIMACY: Advisory-only, non-intrusive operation
- NO_HIDDEN_CHANNELS: Surfaced data maps directly to logged evidence
- EXECUTION_GATE: Does not initiate or execute actions

DESIGN PRINCIPLES:
- Non-intrusive, advisory-only operation
- Present facts without urgency
- Respect human attention
- Surface only what matters

Role: ui/status_surface
Scope: Human-readable status summary generation
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from ..core.evidence import load_recent_events, get_last_event_ts
from ..core.intent import load_current_intent

COMPONENT_ROLE = "status_surface"
COMPONENT_SCOPE = "human-readable status summary generation"


def get_system_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Determine overall system state from recent events.
    
    Status language reflects evidence + uncertainty:
    - Snapshot count and time window computed dynamically
    - Confidence reflects lowest confidence among surfaced trends
    - No anthropomorphic phrasing
    """
    # Check for recent issues
    recent_errors = [e for e in events[-50:] if "error" in e.get("tags", [])]
    recent_drifts = [e for e in events[-50:] if e.get("event_type") == "DRIFT_WARNING"]
    recent_trends = [e for e in events[-50:] if e.get("event_type") == "TREND_DETECTED"]
    
    # Extract snapshot metadata for dynamic description
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    snapshot_count = len(snapshots)
    
    # Calculate time window from snapshots
    time_window_hours = 0.0
    if len(snapshots) >= 2:
        try:
            from datetime import datetime, timezone
            first_ts = datetime.fromisoformat(snapshots[0].get("ts", "").replace("Z", "+00:00"))
            last_ts = datetime.fromisoformat(snapshots[-1].get("ts", "").replace("Z", "+00:00"))
            time_window_hours = (last_ts - first_ts).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    
    # Determine lowest confidence among trends/drifts
    all_findings = recent_trends + recent_drifts
    lowest_confidence = _get_lowest_confidence(all_findings)
    
    # Build state description with evidence
    if recent_drifts:
        state = "notable_changes"
        state_desc = _format_evidence_description(
            "Drift warnings detected",
            snapshot_count,
            time_window_hours,
            lowest_confidence,
        )
    elif recent_trends:
        state = "trends_observed"
        state_desc = _format_evidence_description(
            "Trends detected",
            snapshot_count,
            time_window_hours,
            lowest_confidence,
        )
    elif recent_errors:
        state = "attention_suggested"
        state_desc = f"Events logged that may warrant attention ({len(recent_errors)} in recent window)"
    else:
        state = "stable"
        if snapshot_count > 0:
            state_desc = f"No significant changes detected from {snapshot_count} snapshot(s)"
        else:
            state_desc = "No snapshots available for analysis"
    
    return {
        "state": state,
        "description": state_desc,
        "error_count": len(recent_errors),
        "drift_count": len(recent_drifts),
        "trend_count": len(recent_trends),
        "snapshot_count": snapshot_count,
        "time_window_hours": round(time_window_hours, 1),
        "lowest_confidence": lowest_confidence,
    }


def _get_lowest_confidence(findings: list[dict[str, Any]]) -> str:
    """
    Get the lowest confidence level from a list of findings.
    Confidence order: HIGH > MEDIUM > LOW
    """
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    lowest = "high"
    lowest_rank = 3
    
    for finding in findings:
        payload = finding.get("payload", {})
        conf = payload.get("confidence", "low").lower()
        rank = confidence_order.get(conf, 1)
        if rank < lowest_rank:
            lowest = conf
            lowest_rank = rank
    
    return lowest if findings else "unknown"


def _format_evidence_description(
    prefix: str,
    snapshot_count: int,
    time_window_hours: float,
    confidence: str,
) -> str:
    """Format status description with evidence details."""
    if snapshot_count == 0:
        return f"{prefix} (no snapshot data available)"
    
    time_str = f"{time_window_hours:.1f} hours" if time_window_hours >= 1 else f"{time_window_hours * 60:.0f} minutes"
    
    return f"{prefix} from {snapshot_count} snapshot(s) over {time_str} (confidence: {confidence.upper()})"


def get_recent_advisories(events: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    """Extract recent advisory summaries."""
    advisories = [e for e in events if e.get("event_type") == "ADVISORY_GENERATED"]
    
    summaries = []
    for adv in advisories[-limit:]:
        payload = adv.get("payload", {})
        summaries.append({
            "timestamp": adv.get("ts", "")[:19],
            "session_id": payload.get("session_id", "unknown"),
            "profile": payload.get("intent_profile", "unknown"),
            "notes_count": payload.get("notes_count", 0),
        })
    
    return summaries


def get_active_findings(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Extract active trends and drift warnings with de-duplication.
    
    De-duplication key: (metric_name, direction)
    For each group, retain:
    - Most recent timestamp
    - Count of occurrences in window
    - Highest confidence observed
    """
    # Collect raw findings
    raw_trends: dict[tuple[str, str], list[dict[str, Any]]] = {}
    raw_drifts: dict[tuple[str, str], list[dict[str, Any]]] = {}
    patterns = []
    
    for e in events[-100:]:
        if e.get("event_type") == "TREND_DETECTED":
            payload = e.get("payload", {})
            key = (payload.get("metric_name", "unknown"), payload.get("direction", "unknown"))
            if key not in raw_trends:
                raw_trends[key] = []
            raw_trends[key].append({
                "metric": key[0],
                "direction": key[1],
                "confidence": payload.get("confidence", "unknown"),
                "timestamp": e.get("ts", "")[:19],
                "values_summary": payload.get("values_summary", {}),
                "evidence_refs": payload.get("evidence_refs", []),
            })
        elif e.get("event_type") == "DRIFT_WARNING":
            payload = e.get("payload", {})
            key = (payload.get("metric_name", "unknown"), payload.get("direction", "unknown"))
            if key not in raw_drifts:
                raw_drifts[key] = []
            raw_drifts[key].append({
                "metric": key[0],
                "direction": key[1],
                "confidence": payload.get("confidence", "unknown"),
                "timestamp": e.get("ts", "")[:19],
                "values_summary": payload.get("values_summary", {}),
                "evidence_refs": payload.get("evidence_refs", []),
            })
        elif e.get("event_type") == "PATTERN_RECURRING":
            patterns.append({
                "summary": e.get("summary", "")[:60],
                "timestamp": e.get("ts", "")[:19],
            })
    
    # De-duplicate trends
    trends = _deduplicate_findings(raw_trends)
    drifts = _deduplicate_findings(raw_drifts)
    
    return {
        "trends": trends[-5:],
        "drifts": drifts[-5:],
        "patterns": patterns[-3:],
    }


def _deduplicate_findings(
    grouped: dict[tuple[str, str], list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """
    De-duplicate findings by (metric, direction) key.
    
    For each group:
    - Most recent timestamp
    - Count of occurrences
    - Highest confidence observed
    """
    confidence_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    deduplicated = []
    
    for (metric, direction), occurrences in grouped.items():
        if not occurrences:
            continue
        
        # Sort by timestamp to get most recent
        sorted_occs = sorted(occurrences, key=lambda x: x.get("timestamp", ""), reverse=True)
        most_recent = sorted_occs[0]
        
        # Find highest confidence
        highest_conf = "unknown"
        highest_rank = 0
        for occ in occurrences:
            conf = occ.get("confidence", "unknown").lower()
            rank = confidence_order.get(conf, 0)
            if rank > highest_rank:
                highest_conf = conf
                highest_rank = rank
        
        deduplicated.append({
            "metric": metric,
            "direction": direction,
            "confidence": highest_conf,
            "timestamp": most_recent.get("timestamp", ""),
            "occurrence_count": len(occurrences),
            "values_summary": most_recent.get("values_summary", {}),
            "evidence_refs": most_recent.get("evidence_refs", []),
        })
    
    # Sort by timestamp (most recent first)
    return sorted(deduplicated, key=lambda x: x.get("timestamp", ""), reverse=True)


def get_latest_snapshot_summary(events: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Get summary of most recent snapshot."""
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    
    if not snapshots:
        return None
    
    latest = snapshots[-1]
    payload = latest.get("payload", {})
    
    return {
        "timestamp": latest.get("ts", "")[:19],
        "hostname": payload.get("hostname", "unknown"),
        "cpu_percent": payload.get("cpu_percent"),
        "memory_percent": payload.get("memory", {}).get("percent"),
        "disk_percent": payload.get("disk", {}).get("percent_used"),
    }


def generate_status_surface(
    events: Optional[list[dict[str, Any]]] = None,
    recent: int = 500,
) -> dict[str, Any]:
    """Generate comprehensive status surface."""
    if events is None:
        events = load_recent_events(recent)
    
    now = datetime.now(timezone.utc)
    intent = load_current_intent()
    
    status = {
        "generated_at": now.isoformat(),
        "system_state": get_system_state(events),
        "intent": {
            "profile": intent.advisory_profile.value if intent else "not_set",
            "description": intent.description if intent else "No intent configured",
        } if intent else None,
        "latest_snapshot": get_latest_snapshot_summary(events),
        "recent_advisories": get_recent_advisories(events),
        "active_findings": get_active_findings(events),
        "events_analyzed": len(events),
        "last_event_ts": get_last_event_ts(),
        "surface_role": COMPONENT_ROLE,
        "advisory_only": True,
    }
    
    return status


def format_status_markdown(status: dict[str, Any]) -> str:
    """Format status surface as human-readable markdown."""
    lines = [
        "# Station Calyx Status",
        "",
        f"*Generated: {status.get('generated_at', 'unknown')[:19]}*",
        "",
        "> This is an informational summary. No action is required.",
        "> Station Calyx is advisory-only and does not execute commands.",
        "",
        "---",
        "",
    ]
    
    # System State
    sys_state = status.get("system_state", {})
    state_emoji = {
        "stable": "??",
        "trends_observed": "??",
        "attention_suggested": "??",
        "notable_changes": "??",
    }.get(sys_state.get("state", ""), "?")
    
    lines.extend([
        "## System State",
        "",
        f"{state_emoji} **{sys_state.get('description', 'Unknown')}**",
        "",
    ])
    
    # Latest Snapshot
    snapshot = status.get("latest_snapshot")
    if snapshot:
        lines.extend([
            "## Latest Snapshot",
            "",
            f"- **Host:** {snapshot.get('hostname', '?')}",
            f"- **Time:** {snapshot.get('timestamp', '?')}",
            f"- **CPU:** {snapshot.get('cpu_percent', '?')}%",
            f"- **Memory:** {snapshot.get('memory_percent', '?')}%",
            f"- **Disk:** {snapshot.get('disk_percent', '?')}%",
            "",
        ])
    
    # Intent
    intent = status.get("intent")
    if intent:
        lines.extend([
            "## Active Intent",
            "",
            f"- **Profile:** {intent.get('profile', 'not set')}",
            f"- **Description:** {intent.get('description', 'None')}",
            "",
        ])
    
    # Active Findings
    findings = status.get("active_findings", {})
    
    drifts = findings.get("drifts", [])
    if drifts:
        lines.extend([
            "## Drift Warnings",
            "",
        ])
        for d in drifts:
            lines.append(f"- **{d.get('metric', '?')}**: {d.get('direction', '?')} ({d.get('confidence', '?')} confidence)")
        lines.append("")
    
    trends = findings.get("trends", [])
    if trends:
        lines.extend([
            "## Observed Trends",
            "",
        ])
        for t in trends:
            lines.append(f"- **{t.get('metric', '?')}**: {t.get('direction', '?')} ({t.get('confidence', '?')} confidence)")
        lines.append("")
    
    patterns = findings.get("patterns", [])
    if patterns:
        lines.extend([
            "## Recurring Patterns",
            "",
        ])
        for p in patterns:
            lines.append(f"- {p.get('summary', '?')}")
        lines.append("")
    
    # Recent Advisories
    advisories = status.get("recent_advisories", [])
    if advisories:
        lines.extend([
            "## Recent Advisories",
            "",
        ])
        for a in advisories:
            lines.append(f"- [{a.get('timestamp', '?')}] {a.get('profile', '?')} profile, {a.get('notes_count', 0)} note(s)")
        lines.append("")
    
    # Footer
    lines.extend([
        "---",
        "",
        "*Station Calyx: Advisory-only. Does not execute. Does not initiate actions.*",
    ])
    
    return "\n".join(lines)


def save_status_surface(status: Optional[dict[str, Any]] = None) -> Path:
    """Save current status surface to file."""
    config = get_config()
    
    if status is None:
        status = generate_status_surface()
    
    md_content = format_status_markdown(status)
    
    output_path = config.summaries_dir / "status_current.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    # Also save JSON version
    json_path = config.summaries_dir / "status_current.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    
    return output_path


def load_status_surface() -> Optional[str]:
    """Load current status surface markdown."""
    config = get_config()
    path = config.summaries_dir / "status_current.md"
    
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    
    status = generate_status_surface()
    print(format_status_markdown(status))
