# -*- coding: utf-8 -*-
"""
Station Calyx Human Translation Layer
======================================

Converts existing evidence into plain-language assessments for human understanding.

ROLE: agents/human_translation
SCOPE: Evidence-to-language synthesis (presentation only)

CALYX AGENT CONTRACT (Pre-Alpha):
- Assess the environment (components, constraints, capacity)
- Observe and record telemetry during settling window
- Provide evidence-backed assessment of:
  - Past behavior
  - Current state
  - Conditional future trajectories

EXPLICIT NON-GOALS:
- No recommendations
- No optimization steps
- No action items
- No scoring systems
- No implied intelligence or authority
- No user behavior modeling

CONSTRAINTS:
- Advisory-only
- Deterministic logic
- Evidence-backed outputs
- No execution authority
- No implied certainty
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from ..core.evidence import load_recent_events
from ..core.config import get_config

COMPONENT_ROLE = "human_translation"
COMPONENT_SCOPE = "evidence-to-language synthesis"


# --- Environment Classification Thresholds ---
# These determine plain-language descriptors

DISK_CONSTRAINED_THRESHOLD = 80.0      # "storage-constrained"
DISK_CRITICAL_THRESHOLD = 90.0         # "storage-critical"
MEMORY_ELEVATED_THRESHOLD = 70.0       # "memory-elevated"
MEMORY_CONSTRAINED_THRESHOLD = 85.0    # "memory-constrained"
CPU_ELEVATED_THRESHOLD = 50.0          # "compute-active"
CPU_CONSTRAINED_THRESHOLD = 80.0       # "compute-constrained"

# Volatility detection
VOLATILITY_CV_THRESHOLD = 0.15         # Coefficient of variation for "volatile"
SETTLING_WINDOW_MINUTES = 60           # First hour observation window


@dataclass
class EnvironmentProfile:
    """Plain-language environment description."""
    
    # Computed descriptors
    storage_status: str = "unknown"
    memory_status: str = "unknown"
    compute_status: str = "unknown"
    
    # Raw values for reference
    disk_percent: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    
    # Capacity assessment
    primary_constraint: Optional[str] = None
    secondary_constraints: list[str] = field(default_factory=list)
    
    def to_plain_language(self) -> str:
        """Generate plain-language environment summary."""
        parts = []
        
        # Primary characterization
        if self.primary_constraint:
            parts.append(f"This system is primarily {self.primary_constraint}.")
        else:
            parts.append("This system is operating within normal parameters.")
        
        # Component status
        status_parts = []
        if self.storage_status != "stable":
            status_parts.append(f"storage is {self.storage_status} ({self.disk_percent:.0f}% used)")
        if self.memory_status != "stable":
            status_parts.append(f"memory is {self.memory_status} ({self.memory_percent:.0f}% used)")
        if self.compute_status != "stable":
            status_parts.append(f"compute is {self.compute_status} ({self.cpu_percent:.0f}% utilized)")
        
        if status_parts:
            parts.append("Currently: " + ", ".join(status_parts) + ".")
        else:
            parts.append("All resource categories are currently stable.")
        
        return " ".join(parts)


@dataclass
class SettlingObservation:
    """First-hour behavior observation."""
    
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    snapshot_count: int = 0
    
    # Behavior characterization
    behavior_summary: str = "insufficient data"
    volatility_observed: bool = False
    stabilization_noted: bool = False
    anomalies: list[str] = field(default_factory=list)
    
    # Metric ranges
    cpu_range: tuple[float, float] = (0.0, 0.0)
    memory_range: tuple[float, float] = (0.0, 0.0)
    disk_range: tuple[float, float] = (0.0, 0.0)
    
    def to_plain_language(self) -> str:
        """Generate plain-language settling window summary."""
        if self.snapshot_count < 3:
            return "Insufficient observation data to characterize settling behavior."
        
        parts = []
        
        # Window description
        if self.window_start and self.window_end:
            duration_mins = (self.window_end - self.window_start).total_seconds() / 60
            parts.append(f"Over the observation window ({duration_mins:.0f} minutes, {self.snapshot_count} samples):")
        
        # Behavior summary
        parts.append(self.behavior_summary)
        
        # Volatility note
        if self.volatility_observed:
            parts.append("Some resource variability was observed, which may indicate active workloads or system processes.")
        elif self.stabilization_noted:
            parts.append("Resource usage remained relatively consistent throughout the window.")
        
        # Anomalies
        if self.anomalies:
            parts.append("Notable observations: " + "; ".join(self.anomalies[:3]) + ".")
        
        return " ".join(parts)


@dataclass
class TrajectoryStatement:
    """Past ? Present ? Conditional Future assessment."""
    
    metric_name: str = ""
    
    # Past
    past_behavior: str = "unknown"
    past_direction: Optional[str] = None  # "rising", "falling", "stable", "volatile"
    
    # Present
    current_state: str = "unknown"
    current_value: float = 0.0
    
    # Conditional future
    conditional_trajectory: str = "unknown"
    evidence_strength: str = "limited"  # "limited", "moderate", "strong"
    
    def to_plain_language(self) -> str:
        """Generate plain-language trajectory statement."""
        parts = []
        
        # Past
        if self.past_direction:
            parts.append(f"{self.metric_name} has been {self.past_behavior}.")
        
        # Present
        parts.append(f"Currently at {self.current_value:.1f}%, which is {self.current_state}.")
        
        # Conditional future (explicit framing)
        if self.conditional_trajectory != "unknown":
            parts.append(f"If current patterns continue, {self.conditional_trajectory}.")
        
        # Evidence qualifier
        parts.append(f"(Evidence strength: {self.evidence_strength})")
        
        return " ".join(parts)


@dataclass
class ReadinessSummary:
    """Descriptive observation readiness assessment."""
    
    observation_readiness: str = "Limited"  # "High", "Moderate", "Limited"
    primary_constraints: list[str] = field(default_factory=list)
    risk_horizons: list[str] = field(default_factory=list)
    confidence_level: str = "low"
    evidence_window_hours: float = 0.0
    snapshot_count: int = 0
    
    def to_plain_language(self) -> str:
        """Generate plain-language readiness summary."""
        parts = []
        
        # Readiness level
        parts.append(f"Observation readiness: {self.observation_readiness}.")
        
        # Evidence basis
        parts.append(
            f"Based on {self.snapshot_count} snapshots over {self.evidence_window_hours:.1f} hours."
        )
        
        # Constraints
        if self.primary_constraints:
            parts.append(f"Primary constraints: {', '.join(self.primary_constraints)}.")
        else:
            parts.append("No significant constraints identified.")
        
        # Risk horizons (conditional, not predictive)
        if self.risk_horizons:
            parts.append(f"Areas to be mindful of: {', '.join(self.risk_horizons)}.")
        
        # Confidence qualifier
        parts.append(f"Overall confidence in this assessment: {self.confidence_level}.")
        
        return " ".join(parts)


@dataclass
class HumanAssessment:
    """Complete human-readable assessment."""
    
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    environment: EnvironmentProfile = field(default_factory=EnvironmentProfile)
    settling: SettlingObservation = field(default_factory=SettlingObservation)
    trajectories: list[TrajectoryStatement] = field(default_factory=list)
    readiness: ReadinessSummary = field(default_factory=ReadinessSummary)
    
    def to_plain_language(self) -> str:
        """Generate complete plain-language assessment."""
        sections = []
        
        # Header
        sections.append("# System Assessment")
        sections.append("")
        sections.append(f"*Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*")
        sections.append("")
        sections.append("> This assessment describes observed system behavior.")
        sections.append("> It does not recommend actions or predict outcomes.")
        sections.append("")
        
        # Environment summary
        sections.append("## Environment Summary")
        sections.append("")
        sections.append(self.environment.to_plain_language())
        sections.append("")
        
        # Settling observation
        sections.append("## Recent Behavior")
        sections.append("")
        sections.append(self.settling.to_plain_language())
        sections.append("")
        
        # Trajectories
        if self.trajectories:
            sections.append("## Resource Trajectories")
            sections.append("")
            for traj in self.trajectories:
                sections.append(f"**{traj.metric_name}:** {traj.to_plain_language()}")
                sections.append("")
        
        # Readiness
        sections.append("## Observation Summary")
        sections.append("")
        sections.append(self.readiness.to_plain_language())
        sections.append("")
        
        # Footer
        sections.append("---")
        sections.append("")
        sections.append("*This assessment is advisory-only and based on observed evidence.*")
        sections.append("*No actions are recommended or implied.*")
        
        return "\n".join(sections)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "environment": {
                "storage_status": self.environment.storage_status,
                "memory_status": self.environment.memory_status,
                "compute_status": self.environment.compute_status,
                "disk_percent": self.environment.disk_percent,
                "memory_percent": self.environment.memory_percent,
                "cpu_percent": self.environment.cpu_percent,
                "primary_constraint": self.environment.primary_constraint,
            },
            "settling": {
                "snapshot_count": self.settling.snapshot_count,
                "behavior_summary": self.settling.behavior_summary,
                "volatility_observed": self.settling.volatility_observed,
            },
            "trajectories": [
                {
                    "metric": t.metric_name,
                    "past": t.past_behavior,
                    "present": t.current_state,
                    "conditional_future": t.conditional_trajectory,
                    "evidence_strength": t.evidence_strength,
                }
                for t in self.trajectories
            ],
            "readiness": {
                "level": self.readiness.observation_readiness,
                "constraints": self.readiness.primary_constraints,
                "confidence": self.readiness.confidence_level,
                "evidence_hours": self.readiness.evidence_window_hours,
            },
        }


def _classify_storage(percent: float) -> str:
    """Classify storage status in plain language."""
    if percent >= DISK_CRITICAL_THRESHOLD:
        return "critically constrained"
    elif percent >= DISK_CONSTRAINED_THRESHOLD:
        return "constrained"
    elif percent >= 60:
        return "moderately utilized"
    else:
        return "stable"


def _classify_memory(percent: float) -> str:
    """Classify memory status in plain language."""
    if percent >= MEMORY_CONSTRAINED_THRESHOLD:
        return "constrained"
    elif percent >= MEMORY_ELEVATED_THRESHOLD:
        return "elevated"
    else:
        return "stable"


def _classify_compute(percent: float) -> str:
    """Classify compute status in plain language."""
    if percent >= CPU_CONSTRAINED_THRESHOLD:
        return "constrained"
    elif percent >= CPU_ELEVATED_THRESHOLD:
        return "active"
    else:
        return "stable"


def _compute_direction(values: list[float]) -> tuple[str, str]:
    """
    Compute trend direction and behavior description.
    Returns (direction, behavior_description).
    """
    if len(values) < 2:
        return "unknown", "insufficient data to characterize"
    
    # Check volatility
    try:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) >= 2 else 0
        cv = stdev / mean if mean > 0 else 0
        
        if cv > VOLATILITY_CV_THRESHOLD:
            return "volatile", "showing variability"
    except statistics.StatisticsError:
        pass
    
    # Check direction
    first_half = values[:len(values)//2] if len(values) >= 4 else values[:1]
    second_half = values[len(values)//2:] if len(values) >= 4 else values[1:]
    
    if not first_half or not second_half:
        return "stable", "relatively consistent"
    
    first_avg = statistics.mean(first_half)
    second_avg = statistics.mean(second_half)
    
    change = second_avg - first_avg
    change_pct = (change / first_avg * 100) if first_avg > 0 else 0
    
    if abs(change_pct) < 5:
        return "stable", "relatively consistent"
    elif change > 0:
        return "rising", f"gradually increasing (up ~{abs(change_pct):.0f}%)"
    else:
        return "falling", f"gradually decreasing (down ~{abs(change_pct):.0f}%)"


def _build_environment_profile(snapshots: list[dict]) -> EnvironmentProfile:
    """Build environment profile from snapshots."""
    profile = EnvironmentProfile()
    
    if not snapshots:
        return profile
    
    # Use latest snapshot for current state
    latest = snapshots[-1].get("payload", {})
    
    profile.disk_percent = latest.get("disk", {}).get("percent_used", 0)
    profile.memory_percent = latest.get("memory", {}).get("percent", 0)
    profile.cpu_percent = latest.get("cpu_percent", 0)
    
    # Classify each resource
    profile.storage_status = _classify_storage(profile.disk_percent)
    profile.memory_status = _classify_memory(profile.memory_percent)
    profile.compute_status = _classify_compute(profile.cpu_percent)
    
    # Determine primary constraint
    constraints = []
    if profile.storage_status in ("constrained", "critically constrained"):
        constraints.append(("storage-constrained", profile.disk_percent))
    if profile.memory_status == "constrained":
        constraints.append(("memory-constrained", profile.memory_percent))
    if profile.compute_status == "constrained":
        constraints.append(("compute-constrained", profile.cpu_percent))
    
    if constraints:
        # Sort by severity (higher percent = more constrained)
        constraints.sort(key=lambda x: -x[1])
        profile.primary_constraint = constraints[0][0]
        profile.secondary_constraints = [c[0] for c in constraints[1:]]
    
    return profile


def _build_settling_observation(
    snapshots: list[dict],
    window_minutes: int = SETTLING_WINDOW_MINUTES,
) -> SettlingObservation:
    """Build settling window observation."""
    obs = SettlingObservation()
    
    if len(snapshots) < 2:
        return obs
    
    # Determine window
    try:
        latest_ts = datetime.fromisoformat(
            snapshots[-1].get("ts", "").replace("Z", "+00:00")
        )
        window_start = latest_ts - timedelta(minutes=window_minutes)
        
        # Filter to window
        window_snapshots = []
        for snap in snapshots:
            ts = datetime.fromisoformat(snap.get("ts", "").replace("Z", "+00:00"))
            if ts >= window_start:
                window_snapshots.append(snap)
        
        if len(window_snapshots) < 2:
            obs.behavior_summary = "Limited data within the observation window."
            return obs
        
        obs.window_start = window_start
        obs.window_end = latest_ts
        obs.snapshot_count = len(window_snapshots)
        
    except (ValueError, TypeError):
        return obs
    
    # Extract metric series
    cpu_values = []
    mem_values = []
    disk_values = []
    
    for snap in window_snapshots:
        payload = snap.get("payload", {})
        cpu_values.append(payload.get("cpu_percent", 0))
        mem_values.append(payload.get("memory", {}).get("percent", 0))
        disk_values.append(payload.get("disk", {}).get("percent_used", 0))
    
    # Compute ranges
    if cpu_values:
        obs.cpu_range = (min(cpu_values), max(cpu_values))
    if mem_values:
        obs.memory_range = (min(mem_values), max(mem_values))
    if disk_values:
        obs.disk_range = (min(disk_values), max(disk_values))
    
    # Characterize behavior
    cpu_dir, cpu_desc = _compute_direction(cpu_values)
    mem_dir, mem_desc = _compute_direction(mem_values)
    disk_dir, disk_desc = _compute_direction(disk_values)
    
    # Check for volatility
    volatile_metrics = []
    if cpu_dir == "volatile":
        volatile_metrics.append("CPU")
        obs.volatility_observed = True
    if mem_dir == "volatile":
        volatile_metrics.append("memory")
        obs.volatility_observed = True
    
    # Build summary
    if obs.volatility_observed:
        obs.behavior_summary = f"Resource usage showed variability in {', '.join(volatile_metrics)}."
    elif cpu_dir == "stable" and mem_dir == "stable" and disk_dir == "stable":
        obs.behavior_summary = "Resource usage remained stable throughout the observation window."
        obs.stabilization_noted = True
    else:
        changes = []
        if cpu_dir == "rising":
            changes.append("CPU usage increased")
        elif cpu_dir == "falling":
            changes.append("CPU usage decreased")
        if mem_dir == "rising":
            changes.append("memory usage increased")
        elif mem_dir == "falling":
            changes.append("memory usage decreased")
        if disk_dir == "rising":
            changes.append("disk usage increased")
        
        if changes:
            obs.behavior_summary = "; ".join(changes) + " during the window."
        else:
            obs.behavior_summary = "No significant changes observed."
            obs.stabilization_noted = True
    
    # Note anomalies
    if obs.cpu_range[1] - obs.cpu_range[0] > 50:
        obs.anomalies.append(f"CPU varied widely ({obs.cpu_range[0]:.0f}%-{obs.cpu_range[1]:.0f}%)")
    if obs.disk_range[1] >= 90:
        obs.anomalies.append(f"Disk usage reached {obs.disk_range[1]:.0f}%")
    
    return obs


def _build_trajectory(
    metric_name: str,
    values: list[float],
    current_value: float,
    classify_fn,
) -> TrajectoryStatement:
    """Build trajectory statement for a metric."""
    traj = TrajectoryStatement(metric_name=metric_name)
    traj.current_value = current_value
    traj.current_state = classify_fn(current_value)
    
    if len(values) < 3:
        traj.past_behavior = "insufficient history to characterize"
        traj.evidence_strength = "limited"
        traj.conditional_trajectory = "cannot be projected from available data"
        return traj
    
    direction, behavior = _compute_direction(values)
    traj.past_direction = direction
    traj.past_behavior = behavior
    
    # Evidence strength based on sample count
    if len(values) >= 20:
        traj.evidence_strength = "strong"
    elif len(values) >= 10:
        traj.evidence_strength = "moderate"
    else:
        traj.evidence_strength = "limited"
    
    # Conditional future (explicit "if" framing, no timelines)
    if direction == "rising":
        if metric_name == "Storage":
            traj.conditional_trajectory = "available space may continue to decrease"
        elif metric_name == "Memory":
            traj.conditional_trajectory = "memory headroom may continue to narrow"
        else:
            traj.conditional_trajectory = "utilization may continue to increase"
    elif direction == "falling":
        traj.conditional_trajectory = "usage may continue to decrease"
    elif direction == "volatile":
        traj.conditional_trajectory = "variability may persist"
    else:
        traj.conditional_trajectory = "current levels are expected to persist"
    
    return traj


def _build_readiness_summary(
    snapshots: list[dict],
    environment: EnvironmentProfile,
    trajectories: list[TrajectoryStatement],
) -> ReadinessSummary:
    """Build readiness summary."""
    summary = ReadinessSummary()
    summary.snapshot_count = len(snapshots)
    
    # Calculate evidence window
    if len(snapshots) >= 2:
        try:
            first_ts = datetime.fromisoformat(
                snapshots[0].get("ts", "").replace("Z", "+00:00")
            )
            last_ts = datetime.fromisoformat(
                snapshots[-1].get("ts", "").replace("Z", "+00:00")
            )
            summary.evidence_window_hours = (last_ts - first_ts).total_seconds() / 3600
        except (ValueError, TypeError):
            pass
    
    # Determine observation readiness
    if summary.snapshot_count >= 30 and summary.evidence_window_hours >= 6:
        summary.observation_readiness = "High"
        summary.confidence_level = "moderate"
    elif summary.snapshot_count >= 10 and summary.evidence_window_hours >= 1:
        summary.observation_readiness = "Moderate"
        summary.confidence_level = "low-to-moderate"
    else:
        summary.observation_readiness = "Limited"
        summary.confidence_level = "low"
    
    # Primary constraints
    if environment.primary_constraint:
        summary.primary_constraints.append(environment.primary_constraint)
    summary.primary_constraints.extend(environment.secondary_constraints)
    
    # Risk horizons (areas to be mindful of, not predictions)
    for traj in trajectories:
        if traj.past_direction == "rising" and traj.metric_name == "Storage":
            summary.risk_horizons.append("storage capacity")
        if traj.past_direction == "volatile":
            summary.risk_horizons.append(f"{traj.metric_name.lower()} stability")
    
    if environment.disk_percent >= 85:
        if "storage capacity" not in summary.risk_horizons:
            summary.risk_horizons.append("storage capacity")
    
    return summary


def generate_human_assessment(
    events: Optional[list[dict]] = None,
    recent: int = 500,
) -> HumanAssessment:
    """
    Generate a complete human-readable assessment from evidence.
    
    This is the main entry point for the human translation layer.
    """
    if events is None:
        events = load_recent_events(recent)
    
    # Extract snapshots
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    snapshots.sort(key=lambda e: e.get("ts", ""))
    
    assessment = HumanAssessment()
    
    # Build components
    assessment.environment = _build_environment_profile(snapshots)
    assessment.settling = _build_settling_observation(snapshots)
    
    # Build trajectories for each major resource
    if snapshots:
        cpu_values = [s.get("payload", {}).get("cpu_percent", 0) for s in snapshots]
        mem_values = [s.get("payload", {}).get("memory", {}).get("percent", 0) for s in snapshots]
        disk_values = [s.get("payload", {}).get("disk", {}).get("percent_used", 0) for s in snapshots]
        
        assessment.trajectories = [
            _build_trajectory("Storage", disk_values, assessment.environment.disk_percent, _classify_storage),
            _build_trajectory("Memory", mem_values, assessment.environment.memory_percent, _classify_memory),
            _build_trajectory("Compute", cpu_values, assessment.environment.cpu_percent, _classify_compute),
        ]
    
    # Build readiness summary
    assessment.readiness = _build_readiness_summary(
        snapshots,
        assessment.environment,
        assessment.trajectories,
    )
    
    return assessment


def print_human_assessment(assessment: Optional[HumanAssessment] = None) -> None:
    """Print human assessment to stdout."""
    if assessment is None:
        assessment = generate_human_assessment()
    
    print(assessment.to_plain_language())


if __name__ == "__main__":
    print(f"[{COMPONENT_ROLE}] Role: {COMPONENT_SCOPE}")
    print()
    print_human_assessment()
