#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Station Calyx Temporal Research Scheduler
==========================================

Time-bound automated research data collection using existing API triggers.

ROLE: tools/scheduler
SCOPE: Scheduled API triggering for research data collection

CONSTRAINTS (NON-NEGOTIABLE):
- Advisory-only system
- No execution of system commands
- No file modification beyond existing append-only evidence logs
- No LLM usage
- No conversational UI
- Deterministic logic only
- Respect rate limits
- All actions are user-equivalent API triggers already exposed in UI

SCHEDULING DEFAULTS:
- Snapshots: Every 15 minutes
- Reflections: Every 2 hours (if >= 4 new snapshots)
- Advisories: Every 3 hours (profile based on disk usage)
- Temporal Analysis: Every 6 hours

Usage:
    python -B tools/scheduled_research.py
    python -B tools/scheduled_research.py --dry-run
    python -B tools/scheduled_research.py --duration 24h
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from station_calyx.core.evidence import append_event, create_event, load_recent_events
from station_calyx.core.config import get_config


# --- Scheduling Configuration ---
# All intervals in seconds

SNAPSHOT_INTERVAL = 15 * 60        # 15 minutes
REFLECTION_INTERVAL = 2 * 60 * 60  # 2 hours
ADVISORY_INTERVAL = 3 * 60 * 60    # 3 hours
TEMPORAL_INTERVAL = 6 * 60 * 60    # 6 hours

# Preconditions
MIN_SNAPSHOTS_FOR_REFLECTION = 4
DISK_THRESHOLD_FOR_STORAGE_PROFILE = 85.0

# Rate limiting
MIN_INTERVAL_BETWEEN_ACTIONS = 30  # seconds
MAX_API_FAILURES_BEFORE_PAUSE = 3
PAUSE_DURATION_AFTER_FAILURES = 5 * 60  # 5 minutes

COMPONENT_ROLE = "scheduled_research"
COMPONENT_SCOPE = "time-bound temporal research data collection"


@dataclass
class SchedulerState:
    """Tracks scheduler state for reporting."""
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Counters
    snapshots_triggered: int = 0
    reflections_triggered: int = 0
    advisories_triggered: int = 0
    temporal_analyses_triggered: int = 0
    
    # Last action times
    last_snapshot: Optional[datetime] = None
    last_reflection: Optional[datetime] = None
    last_advisory: Optional[datetime] = None
    last_temporal: Optional[datetime] = None
    
    # Snapshot count tracking
    snapshots_since_reflection: int = 0
    
    # Failure tracking
    consecutive_failures: int = 0
    total_failures: int = 0
    skipped_actions: int = 0
    
    # Intent tracking
    advisory_intents: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "duration_hours": (datetime.now(timezone.utc) - self.started_at).total_seconds() / 3600,
            "snapshots_triggered": self.snapshots_triggered,
            "reflections_triggered": self.reflections_triggered,
            "advisories_triggered": self.advisories_triggered,
            "temporal_analyses_triggered": self.temporal_analyses_triggered,
            "total_actions": (
                self.snapshots_triggered + self.reflections_triggered +
                self.advisories_triggered + self.temporal_analyses_triggered
            ),
            "total_failures": self.total_failures,
            "skipped_actions": self.skipped_actions,
            "advisory_intents": self.advisory_intents,
        }


def log_scheduler_event(
    event_type: str,
    action: str,
    success: bool,
    details: dict,
    state: SchedulerState,
) -> None:
    """Log scheduler action to evidence."""
    event = create_event(
        event_type=event_type,
        node_role=COMPONENT_ROLE,
        summary=f"Scheduled {action}: {'success' if success else 'failed'}",
        payload={
            "action": action,
            "trigger_type": "scheduled",
            "success": success,
            "snapshot_count_at_action": state.snapshots_triggered,
            **details,
        },
        tags=["scheduler", "research", action],
    )
    append_event(event)


def check_api_available() -> bool:
    """Check if API is reachable."""
    try:
        from station_calyx_desktop.api_client import is_service_running
        return is_service_running()
    except Exception:
        return False


def get_current_disk_percent() -> float:
    """Get current disk usage percent from latest snapshot."""
    try:
        events = load_recent_events(50)
        snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
        if snapshots:
            latest = snapshots[-1]
            return latest.get("payload", {}).get("disk", {}).get("percent_used", 0)
    except Exception:
        pass
    return 0.0


def trigger_snapshot(state: SchedulerState, dry_run: bool = False) -> bool:
    """Trigger a snapshot via API."""
    if dry_run:
        print(f"[DRY-RUN] Would trigger snapshot")
        return True
    
    try:
        from station_calyx_desktop.api_client import get_client
        client = get_client()
        response = client.capture_snapshot()
        
        if response.success:
            state.snapshots_triggered += 1
            state.snapshots_since_reflection += 1
            state.last_snapshot = datetime.now(timezone.utc)
            state.consecutive_failures = 0
            
            log_scheduler_event(
                "SCHEDULED_SNAPSHOT",
                "snapshot",
                True,
                {"snapshots_since_reflection": state.snapshots_since_reflection},
                state,
            )
            return True
        else:
            state.consecutive_failures += 1
            state.total_failures += 1
            log_scheduler_event(
                "SCHEDULED_SNAPSHOT_FAILED",
                "snapshot",
                False,
                {"error": response.error},
                state,
            )
            return False
    except Exception as e:
        state.consecutive_failures += 1
        state.total_failures += 1
        return False


def trigger_reflection(state: SchedulerState, dry_run: bool = False) -> bool:
    """Trigger a reflection via API."""
    # Precondition check
    if state.snapshots_since_reflection < MIN_SNAPSHOTS_FOR_REFLECTION:
        state.skipped_actions += 1
        print(f"[SKIP] Reflection: only {state.snapshots_since_reflection} snapshots (need {MIN_SNAPSHOTS_FOR_REFLECTION})")
        return False
    
    if dry_run:
        print(f"[DRY-RUN] Would trigger reflection ({state.snapshots_since_reflection} snapshots)")
        return True
    
    try:
        from station_calyx_desktop.api_client import get_client
        client = get_client()
        response = client.run_reflection()
        
        if response.success:
            state.reflections_triggered += 1
            state.last_reflection = datetime.now(timezone.utc)
            snapshots_used = state.snapshots_since_reflection
            state.snapshots_since_reflection = 0  # Reset counter
            state.consecutive_failures = 0
            
            log_scheduler_event(
                "SCHEDULED_REFLECTION",
                "reflection",
                True,
                {"snapshots_used": snapshots_used},
                state,
            )
            return True
        else:
            state.consecutive_failures += 1
            state.total_failures += 1
            log_scheduler_event(
                "SCHEDULED_REFLECTION_FAILED",
                "reflection",
                False,
                {"error": response.error},
                state,
            )
            return False
    except Exception as e:
        state.consecutive_failures += 1
        state.total_failures += 1
        return False


def trigger_advisory(state: SchedulerState, dry_run: bool = False) -> bool:
    """Trigger an advisory via API with profile selection."""
    # Determine profile based on disk usage
    disk_percent = get_current_disk_percent()
    
    if disk_percent >= DISK_THRESHOLD_FOR_STORAGE_PROFILE:
        profile = "storage_pressure"
    else:
        profile = "stability_first"
    
    # Track intent frequency
    state.advisory_intents[profile] = state.advisory_intents.get(profile, 0) + 1
    
    if dry_run:
        print(f"[DRY-RUN] Would trigger advisory (profile: {profile}, disk: {disk_percent:.1f}%)")
        return True
    
    try:
        from station_calyx_desktop.api_client import get_client
        client = get_client()
        
        # Set intent profile first
        client.set_intent(profile, f"Scheduled research - disk at {disk_percent:.1f}%")
        
        response = client.generate_advisory()
        
        if response.success:
            state.advisories_triggered += 1
            state.last_advisory = datetime.now(timezone.utc)
            state.consecutive_failures = 0
            
            log_scheduler_event(
                "SCHEDULED_ADVISORY",
                "advisory",
                True,
                {"profile": profile, "disk_percent": disk_percent},
                state,
            )
            return True
        else:
            state.consecutive_failures += 1
            state.total_failures += 1
            log_scheduler_event(
                "SCHEDULED_ADVISORY_FAILED",
                "advisory",
                False,
                {"error": response.error, "profile": profile},
                state,
            )
            return False
    except Exception as e:
        state.consecutive_failures += 1
        state.total_failures += 1
        return False


def trigger_temporal_analysis(state: SchedulerState, dry_run: bool = False) -> bool:
    """Trigger temporal analysis via API."""
    if dry_run:
        print(f"[DRY-RUN] Would trigger temporal analysis")
        return True
    
    try:
        from station_calyx_desktop.api_client import get_client
        client = get_client()
        response = client.run_temporal_analysis()
        
        if response.success:
            state.temporal_analyses_triggered += 1
            state.last_temporal = datetime.now(timezone.utc)
            state.consecutive_failures = 0
            
            log_scheduler_event(
                "SCHEDULED_TEMPORAL_ANALYSIS",
                "temporal",
                True,
                {"total_snapshots": state.snapshots_triggered},
                state,
            )
            return True
        else:
            state.consecutive_failures += 1
            state.total_failures += 1
            log_scheduler_event(
                "SCHEDULED_TEMPORAL_ANALYSIS_FAILED",
                "temporal",
                False,
                {"error": response.error},
                state,
            )
            return False
    except Exception as e:
        state.consecutive_failures += 1
        state.total_failures += 1
        return False


def should_trigger(last_time: Optional[datetime], interval: int) -> bool:
    """Check if enough time has passed since last trigger."""
    if last_time is None:
        return True
    
    elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
    return elapsed >= interval


def print_status(state: SchedulerState) -> None:
    """Print current scheduler status."""
    now = datetime.now(timezone.utc)
    runtime = now - state.started_at
    
    print(f"\n{'='*60}")
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Scheduler Status")
    print(f"{'='*60}")
    print(f"Runtime: {runtime.total_seconds() / 3600:.1f} hours")
    print(f"Snapshots: {state.snapshots_triggered}")
    print(f"Reflections: {state.reflections_triggered}")
    print(f"Advisories: {state.advisories_triggered}")
    print(f"Temporal Analyses: {state.temporal_analyses_triggered}")
    print(f"Failures: {state.total_failures} | Skipped: {state.skipped_actions}")
    print(f"Advisory intents: {state.advisory_intents}")
    print(f"{'='*60}\n")


def generate_return_report(state: SchedulerState) -> str:
    """Generate summary report for Architect return."""
    now = datetime.now(timezone.utc)
    runtime = now - state.started_at
    
    lines = [
        "# Temporal Research Scheduler Report",
        "",
        f"**Duration:** {runtime.total_seconds() / 3600:.1f} hours",
        f"**Started:** {state.started_at.isoformat()}",
        f"**Ended:** {now.isoformat()}",
        "",
        "## Actions Triggered",
        "",
        f"| Action | Count |",
        f"|--------|-------|",
        f"| Snapshots | {state.snapshots_triggered} |",
        f"| Reflections | {state.reflections_triggered} |",
        f"| Advisories | {state.advisories_triggered} |",
        f"| Temporal Analyses | {state.temporal_analyses_triggered} |",
        f"| **Total** | {state.snapshots_triggered + state.reflections_triggered + state.advisories_triggered + state.temporal_analyses_triggered} |",
        "",
        "## Advisory Intent Frequency",
        "",
    ]
    
    if state.advisory_intents:
        for intent, count in state.advisory_intents.items():
            lines.append(f"- {intent}: {count} times")
    else:
        lines.append("- No advisories generated")
    
    lines.extend([
        "",
        "## Reliability",
        "",
        f"- Total failures: {state.total_failures}",
        f"- Skipped actions (preconditions not met): {state.skipped_actions}",
        "",
        "## Notes",
        "",
        "- All data logged to evidence.jsonl",
        "- Run `python -m station_calyx.ui.cli trends` for current analysis",
        "- Run `python -B tools/verify_imports.py` to verify module paths",
        "",
        "---",
        "*Report generated by scheduled_research.py*",
    ])
    
    return "\n".join(lines)


def run_scheduler(
    duration_hours: Optional[float] = None,
    dry_run: bool = False,
    verbose: bool = True,
) -> SchedulerState:
    """
    Run the scheduled research loop.
    
    Args:
        duration_hours: Max duration in hours (None = run until interrupted)
        dry_run: If True, don't actually trigger actions
        verbose: Print status updates
    """
    state = SchedulerState()
    
    print(f"\n{'='*60}")
    print("Station Calyx Temporal Research Scheduler")
    print(f"{'='*60}")
    print(f"Started: {state.started_at.isoformat()}")
    print(f"Duration: {'unlimited' if duration_hours is None else f'{duration_hours}h'}")
    print(f"Dry run: {dry_run}")
    print(f"\nSchedule:")
    print(f"  - Snapshots: every {SNAPSHOT_INTERVAL // 60} minutes")
    print(f"  - Reflections: every {REFLECTION_INTERVAL // 3600} hours (if >= {MIN_SNAPSHOTS_FOR_REFLECTION} snapshots)")
    print(f"  - Advisories: every {ADVISORY_INTERVAL // 3600} hours")
    print(f"  - Temporal Analysis: every {TEMPORAL_INTERVAL // 3600} hours")
    print(f"\nPress Ctrl+C to stop and generate report.\n")
    
    # Log scheduler start
    if not dry_run:
        log_scheduler_event(
            "SCHEDULER_STARTED",
            "scheduler",
            True,
            {
                "duration_hours": duration_hours,
                "snapshot_interval": SNAPSHOT_INTERVAL,
                "reflection_interval": REFLECTION_INTERVAL,
                "advisory_interval": ADVISORY_INTERVAL,
                "temporal_interval": TEMPORAL_INTERVAL,
            },
            state,
        )
    
    end_time = None
    if duration_hours is not None:
        end_time = state.started_at + timedelta(hours=duration_hours)
    
    try:
        while True:
            now = datetime.now(timezone.utc)
            
            # Check duration limit
            if end_time is not None and now >= end_time:
                print("\n[COMPLETE] Duration limit reached.")
                break
            
            # Check API availability
            if not dry_run and not check_api_available():
                print(f"[WAIT] API not available, waiting...")
                time.sleep(60)
                continue
            
            # Check for failure pause
            if state.consecutive_failures >= MAX_API_FAILURES_BEFORE_PAUSE:
                print(f"[PAUSE] {state.consecutive_failures} consecutive failures, pausing {PAUSE_DURATION_AFTER_FAILURES // 60} minutes...")
                time.sleep(PAUSE_DURATION_AFTER_FAILURES)
                state.consecutive_failures = 0
                continue
            
            # Snapshot check
            if should_trigger(state.last_snapshot, SNAPSHOT_INTERVAL):
                if verbose:
                    print(f"[{now.strftime('%H:%M:%S')}] Triggering snapshot...")
                if trigger_snapshot(state, dry_run):
                    if verbose:
                        print(f"  -> Snapshot #{state.snapshots_triggered} complete")
            
            # Reflection check
            if should_trigger(state.last_reflection, REFLECTION_INTERVAL):
                if verbose:
                    print(f"[{now.strftime('%H:%M:%S')}] Checking reflection...")
                if trigger_reflection(state, dry_run):
                    if verbose:
                        print(f"  -> Reflection #{state.reflections_triggered} complete")
            
            # Advisory check
            if should_trigger(state.last_advisory, ADVISORY_INTERVAL):
                if verbose:
                    print(f"[{now.strftime('%H:%M:%S')}] Triggering advisory...")
                if trigger_advisory(state, dry_run):
                    if verbose:
                        print(f"  -> Advisory #{state.advisories_triggered} complete")
            
            # Temporal analysis check
            if should_trigger(state.last_temporal, TEMPORAL_INTERVAL):
                if verbose:
                    print(f"[{now.strftime('%H:%M:%S')}] Triggering temporal analysis...")
                if trigger_temporal_analysis(state, dry_run):
                    if verbose:
                        print(f"  -> Temporal analysis #{state.temporal_analyses_triggered} complete")
            
            # Status update every hour
            runtime_hours = (now - state.started_at).total_seconds() / 3600
            if runtime_hours > 0 and int(runtime_hours) > int((now - timedelta(minutes=1) - state.started_at).total_seconds() / 3600):
                print_status(state)
            
            # Sleep before next check
            time.sleep(MIN_INTERVAL_BETWEEN_ACTIONS)
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopping scheduler...")
    
    # Log scheduler stop
    if not dry_run:
        log_scheduler_event(
            "SCHEDULER_STOPPED",
            "scheduler",
            True,
            state.to_dict(),
            state,
        )
    
    # Generate and save report
    report = generate_return_report(state)
    
    report_path = Path("summaries") / f"research_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    
    print(f"\n{'='*60}")
    print("SCHEDULER REPORT")
    print(f"{'='*60}")
    print(report)
    print(f"\nReport saved to: {report_path}")
    
    return state


def main():
    parser = argparse.ArgumentParser(
        description="Station Calyx Temporal Research Scheduler"
    )
    parser.add_argument(
        "--duration",
        type=str,
        default=None,
        help="Duration to run (e.g., '24h', '6h', '30m'). Default: unlimited"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually trigger actions, just simulate"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Parse duration
    duration_hours = None
    if args.duration:
        if args.duration.endswith('h'):
            duration_hours = float(args.duration[:-1])
        elif args.duration.endswith('m'):
            duration_hours = float(args.duration[:-1]) / 60
        else:
            duration_hours = float(args.duration)
    
    run_scheduler(
        duration_hours=duration_hours,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
