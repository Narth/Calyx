"""
Station Calyx Advisory Agent
============================

Produces context-aware advisory output based on:
- Recent events
- Reflection outputs
- User intent and advisory profile

INVARIANTS:
- HUMAN_PRIMACY: All output is advisory only
- NO_HIDDEN_CHANNELS: All reasoning is logged
- EXECUTION_GATE: Never proposes commands or execution

GUARDRAILS:
- Never propose commands
- Never suggest execution
- Never claim certainty without evidence
- Every statement must reference reflection outputs or snapshot data

Role: agents/advisor
Scope: Context-aware advisory generation with evidence-based reasoning
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..core.config import get_config
from ..core.evidence import append_event, create_event, compute_sha256, generate_session_id
from ..core.intent import UserIntent, AdvisoryProfile, load_current_intent, get_or_create_default_intent

COMPONENT_ROLE = "advisor_agent"
COMPONENT_SCOPE = "context-aware advisory generation with evidence-based reasoning"

# Guardrail constants
FORBIDDEN_PHRASES = [
    "run this command",
    "execute",
    "you should run",
    "restart the",
    "kill the process",
    "sudo",
    "rm -rf",
    "delete",
    "modify the file",
    "change the setting",
]


class ConfidenceLevel(Enum):
    """Confidence level for advisory notes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    
    @classmethod
    def from_evidence_count(cls, count: int) -> "ConfidenceLevel":
        """Determine confidence based on evidence count."""
        if count >= 5:
            return cls.HIGH
        elif count >= 2:
            return cls.MEDIUM
        return cls.LOW


@dataclass
class AdvisoryNote:
    """
    A single advisory note with evidence-based reasoning.
    
    GUARDRAIL: Every note must include rationale with evidence references.
    """
    message: str
    confidence_level: ConfidenceLevel
    rationale: str
    uncertainties: list[str]
    evidence_refs: list[str]
    profile_context: str
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "confidence_level": self.confidence_level.value,
            "rationale": self.rationale,
            "uncertainties": self.uncertainties,
            "evidence_refs": self.evidence_refs,
            "profile_context": self.profile_context,
        }
    
    def validate_guardrails(self) -> list[str]:
        """Check for guardrail violations."""
        violations = []
        message_lower = self.message.lower()
        
        for phrase in FORBIDDEN_PHRASES:
            if phrase in message_lower:
                violations.append(f"Forbidden phrase detected: '{phrase}'")
        
        if not self.evidence_refs:
            violations.append("No evidence references provided")
        
        if not self.rationale:
            violations.append("No rationale provided")
        
        return violations


def analyze_for_stability(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: UserIntent,
) -> list[AdvisoryNote]:
    """Generate stability-focused advisory notes."""
    notes = []
    framing = intent.get_framing()
    
    # Check for errors in events
    error_events = [e for e in events if "error" in e.get("tags", []) or e.get("event_type", "").startswith("ERROR")]
    if error_events:
        notes.append(AdvisoryNote(
            message=f"ADVISORY: {len(error_events)} error event(s) detected in recent history. Review error logs to understand root causes before making system changes.",
            confidence_level=ConfidenceLevel.from_evidence_count(len(error_events)),
            rationale=f"Error events indicate potential stability issues. Profile '{intent.advisory_profile.value}' prioritizes {framing.get('priority', 'stability')}.",
            uncertainties=["Error severity not fully assessed", "Root cause requires investigation"],
            evidence_refs=[f"event:{e.get('event_type')}@{e.get('ts', 'unknown')[:19]}" for e in error_events[:3]],
            profile_context=f"Stability-first profile suggests conservative approach to error resolution.",
        ))
    
    # Check anomalies from reflection
    anomalies = reflection.get("anomalies", [])
    if anomalies:
        for anomaly in anomalies[:2]:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Anomaly detected - {anomaly.get('type', 'UNKNOWN')}. {anomaly.get('description', 'No description')}",
                confidence_level=ConfidenceLevel.MEDIUM if anomaly.get("severity") == "warning" else ConfidenceLevel.LOW,
                rationale=f"Anomaly flagged by reflector analysis. Severity: {anomaly.get('severity', 'unknown')}.",
                uncertainties=["Anomaly may be transient", "Additional monitoring recommended"],
                evidence_refs=[f"reflection:anomaly:{anomaly.get('type')}"],
                profile_context=f"Profile emphasizes: {', '.join(framing.get('emphasis', []))}",
            ))
    
    # Check for resource concerns in snapshots
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    if snapshots:
        latest = snapshots[-1].get("payload", {})
        disk = latest.get("disk", {})
        if disk.get("percent_used", 0) > 85:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Disk usage at {disk.get('percent_used')}%. Consider reviewing disk space to maintain system stability.",
                confidence_level=ConfidenceLevel.HIGH,
                rationale=f"High disk usage can impact system stability and performance. Current: {disk.get('used_gb', '?')}GB / {disk.get('total_gb', '?')}GB.",
                uncertainties=["Growth rate unknown", "Critical threshold depends on workload"],
                evidence_refs=[f"snapshot:disk:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Stability-first profile prioritizes preventing resource exhaustion.",
            ))
        
        mem = latest.get("memory", {})
        if mem.get("percent", 0) > 80:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Memory usage at {mem.get('percent')}%. Monitor for potential memory pressure.",
                confidence_level=ConfidenceLevel.MEDIUM,
                rationale=f"Elevated memory usage may impact system responsiveness. Available: {mem.get('available_gb', '?')}GB.",
                uncertainties=["Usage may be temporary", "Application behavior varies"],
                evidence_refs=[f"snapshot:memory:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Stability profile recommends proactive monitoring of resources.",
            ))
    
    return notes


def analyze_for_performance(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: UserIntent,
) -> list[AdvisoryNote]:
    """Generate performance-focused advisory notes."""
    notes = []
    framing = intent.get_framing()
    
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    if snapshots:
        latest = snapshots[-1].get("payload", {})
        
        cpu = latest.get("cpu_percent", 0)
        if cpu > 70:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: CPU usage at {cpu}%. This may impact application responsiveness.",
                confidence_level=ConfidenceLevel.MEDIUM,
                rationale=f"High CPU usage can affect latency-sensitive operations. Profile prioritizes {framing.get('priority', 'performance')}.",
                uncertainties=["CPU spike may be temporary", "Workload context unknown"],
                evidence_refs=[f"snapshot:cpu:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Performance-sensitive profile emphasizes responsiveness.",
            ))
        
        top_procs = latest.get("top_processes", [])
        if top_procs:
            high_cpu = [p for p in top_procs if p.get("cpu_percent", 0) > 30]
            if high_cpu:
                proc_names = ", ".join(p.get("name", "unknown") for p in high_cpu[:3])
                notes.append(AdvisoryNote(
                    message=f"ADVISORY: High CPU processes detected: {proc_names}. Consider whether these are expected workloads.",
                    confidence_level=ConfidenceLevel.LOW,
                    rationale="Identifying CPU-intensive processes helps understand system load distribution.",
                    uncertainties=["Process importance unknown", "May be legitimate workload"],
                    evidence_refs=[f"snapshot:process:{p.get('name')}" for p in high_cpu[:3]],
                    profile_context="Performance profile tracks resource-intensive processes.",
                ))
    
    # Check for changes from reflection
    changes = reflection.get("changes", [])
    for change in changes[:2]:
        if "CPU" in change.get("type", "") or "MEMORY" in change.get("type", ""):
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Resource change detected - {change.get('description', 'Unknown change')}.",
                confidence_level=ConfidenceLevel.MEDIUM,
                rationale="Significant resource changes may indicate workload shifts or performance issues.",
                uncertainties=["Change may be expected", "Trend direction unclear"],
                evidence_refs=[f"reflection:change:{change.get('type')}"],
                profile_context=f"Performance profile monitors: {', '.join(framing.get('emphasis', []))}",
            ))
    
    return notes


def analyze_for_resources(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: UserIntent,
) -> list[AdvisoryNote]:
    """Generate resource-focused advisory notes."""
    notes = []
    framing = intent.get_framing()
    
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    if snapshots:
        latest = snapshots[-1].get("payload", {})
        
        disk = latest.get("disk", {})
        free_gb = disk.get("free_gb", 0)
        if free_gb < 50:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Only {free_gb}GB disk space remaining. Resource-constrained environments benefit from proactive space management.",
                confidence_level=ConfidenceLevel.HIGH if free_gb < 20 else ConfidenceLevel.MEDIUM,
                rationale=f"Limited disk space can impact system operations. Profile prioritizes {framing.get('priority', 'resource conservation')}.",
                uncertainties=["Space requirements vary by workload", "Growth rate unknown"],
                evidence_refs=[f"snapshot:disk:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Resource-constrained profile emphasizes efficient resource usage.",
            ))
        
        mem = latest.get("memory", {})
        if mem.get("percent", 0) > 60:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Memory at {mem.get('percent')}% utilization ({mem.get('used_gb', '?')}GB used). Monitor for efficient resource allocation.",
                confidence_level=ConfidenceLevel.LOW,
                rationale="Resource-constrained environments benefit from memory awareness.",
                uncertainties=["Usage pattern unknown", "Some memory usage is healthy"],
                evidence_refs=[f"snapshot:memory:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Profile emphasizes memory efficiency.",
            ))
    
    return notes


def analyze_for_developer(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: UserIntent,
) -> list[AdvisoryNote]:
    """Generate developer-workstation-focused advisory notes."""
    notes = []
    framing = intent.get_framing()
    
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    if snapshots:
        latest = snapshots[-1].get("payload", {})
        
        top_procs = latest.get("top_processes", [])
        dev_tools = ["devenv", "code", "rider", "idea", "node", "python", "dotnet", "java", "gradle", "maven"]
        active_tools = [p for p in top_procs if any(tool in p.get("name", "").lower() for tool in dev_tools)]
        
        if active_tools:
            tool_names = ", ".join(set(p.get("name", "unknown") for p in active_tools[:5]))
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Development tools detected: {tool_names}. System resources appear allocated to development workload.",
                confidence_level=ConfidenceLevel.HIGH,
                rationale="Identifying active development tools helps contextualize resource usage.",
                uncertainties=["Tool activity level unknown", "Build status unclear"],
                evidence_refs=[f"snapshot:process:{p.get('name')}" for p in active_tools[:3]],
                profile_context="Developer workstation profile tracks IDE and build tool activity.",
            ))
        
        mem = latest.get("memory", {})
        if mem.get("percent", 0) > 75:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Memory at {mem.get('percent')}%. Development tools often benefit from available memory headroom.",
                confidence_level=ConfidenceLevel.MEDIUM,
                rationale="IDEs and build tools perform better with memory headroom for caching and compilation.",
                uncertainties=["Optimal memory varies by project", "Usage may be temporary"],
                evidence_refs=[f"snapshot:memory:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Developer profile emphasizes tool performance.",
            ))
    
    # Check reflection questions
    questions = reflection.get("questions", [])
    if questions:
        notes.append(AdvisoryNote(
            message=f"ADVISORY: Reflector raised {len(questions)} question(s) for consideration. Review reflection output for details.",
            confidence_level=ConfidenceLevel.LOW,
            rationale="Questions from reflection indicate areas that may benefit from human attention.",
            uncertainties=["Question relevance varies", "Context-dependent"],
            evidence_refs=["reflection:questions"],
            profile_context="Developer profile values awareness of system state.",
        ))
    
    return notes


def analyze_for_storage_pressure(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: UserIntent,
) -> list[AdvisoryNote]:
    """
    Generate storage-pressure-focused advisory notes.
    
    Focus: Disk usage, storage trends, file system observations.
    """
    notes = []
    
    # Get latest snapshot for disk metrics
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    
    if snapshots:
        latest = snapshots[-1].get("payload", {})
        
        disk = latest.get("disk", {})
        disk_percent = disk.get("percent_used", 0)
        disk_free_gb = disk.get("free_gb", 0)
        
        # Storage-specific observations
        if disk_percent > 90:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Disk usage at {disk_percent}% ({disk_free_gb:.1f} GB free). Storage capacity is constrained.",
                confidence_level=ConfidenceLevel.HIGH,
                rationale="Disk usage above 90% can impact system performance and prevent new file creation.",
                uncertainties=["Usage distribution unknown", "Critical files vs. removable data unclear"],
                evidence_refs=[f"snapshot:disk:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Storage pressure profile prioritizes disk space awareness.",
            ))
        elif disk_percent > 80:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Disk usage at {disk_percent}% ({disk_free_gb:.1f} GB free). Approaching storage constraints.",
                confidence_level=ConfidenceLevel.MEDIUM,
                rationale="Disk usage above 80% warrants awareness of storage trends.",
                uncertainties=["Growth rate uncertain", "Cleanup potential unknown"],
                evidence_refs=[f"snapshot:disk:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Storage pressure profile tracks disk capacity.",
            ))
        else:
            notes.append(AdvisoryNote(
                message=f"ADVISORY: Disk usage at {disk_percent}% ({disk_free_gb:.1f} GB free). Storage capacity adequate.",
                confidence_level=ConfidenceLevel.HIGH,
                rationale="Disk usage below 80% indicates sufficient storage headroom.",
                uncertainties=["Future growth rate unknown"],
                evidence_refs=[f"snapshot:disk:{latest.get('timestamp', 'unknown')[:19]}"],
                profile_context="Storage pressure profile confirms capacity.",
            ))
    
    # Check for disk-related trends
    for e in events[-50:]:
        if e.get("event_type") == "TREND_DETECTED":
            payload = e.get("payload", {})
            if "disk" in payload.get("metric_name", "").lower():
                direction = payload.get("direction", "unknown")
                notes.append(AdvisoryNote(
                    message=f"ADVISORY: Disk usage trend detected: {direction}. Monitor storage capacity.",
                    confidence_level=ConfidenceLevel.MEDIUM,
                    rationale="Disk trends inform capacity planning.",
                    uncertainties=["Trend may not continue", "External factors may apply"],
                    evidence_refs=[f"trend:disk:{e.get('ts', '')[:19]}"],
                    profile_context="Storage pressure profile emphasizes disk trends.",
                ))
                break  # Only report first disk trend
    
    return notes


def generate_advisory(
    events: list[dict[str, Any]],
    reflection: dict[str, Any],
    intent: Optional[UserIntent] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate context-aware advisory output.
    
    GUARDRAILS ENFORCED:
    - No command proposals
    - No execution suggestions
    - All statements reference evidence
    """
    intent = intent or get_or_create_default_intent()
    session_id = session_id or generate_session_id()
    now = datetime.now(timezone.utc)
    
    # Select analysis based on profile
    profile_analyzers = {
        AdvisoryProfile.STABILITY_FIRST: analyze_for_stability,
        AdvisoryProfile.PERFORMANCE_SENSITIVE: analyze_for_performance,
        AdvisoryProfile.RESOURCE_CONSTRAINED: analyze_for_resources,
        AdvisoryProfile.STORAGE_PRESSURE: analyze_for_storage_pressure,
        AdvisoryProfile.DEVELOPER_WORKSTATION: analyze_for_developer,
    }
    
    analyzer = profile_analyzers.get(intent.advisory_profile, analyze_for_stability)
    notes = analyzer(events, reflection, intent)
    
    # Add baseline note if no specific advisories
    if not notes:
        notes.append(AdvisoryNote(
            message="ADVISORY: No specific concerns detected based on available evidence. System appears to be operating normally.",
            confidence_level=ConfidenceLevel.MEDIUM,
            rationale=f"Analysis of {len(events)} events and reflection output revealed no anomalies matching {intent.advisory_profile.value} profile concerns.",
            uncertainties=["Limited event history", "Some issues may not be captured"],
            evidence_refs=[f"events:count:{len(events)}", "reflection:summary"],
            profile_context=f"Profile: {intent.advisory_profile.value} - {intent.description[:50]}",
        ))
    
    # Validate guardrails
    guardrail_violations = []
    for note in notes:
        violations = note.validate_guardrails()
        guardrail_violations.extend(violations)
    
    advisory = {
        "session_id": session_id,
        "timestamp": now.isoformat(),
        "intent": intent.to_dict(),
        "events_analyzed": len(events),
        "reflection_session": reflection.get("session_id"),
        "advisory_notes": [n.to_dict() for n in notes],
        "guardrail_check": {
            "passed": len(guardrail_violations) == 0,
            "violations": guardrail_violations,
        },
        "advisor_role": COMPONENT_ROLE,
        "advisory_only": True,
        "execution_capability": False,
    }
    
    return advisory


def save_advisory(
    advisory: dict[str, Any],
    summaries_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Save advisory to markdown and JSON files."""
    config = get_config()
    output_dir = summaries_dir or config.summaries_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    session_id = advisory.get("session_id", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    base_name = f"advisory_{session_id}_{timestamp}"
    md_path = output_dir / f"{base_name}.md"
    json_path = output_dir / f"{base_name}.json"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(advisory, f, indent=2, ensure_ascii=False)
    
    md_content = format_advisory_markdown(advisory)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    return md_path, json_path


def format_advisory_markdown(advisory: dict[str, Any]) -> str:
    """Format advisory as markdown document."""
    intent = advisory.get("intent", {})
    notes = advisory.get("advisory_notes", [])
    
    lines = [
        "# Station Calyx Advisory Report",
        "",
        "> **NOTICE:** This is an advisory document only. No automated actions are taken.",
        "> All recommendations require human review and decision-making.",
        "",
        f"**Session ID:** {advisory.get('session_id', 'unknown')}",
        f"**Timestamp:** {advisory.get('timestamp', 'unknown')}",
        f"**Events Analyzed:** {advisory.get('events_analyzed', 0)}",
        f"**Reflection Session:** {advisory.get('reflection_session', 'N/A')}",
        "",
        "---",
        "",
        "## User Intent",
        "",
        f"**Profile:** {intent.get('advisory_profile', 'unknown')}",
        f"**Description:** {intent.get('description', 'No description')}",
        "",
        "---",
        "",
        "## Advisory Notes",
        "",
    ]
    
    if notes:
        for i, note in enumerate(notes, 1):
            confidence = note.get("confidence_level", "unknown").upper()
            lines.extend([
                f"### Note {i} [{confidence} confidence]",
                "",
                f"{note.get('message', 'No message')}",
                "",
                f"**Rationale:** {note.get('rationale', 'No rationale')}",
                "",
                "**Evidence References:**",
            ])
            for ref in note.get("evidence_refs", []):
                lines.append(f"- `{ref}`")
            
            lines.append("")
            lines.append("**Uncertainties:**")
            for unc in note.get("uncertainties", []):
                lines.append(f"- {unc}")
            
            lines.extend([
                "",
                f"*Profile Context:* {note.get('profile_context', 'N/A')}",
                "",
                "---",
                "",
            ])
    else:
        lines.append("No advisory notes generated.")
        lines.append("")
    
    # Guardrail status
    guardrail = advisory.get("guardrail_check", {})
    lines.extend([
        "## Guardrail Verification",
        "",
        f"**Status:** {'PASSED' if guardrail.get('passed', True) else 'VIOLATIONS DETECTED'}",
        "",
    ])
    
    if not guardrail.get("passed", True):
        lines.append("**Violations:**")
        for v in guardrail.get("violations", []):
            lines.append(f"- {v}")
        lines.append("")
    
    lines.extend([
        "---",
        "",
        "*Generated by Station Calyx Advisory Agent (v1 - Advisory Only)*",
        "",
        "**Invariants Enforced:**",
        "- HUMAN_PRIMACY: All output is advisory only",
        "- EXECUTION_GATE: No commands proposed or executed",
        "- NO_HIDDEN_CHANNELS: All reasoning logged to evidence",
    ])
    
    return "\n".join(lines)


def log_advisory_event(advisory: dict[str, Any], md_path: Path, json_path: Path) -> None:
    """Log advisory generation to evidence."""
    md_hash = compute_sha256(md_path.read_bytes())
    json_hash = compute_sha256(json_path.read_bytes())
    
    event = create_event(
        event_type="ADVISORY_GENERATED",
        node_role=COMPONENT_ROLE,
        summary=f"Advisory generated for session {advisory.get('session_id')} with {len(advisory.get('advisory_notes', []))} notes",
        payload={
            "session_id": advisory.get("session_id"),
            "intent_profile": advisory.get("intent", {}).get("advisory_profile"),
            "events_analyzed": advisory.get("events_analyzed"),
            "notes_count": len(advisory.get("advisory_notes", [])),
            "guardrail_passed": advisory.get("guardrail_check", {}).get("passed", True),
            "md_path": str(md_path),
            "json_path": str(json_path),
            "md_hash": md_hash,
            "json_hash": json_hash,
        },
        tags=["advisory", "summary", advisory.get("intent", {}).get("advisory_profile", "unknown")],
        session_id=advisory.get("session_id"),
    )
    
    append_event(event)


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print("\nGuardrails enforced:")
    print("- No command proposals")
    print("- No execution suggestions")
    print("- All statements require evidence references")
