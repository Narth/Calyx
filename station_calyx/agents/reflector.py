"""
Station Calyx Reflector Agent
=============================

Rule-based reflection over system events.
Produces advisory insights without taking actions.

INVARIANT: HUMAN_PRIMACY
- Output is advisory only
- No execution capability
- Does not initiate or command actions

Role: agents/reflector
Scope: Event analysis, pattern detection, advisory generation
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..core.evidence import (
    append_event,
    create_event,
    compute_sha256,
    generate_session_id,
)
from ..core.config import get_config

# Role declaration
COMPONENT_ROLE = "reflector_agent"
COMPONENT_SCOPE = "rule-based event analysis and advisory generation"


def analyze_event_types(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count event types in the event list."""
    return dict(Counter(e.get("event_type", "UNKNOWN") for e in events))


def analyze_node_roles(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count events by node role."""
    return dict(Counter(e.get("node_role", "unknown") for e in events))


def analyze_tags(events: list[dict[str, Any]]) -> dict[str, int]:
    """Count tag occurrences."""
    tags = []
    for e in events:
        tags.extend(e.get("tags", []))
    return dict(Counter(tags))


def detect_anomalies(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detect anomalous patterns in events (rule-based).
    
    Rules:
    - Multiple errors in short succession
    - Unusual event frequencies
    - Policy violations
    """
    anomalies = []
    
    # Check for error events
    error_events = [e for e in events if "error" in e.get("tags", []) or e.get("event_type", "").startswith("ERROR")]
    if len(error_events) > 3:
        anomalies.append({
            "type": "HIGH_ERROR_RATE",
            "severity": "warning",
            "description": f"Found {len(error_events)} error events in recent history",
            "count": len(error_events),
        })
    
    # Check for policy denials
    policy_denials = [e for e in events if e.get("event_type") == "POLICY_DECISION" and "denied" in e.get("tags", [])]
    if policy_denials:
        anomalies.append({
            "type": "POLICY_DENIALS",
            "severity": "info",
            "description": f"{len(policy_denials)} execution requests denied (expected in v1 deny-all mode)",
            "count": len(policy_denials),
        })
    
    # Check for gaps in timestamps (if we have enough events)
    if len(events) >= 10:
        timestamps = []
        for e in events:
            try:
                ts = datetime.fromisoformat(e.get("ts", "").replace("Z", "+00:00"))
                timestamps.append(ts)
            except (ValueError, TypeError):
                continue
        
        if len(timestamps) >= 2:
            timestamps.sort()
            gaps = []
            for i in range(1, len(timestamps)):
                gap = (timestamps[i] - timestamps[i-1]).total_seconds()
                if gap > 3600:  # Gap > 1 hour
                    gaps.append(gap)
            
            if gaps:
                anomalies.append({
                    "type": "EVENT_GAPS",
                    "severity": "info",
                    "description": f"Found {len(gaps)} gaps >1 hour in event timeline",
                    "max_gap_hours": round(max(gaps) / 3600, 1),
                })
    
    return anomalies


def detect_changes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detect significant changes in system state.
    
    Looks for:
    - Snapshot differences
    - Configuration changes
    - Status transitions
    """
    changes = []
    
    # Find snapshot events
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    
    if len(snapshots) >= 2:
        latest = snapshots[-1].get("payload", {})
        previous = snapshots[-2].get("payload", {})
        
        # Compare CPU
        cpu_latest = latest.get("cpu_percent")
        cpu_previous = previous.get("cpu_percent")
        if cpu_latest is not None and cpu_previous is not None:
            cpu_diff = cpu_latest - cpu_previous
            if abs(cpu_diff) > 20:
                changes.append({
                    "type": "CPU_CHANGE",
                    "description": f"CPU usage changed from {cpu_previous}% to {cpu_latest}%",
                    "delta": round(cpu_diff, 1),
                })
        
        # Compare memory
        mem_latest = latest.get("memory", {}).get("percent")
        mem_previous = previous.get("memory", {}).get("percent")
        if mem_latest is not None and mem_previous is not None:
            mem_diff = mem_latest - mem_previous
            if abs(mem_diff) > 10:
                changes.append({
                    "type": "MEMORY_CHANGE",
                    "description": f"Memory usage changed from {mem_previous}% to {mem_latest}%",
                    "delta": round(mem_diff, 1),
                })
    
    return changes


def generate_highlights(events: list[dict[str, Any]]) -> list[str]:
    """Generate highlight observations from events."""
    highlights = []
    
    if not events:
        highlights.append("No events found in the analysis window.")
        return highlights
    
    # Event count
    highlights.append(f"Analyzed {len(events)} events in this session.")
    
    # Event type distribution
    type_counts = analyze_event_types(events)
    top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    if top_types:
        highlights.append(f"Most common event types: {', '.join(f'{t[0]} ({t[1]})' for t in top_types)}")
    
    # Node role activity
    role_counts = analyze_node_roles(events)
    active_roles = [r for r, c in role_counts.items() if c > 0]
    if active_roles:
        highlights.append(f"Active components: {', '.join(active_roles[:5])}")
    
    # Time span
    timestamps = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e.get("ts", "").replace("Z", "+00:00"))
            timestamps.append(ts)
        except (ValueError, TypeError):
            continue
    
    if len(timestamps) >= 2:
        timestamps.sort()
        span = timestamps[-1] - timestamps[0]
        hours = span.total_seconds() / 3600
        highlights.append(f"Events span {round(hours, 1)} hours.")
    
    return highlights


def generate_questions(events: list[dict[str, Any]], anomalies: list[dict[str, Any]]) -> list[str]:
    """Generate questions for human consideration."""
    questions = []
    
    # Based on anomalies
    for anomaly in anomalies:
        if anomaly["type"] == "HIGH_ERROR_RATE":
            questions.append("What is causing the elevated error rate? Should error sources be investigated?")
        elif anomaly["type"] == "EVENT_GAPS":
            questions.append(f"Why were there gaps up to {anomaly.get('max_gap_hours', '?')} hours? Was the system offline?")
    
    # General questions
    if not events:
        questions.append("No events recorded. Is the system configured correctly?")
    elif len(events) < 10:
        questions.append("Low event count. Should more connectors be enabled?")
    
    return questions


def generate_suggestions(
    events: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    changes: list[dict[str, Any]],
) -> list[str]:
    """
    Generate suggested next steps (advisory only).
    
    INVARIANT: These are suggestions, not commands.
    """
    suggestions = []
    
    # Based on anomalies
    for anomaly in anomalies:
        if anomaly["type"] == "HIGH_ERROR_RATE":
            suggestions.append("ADVISORY: Review error logs to identify root cause of failures.")
    
    # Based on changes
    for change in changes:
        if change["type"] == "CPU_CHANGE" and change.get("delta", 0) > 30:
            suggestions.append("ADVISORY: High CPU spike detected. Consider reviewing active processes.")
        elif change["type"] == "MEMORY_CHANGE" and change.get("delta", 0) > 20:
            suggestions.append("ADVISORY: Significant memory increase. Monitor for potential leaks.")
    
    # General suggestions
    if not events:
        suggestions.append("ADVISORY: Run `calyx snapshot` to begin collecting system telemetry.")
    
    if not suggestions:
        suggestions.append("ADVISORY: System appears stable. Continue monitoring.")
    
    return suggestions


def reflect(events: list[dict[str, Any]], session_id: Optional[str] = None) -> dict[str, Any]:
    """
    Perform reflection over events.
    
    Returns a reflection artifact with:
    - highlights: Key observations
    - anomalies: Detected anomalies
    - changes: Detected changes
    - questions: Questions for human consideration
    - suggested_next_steps: Advisory suggestions (not commands)
    """
    session_id = session_id or generate_session_id()
    now = datetime.now(timezone.utc)
    
    # Analysis
    anomalies = detect_anomalies(events)
    changes = detect_changes(events)
    highlights = generate_highlights(events)
    questions = generate_questions(events, anomalies)
    suggestions = generate_suggestions(events, anomalies, changes)
    
    reflection = {
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "events_analyzed": len(events),
        "highlights": highlights,
        "anomalies": anomalies,
        "changes": changes,
        "questions": questions,
        "suggested_next_steps": suggestions,
        "reflector_role": COMPONENT_ROLE,
        "advisory_only": True,  # INVARIANT: Human primacy
    }
    
    return reflection


def save_reflection(
    reflection: dict[str, Any],
    summaries_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """
    Save reflection to both markdown and JSON formats.
    
    Returns (md_path, json_path).
    """
    config = get_config()
    output_dir = summaries_dir or config.summaries_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = reflection.get("session_id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    base_name = f"reflection_{session_id}_{timestamp}"
    md_path = output_dir / f"{base_name}.md"
    json_path = output_dir / f"{base_name}.json"
    
    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(reflection, f, indent=2, ensure_ascii=False)
    
    # Save Markdown
    md_content = format_reflection_markdown(reflection)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return md_path, json_path


def format_reflection_markdown(reflection: dict[str, Any]) -> str:
    """Format reflection as markdown document."""
    lines = [
        f"# Station Calyx Reflection",
        f"",
        f"**Session ID:** {reflection.get('session_id', 'unknown')}",
        f"**Timestamp:** {reflection.get('timestamp', 'unknown')}",
        f"**Events Analyzed:** {reflection.get('events_analyzed', 0)}",
        f"**Advisory Only:** {reflection.get('advisory_only', True)}",
        f"",
        f"---",
        f"",
        f"## Highlights",
        f"",
    ]
    
    for h in reflection.get("highlights", []):
        lines.append(f"- {h}")
    
    lines.extend([
        f"",
        f"## Anomalies Detected",
        f"",
    ])
    
    anomalies = reflection.get("anomalies", [])
    if anomalies:
        for a in anomalies:
            lines.append(f"- **[{a.get('severity', 'info').upper()}]** {a.get('type', 'UNKNOWN')}: {a.get('description', '')}")
    else:
        lines.append("- No anomalies detected.")
    
    lines.extend([
        f"",
        f"## Changes Detected",
        f"",
    ])
    
    changes = reflection.get("changes", [])
    if changes:
        for c in changes:
            lines.append(f"- {c.get('type', 'UNKNOWN')}: {c.get('description', '')}")
    else:
        lines.append("- No significant changes detected.")
    
    lines.extend([
        f"",
        f"## Questions for Consideration",
        f"",
    ])
    
    for q in reflection.get("questions", []):
        lines.append(f"- {q}")
    
    lines.extend([
        f"",
        f"## Suggested Next Steps (Advisory)",
        f"",
        f"> **Note:** These are suggestions only. No automated action will be taken.",
        f"",
    ])
    
    for s in reflection.get("suggested_next_steps", []):
        lines.append(f"- {s}")
    
    lines.extend([
        f"",
        f"---",
        f"",
        f"*Generated by Station Calyx Reflector Agent (v1 - Advisory Only)*",
    ])
    
    return "\n".join(lines)


def log_reflection_event(reflection: dict[str, Any], md_path: Path, json_path: Path) -> None:
    """Log reflection generation to evidence log."""
    # Compute hashes for integrity
    md_hash = compute_sha256(md_path.read_bytes())
    json_hash = compute_sha256(json_path.read_bytes())
    
    event = create_event(
        event_type="REFLECTION_GENERATED",
        node_role=COMPONENT_ROLE,
        summary=f"Reflection generated for session {reflection.get('session_id', 'unknown')} analyzing {reflection.get('events_analyzed', 0)} events",
        payload={
            "session_id": reflection.get("session_id"),
            "events_analyzed": reflection.get("events_analyzed"),
            "anomaly_count": len(reflection.get("anomalies", [])),
            "change_count": len(reflection.get("changes", [])),
            "md_path": str(md_path),
            "json_path": str(json_path),
            "md_hash": md_hash,
            "json_hash": json_hash,
        },
        tags=["reflection", "summary"],
        session_id=reflection.get("session_id"),
    )
    
    append_event(event)


# Self-test
if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    
    # Test with sample events
    sample_events = [
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": "TEST",
            "node_role": "test",
            "session_id": "test123",
            "summary": "Test event",
            "payload": {},
            "tags": ["test"],
        }
    ]
    
    reflection = reflect(sample_events)
    print(f"\nReflection generated:")
    print(f"- Highlights: {len(reflection['highlights'])}")
    print(f"- Anomalies: {len(reflection['anomalies'])}")
    print(f"- Suggestions: {len(reflection['suggested_next_steps'])}")
