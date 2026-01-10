#!/usr/bin/env python3
"""
Station Calyx CLI
=================

Command-line interface for the Ops Reflector service.

Usage:
    python -m station_calyx.ui.cli status
    python -m station_calyx.ui.cli snapshot
    python -m station_calyx.ui.cli reflect --recent 100
    python -m station_calyx.ui.cli ingest --file event.json
    python -m station_calyx.ui.cli intent set --profile STABILITY_FIRST --desc "..."
    python -m station_calyx.ui.cli intent show
    python -m station_calyx.ui.cli advise

Role: ui/cli
Scope: Command-line interface for local operations
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from station_calyx.core.config import get_config
from station_calyx.core.evidence import (
    append_event,
    create_event,
    load_recent_events,
    get_last_event_ts,
    compute_sha256,
)
from station_calyx.core.policy import get_policy_gate
from station_calyx.core.intent import (
    UserIntent,
    AdvisoryProfile,
    load_current_intent,
    save_intent,
    create_intent,
    get_or_create_default_intent,
)
from station_calyx.connectors.sys_telemetry import collect_snapshot, format_snapshot_summary
from station_calyx.agents.reflector import reflect, save_reflection, log_reflection_event, format_reflection_markdown
from station_calyx.agents.advisor import generate_advisory, save_advisory, log_advisory_event, format_advisory_markdown
from station_calyx.agents.temporal import (
    run_temporal_analysis,
    save_temporal_analysis,
    log_temporal_event,
    log_finding_events,
    format_temporal_markdown,
)
from station_calyx.ui.status_surface import (
    generate_status_surface,
    format_status_markdown,
    save_status_surface,
    load_status_surface,
)
from station_calyx.core.notifications import (
    get_emitter,
    get_notifications_from_evidence,
)
from station_calyx.core.service import (
    start_service,
    stop_service,
    get_service_status,
)
from station_calyx.core.doctor import (
    run_all_checks,
    format_doctor_report,
)
from station_calyx.core.onboarding import (
    is_first_run,
    present_onboarding,
    load_onboarding,
)

# Role declaration
COMPONENT_ROLE = "cli"
COMPONENT_SCOPE = "command-line interface"


def cmd_status(args: argparse.Namespace) -> int:
    """Show service status."""
    # Check for --human flag
    if hasattr(args, 'human') and args.human:
        return cmd_status_human(args)
    
    config = get_config()
    policy_gate = get_policy_gate()
    
    events = load_recent_events(10000)
    last_ts = get_last_event_ts()
    
    print(f"\n=== {config.station_name} Status ===")
    print(f"Version: {config.version}")
    print(f"Data Directory: {config.data_dir}")
    print(f"Advisory-only: {config.advisory_only}")
    print(f"Execution enabled: {config.execution_enabled}")
    print(f"\n--- Evidence Log ---")
    print(f"Total events: {len(events)}")
    print(f"Last event: {last_ts or 'none'}")
    print(f"\n--- Policy Gate ---")
    stats = policy_gate.get_stats()
    print(f"Policy version: {stats['policy_version']}")
    print(f"Deny-all: {stats['deny_all']}")
    print(f"Total decisions: {stats['total_decisions']}")
    print(f"Denied: {stats['denied_count']}")
    print()
    
    return 0


def cmd_status_human(args: argparse.Namespace) -> int:
    """Show human-friendly status summary."""
    # Try to load existing status first
    existing = load_status_surface()
    
    if existing and not getattr(args, 'refresh', False):
        print(existing)
    else:
        # Generate fresh status
        status = generate_status_surface()
        save_status_surface(status)
        print(format_status_markdown(status))
    
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Capture and display system snapshot."""
    print("Capturing system snapshot...")
    
    snapshot = collect_snapshot()
    summary = format_snapshot_summary(snapshot)
    
    print(summary)
    
    if not args.no_log:
        # Log to evidence
        event = create_event(
            event_type="SYSTEM_SNAPSHOT",
            node_role="cli_snapshot",
            summary=f"CLI snapshot: {snapshot.get('hostname', 'unknown')}",
            payload=snapshot,
            tags=["snapshot", "cli"],
        )
        append_event(event)
        print("\nSnapshot logged to evidence.jsonl")
    
    if args.json:
        print("\n--- JSON Output ---")
        print(json.dumps(snapshot, indent=2))
    
    return 0


def cmd_reflect(args: argparse.Namespace) -> int:
    """Run reflection over recent events."""
    recent = args.recent
    
    print(f"Loading last {recent} events...")
    events = load_recent_events(recent)
    
    if not events:
        print("No events found. Run `calyx snapshot` first to generate some data.")
        return 1
    
    print(f"Analyzing {len(events)} events...")
    
    reflection = reflect(events)
    
    # Save artifacts
    md_path, json_path = save_reflection(reflection)
    log_reflection_event(reflection, md_path, json_path)
    
    # Display reflection
    if args.json:
        print(json.dumps(reflection, indent=2))
    else:
        print(format_reflection_markdown(reflection))
    
    print(f"\n--- Artifacts Saved ---")
    print(f"Markdown: {md_path}")
    print(f"JSON: {json_path}")
    
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest event from file."""
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
    
    try:
        content = file_path.read_bytes()
        content_hash = compute_sha256(content)
        
        # Try to parse as JSON
        try:
            payload = json.loads(content.decode("utf-8"))
            event_type = payload.pop("event_type", "FILE_INGESTED")
            summary = payload.pop("summary", f"File ingested: {file_path.name}")
            tags = payload.pop("tags", ["ingested"])
        except json.JSONDecodeError:
            # Not JSON, treat as raw file
            event_type = "FILE_INGESTED"
            summary = f"Raw file ingested: {file_path.name}"
            payload = {
                "filename": file_path.name,
                "size_bytes": len(content),
                "content_hash": content_hash,
            }
            tags = ["ingested", "raw"]
        
        event = create_event(
            event_type=event_type,
            node_role="cli_ingest",
            summary=summary,
            payload={
                **payload,
                "source_file": str(file_path),
                "file_hash": content_hash,
            },
            tags=tags,
        )
        
        append_event(event)
        
        print(f"? Event ingested: {event_type}")
        print(f"  File: {file_path.name}")
        print(f"  Hash: {content_hash[:16]}...")
        print(f"  Timestamp: {event['ts']}")
        
        return 0
        
    except Exception as e:
        print(f"Error ingesting file: {e}")
        return 1


def cmd_events(args: argparse.Namespace) -> int:
    """List recent events."""
    events = load_recent_events(args.recent)
    
    if not events:
        print("No events found.")
        return 0
    
    print(f"\n=== Last {len(events)} Events ===\n")
    
    for e in events[-args.recent:]:
        ts = e.get("ts", "?")[:19]
        etype = e.get("event_type", "?")
        summary = e.get("summary", "")[:60]
        print(f"[{ts}] {etype:20} {summary}")
    
    print()
    return 0


def cmd_intent_set(args: argparse.Namespace) -> int:
    """Set or update user intent."""
    try:
        profile = AdvisoryProfile.from_string(args.profile)
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Valid profiles: {[p.name for p in AdvisoryProfile]}")
        return 1
    
    description = args.desc or f"User intent: {profile.value}"
    
    intent = create_intent(
        description=description,
        profile=profile,
    )
    
    save_intent(intent, log_event=True)
    
    framing = intent.get_framing()
    print(f"\n=== Intent Set ===")
    print(f"Intent ID: {intent.intent_id}")
    print(f"Profile: {intent.advisory_profile.value}")
    print(f"Description: {intent.description}")
    print(f"Priority: {framing.get('priority', 'N/A')}")
    print(f"Tone: {framing.get('tone', 'N/A')}")
    print(f"Emphasis: {', '.join(framing.get('emphasis', []))}")
    print(f"\n[Logged INTENT_SET event to evidence.jsonl]")
    
    return 0


def cmd_intent_show(args: argparse.Namespace) -> int:
    """Show current user intent."""
    intent = load_current_intent()
    
    if not intent:
        print("No intent set. Use `calyx intent set --profile <PROFILE>` to set one.")
        print(f"\nAvailable profiles:")
        for p in AdvisoryProfile:
            framing = p.get_framing_guidance()
            print(f"  - {p.name}: {framing.get('priority', 'N/A')}")
        return 0
    
    framing = intent.get_framing()
    print(f"\n=== Current Intent ===")
    print(f"Intent ID: {intent.intent_id}")
    print(f"Profile: {intent.advisory_profile.value}")
    print(f"Description: {intent.description}")
    print(f"Created: {intent.created_at.isoformat()}")
    print(f"\n--- Framing Guidance ---")
    print(f"Priority: {framing.get('priority', 'N/A')}")
    print(f"Tone: {framing.get('tone', 'N/A')}")
    print(f"Risk Tolerance: {framing.get('risk_tolerance', 'N/A')}")
    print(f"Emphasis: {', '.join(framing.get('emphasis', []))}")
    print(f"Avoid: {', '.join(framing.get('avoid', []))}")
    print()
    
    return 0


def cmd_advise(args: argparse.Namespace) -> int:
    """Generate advisory based on current intent."""
    recent = args.recent
    
    print(f"Loading last {recent} events...")
    events = load_recent_events(recent)
    
    if not events:
        print("No events found. Run `calyx snapshot` first.")
        return 1
    
    # Get or create intent
    intent = get_or_create_default_intent()
    print(f"Using intent profile: {intent.advisory_profile.value}")
    
    # Run reflection first
    print("Running reflection...")
    reflection = reflect(events)
    
    # Generate advisory
    print("Generating advisory...")
    advisory = generate_advisory(events, reflection, intent)
    
    # Save artifacts
    md_path, json_path = save_advisory(advisory)
    log_advisory_event(advisory, md_path, json_path)
    
    # Display
    if args.json:
        print(json.dumps(advisory, indent=2))
    else:
        print(format_advisory_markdown(advisory))
    
    print(f"\n--- Artifacts Saved ---")
    print(f"Markdown: {md_path}")
    print(f"JSON: {json_path}")
    
    guardrail = advisory.get("guardrail_check", {})
    if guardrail.get("passed", True):
        print("\n[Guardrails: PASSED]")
    else:
        print(f"\n[Guardrails: VIOLATIONS - {guardrail.get('violations', [])}]")
    
    return 0


def cmd_trends(args: argparse.Namespace) -> int:
    """Show recent temporal trends."""
    events = load_recent_events(1000)
    
    # Find trend-related events
    trends = [e for e in events if e.get("event_type") == "TREND_DETECTED"]
    drifts = [e for e in events if e.get("event_type") == "DRIFT_WARNING"]
    patterns = [e for e in events if e.get("event_type") == "PATTERN_RECURRING"]
    analyses = [e for e in events if e.get("event_type") == "TEMPORAL_ANALYSIS_COMPLETED"]
    
    print("\n=== Recent Temporal Findings ===\n")
    
    if analyses:
        latest = analyses[-1]
        print(f"Last analysis: {latest.get('ts', 'unknown')[:19]}")
        payload = latest.get("payload", {})
        print(f"  Snapshots analyzed: {payload.get('snapshots_analyzed', 0)}")
        print(f"  Time span: {payload.get('time_span_hours', 0)}h")
        print(f"  Total findings: {payload.get('total_findings', 0)}")
        print()
    
    print(f"--- Trends ({len(trends)}) ---")
    for t in trends[-5:]:
        payload = t.get("payload", {})
        print(f"  [{t.get('ts', '?')[:19]}] {payload.get('metric_name', '?')}: {payload.get('direction', '?')}")
    
    print(f"\n--- Drift Warnings ({len(drifts)}) ---")
    for d in drifts[-5:]:
        payload = d.get("payload", {})
        print(f"  [{d.get('ts', '?')[:19]}] {payload.get('metric_name', '?')}: {payload.get('direction', '?')}")
    
    print(f"\n--- Recurring Patterns ({len(patterns)}) ---")
    for p in patterns[-5:]:
        print(f"  [{p.get('ts', '?')[:19]}] {p.get('summary', '?')[:60]}")
    
    if not (trends or drifts or patterns):
        print("No temporal findings yet. Run `calyx analyze temporal` first.")
    
    print()
    return 0


def cmd_analyze_temporal(args: argparse.Namespace) -> int:
    """Run temporal analysis."""
    recent = args.recent
    
    print(f"Loading last {recent} events...")
    events = load_recent_events(recent)
    
    snapshots = [e for e in events if e.get("event_type") == "SYSTEM_SNAPSHOT"]
    print(f"Found {len(snapshots)} snapshots to analyze...")
    
    if len(snapshots) < 2:
        print("Need at least 2 snapshots for temporal analysis. Run `calyx snapshot` multiple times.")
        return 1
    
    print("Running temporal analysis...")
    analysis = run_temporal_analysis(events)
    
    # Save artifacts
    md_path, json_path = save_temporal_analysis(analysis)
    log_temporal_event(analysis, md_path, json_path)
    
    # Log individual findings
    all_findings = (
        analysis.get("trends_detected", []) +
        analysis.get("drift_warnings", []) +
        analysis.get("recurring_patterns", [])
    )
    if all_findings:
        log_finding_events(all_findings, analysis.get("session_id", "unknown"))
    
    # Display
    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print(format_temporal_markdown(analysis))
    
    print(f"\n--- Artifacts Saved ---")
    print(f"Markdown: {md_path}")
    print(f"JSON: {json_path}")
    
    guardrails = analysis.get("guardrails", {})
    if all(guardrails.values()) if guardrails else True:
        print("\n[Guardrails: PASSED]")
    else:
        print(f"\n[Guardrails: CHECK FAILED]")
    
    return 0


def cmd_notify_test(args: argparse.Namespace) -> int:
    """Show test notification without emitting to evidence."""
    emitter = get_emitter()
    test_notification = emitter.test_notification()
    
    print("\n[TEST MODE - This notification is not logged to evidence]")
    print(test_notification.format_console())
    
    print("Notification triggers:")
    print("- DRIFT_WARNING events")
    print("- PATTERN_RECURRING events")
    print("- HIGH confidence advisories")
    print(f"\nRate limit: 3 per 5 minutes")
    
    return 0


def cmd_notifications(args: argparse.Namespace) -> int:
    """Show recent notifications."""
    notifications = get_notifications_from_evidence(limit=10)
    
    if not notifications:
        print("\nNo notifications emitted yet.")
        print("Notifications are triggered by:")
        print("- DRIFT_WARNING events")
        print("- PATTERN_RECURRING events")
        print("- HIGH confidence advisories")
        return 0
    
    print(f"\n=== Recent Notifications ({len(notifications)}) ===\n")
    
    for n in notifications:
        print(f"[{n.get('timestamp', '?')[:19]}] {n.get('priority', '?').upper()}")
        print(f"  Title: {n.get('title', '?')}")
        print(f"  Message: {n.get('message', '?')[:60]}...")
        print()
    
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Start the Station Calyx service."""
    # First-run onboarding
    if is_first_run():
        print("\n[First Run] Generating onboarding documentation...")
        present_onboarding()
        print("[First Run] See: station_calyx/data/onboarding.md\n")
    
    # Check current status
    status = get_service_status()
    if status["running"]:
        print(f"\n[Status] Service already running (PID {status['pid']})")
        print("[Status] Stop with: calyx stop\n")
        return 0
    
    # Run quick checks
    if not args.skip_checks:
        print("\n[Doctor] Running health checks...")
        results = run_all_checks()
        
        if not results["healthy"]:
            print(format_doctor_report(results))
            print("[Doctor] Fix issues before starting, or use --skip-checks\n")
            return 1
        
        print(f"[Doctor] All {results['total']} checks passed\n")
    
    # Start
    background = getattr(args, 'background', False)
    host = getattr(args, 'host', '127.0.0.1')
    port = getattr(args, 'port', 8420)
    
    mode = "background" if background else "foreground"
    print(f"[Start] Starting service in {mode} mode...")
    print(f"[Start] URL: http://{host}:{port}\n")
    
    result = start_service(host=host, port=port, background=background)
    
    if result["success"]:
        if background:
            print(f"[Start] {result['message']}")
            print(f"[Start] Stop with: calyx stop")
        return 0
    else:
        print(f"[Error] {result['message']}")
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop the Station Calyx service."""
    status = get_service_status()
    
    if not status["running"]:
        print("\n[Status] Service is not running\n")
        return 0
    
    print(f"\n[Status] Service running (PID {status['pid']})")
    print("[Stop] Stopping service...")
    
    result = stop_service()
    
    if result["success"]:
        print(f"[Stop] {result['message']}\n")
        return 0
    else:
        print(f"[Error] {result['message']}\n")
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run health checks."""
    print("\n[Doctor] Running health checks...")
    results = run_all_checks()
    print(format_doctor_report(results))
    
    return 0 if results["healthy"] else 1


def cmd_assess(args: argparse.Namespace) -> int:
    """
    Generate human-readable system assessment.
    
    Uses the Human Translation Layer to convert evidence into plain-language.
    """
    from station_calyx.agents.human_translation import generate_human_assessment
    
    recent = args.recent
    
    print(f"Loading last {recent} events...")
    events = load_recent_events(recent)
    
    if not events:
        print("No events found. Run `calyx snapshot` first to generate some data.")
        return 1
    
    print(f"Generating human assessment from {len(events)} events...\n")
    
    # Generate assessment using human translation layer
    assessment = generate_human_assessment(events, recent)
    
    if hasattr(args, 'json') and args.json:
        # JSON output
        print(json.dumps(assessment.to_dict(), indent=2))
    else:
        # Plain language output
        print(assessment.to_plain_language())
    
    # Save to file if requested
    if hasattr(args, 'save') and args.save:
        config = get_config()
        summaries_dir = config.summaries_dir
        summaries_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Save markdown
        md_path = summaries_dir / f"assessment_{timestamp}.md"
        md_path.write_text(assessment.to_plain_language(), encoding="utf-8")
        
        # Save JSON
        json_path = summaries_dir / f"assessment_{timestamp}.json"
        json_path.write_text(json.dumps(assessment.to_dict(), indent=2), encoding="utf-8")
        
        print(f"\nAssessment saved to:")
        print(f"  {md_path}")
        print(f"  {json_path}")
    
    return 0


def cmd_ingest_evidence(args: argparse.Namespace) -> int:
    """
    Ingest evidence envelopes from JSONL file.
    
    This is the CLI interface for Node Evidence Relay v0.
    Reads envelopes, validates, and appends to per-node evidence stores.
    """
    from station_calyx.evidence.store import ingest_jsonl_file
    from station_calyx.schemas.evidence_envelope_v1 import (
        EvidenceEnvelopeV1,
        validate_envelope,
    )
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
    
    if not file_path.suffix == ".jsonl":
        print(f"Warning: Expected .jsonl file, got {file_path.suffix}")
    
    print(f"\n[Ingest] Reading evidence bundle: {file_path.name}")
    
    # Count lines for preview
    with open(file_path, "r", encoding="utf-8") as f:
        line_count = sum(1 for line in f if line.strip())
    
    print(f"[Ingest] Found {line_count} envelope(s) in file")
    
    # Dry-run mode: validate only
    if hasattr(args, 'dry_run') and args.dry_run:
        print("\n[Dry-Run] Validating envelopes...")
        
        valid_count = 0
        invalid_count = 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    env_dict = json.loads(line)
                    envelope = EvidenceEnvelopeV1.from_dict(env_dict)
                    is_valid, errors = validate_envelope(envelope)
                    
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                        print(f"  Line {i}: INVALID - {'; '.join(errors[:2])}")
                except Exception as e:
                    invalid_count += 1
                    print(f"  Line {i}: PARSE ERROR - {str(e)[:50]}")
        
        print(f"\n[Dry-Run] Results: {valid_count} valid, {invalid_count} invalid")
        return 0 if invalid_count == 0 else 1
    
    # Actual ingest
    print("[Ingest] Processing...")
    summary = ingest_jsonl_file(file_path)
    
    print(f"\n[Ingest] Results:")
    print(f"  Accepted: {summary.accepted_count}")
    print(f"  Rejected: {summary.rejected_count}")
    
    if summary.rejection_reasons:
        print(f"\n[Ingest] Rejection reasons:")
        for reason in summary.rejection_reasons[:5]:
            print(f"  - {reason}")
        if len(summary.rejection_reasons) > 5:
            print(f"  ... and {len(summary.rejection_reasons) - 5} more")
    
    if summary.accepted_count > 0:
        print(f"\n? Successfully ingested {summary.accepted_count} envelope(s)")
    
    return 0 if summary.rejected_count == 0 else 1


def cmd_nodes(args: argparse.Namespace) -> int:
    """List known evidence nodes."""
    from station_calyx.evidence.store import get_known_nodes, load_ingest_state
    
    nodes = get_known_nodes()
    
    if not nodes:
        print("\n[Nodes] No evidence nodes found.")
        print("  Ingest evidence with: calyx ingest <path_to_bundle.jsonl>")
        return 0
    
    if hasattr(args, 'json') and args.json:
        # JSON output
        result = {}
        for node_id in nodes:
            state = load_ingest_state(node_id)
            result[node_id] = state.to_dict()
        print(json.dumps(result, indent=2))
    else:
        # Tabular format
        print(f"\n{'='*70}")
        print(f"Known Evidence Nodes ({len(nodes)})")
        print(f"{'='*70}")
        print(f"{'Node ID':<30} {'Last Seq':<10} {'Envelopes':<12} {'Last Ingested':<20}")
        print(f"{'-'*70}")
        
        for node_id in nodes:
            state = load_ingest_state(node_id)
            last_ingested = state.last_ingested_at[:19] if state.last_ingested_at else "Never"
            
            # Truncate long node IDs
            display_id = node_id[:28] + ".." if len(node_id) > 30 else node_id
            
            print(f"{display_id:<30} {state.last_seq:<10} {state.total_envelopes:<12} {last_ingested:<20}")
        
        print(f"{'='*70}\n")
    
    return 0


def cmd_export_evidence(args: argparse.Namespace) -> int:
    """
    Export evidence bundle for relay transfer.
    
    Creates a JSONL bundle containing evidence envelopes for transfer
    to another Station Calyx node.
    """
    from station_calyx.evidence.export import (
        export_evidence,
        get_export_status,
    )
    
    # Status only mode
    if hasattr(args, 'status') and args.status:
        status = get_export_status()
        print(f"\n{'='*60}")
        print("Evidence Export Status")
        print(f"{'='*60}")
        print(f"Node ID:      {status['node_id']}")
        print(f"Node Name:    {status['node_name']}")
        print(f"Last Seq:     {status['last_exported_seq']}")
        print(f"Last Export:  {status['last_export_at'] or 'Never'}")
        print(f"Total Exports: {status['total_exports']}")
        print(f"Export Dir:   {status['export_dir']}")
        print(f"{'='*60}\n")
        return 0
    
    # Export
    recent = getattr(args, 'recent', 1000)
    include_all = getattr(args, 'include_all', False)
    
    print(f"\n[Export] Creating evidence bundle...")
    print(f"  Recent events: {recent}")
    print(f"  Include all: {include_all}")
    
    result = export_evidence(recent=recent, include_all=include_all)
    
    if result.success:
        print(f"\n[Export] Bundle created successfully!")
        print(f"  Path: {result.bundle_path}")
        print(f"  Envelopes: {result.envelope_count}")
        print(f"  Seq range: {result.seq_range[0]} - {result.seq_range[1]}")
        print(f"\n  Transfer this file to the receiving node and run:")
        print(f"    calyx ingest {result.bundle_path.name}")
        return 0
    else:
        print(f"\n[Export] Failed: {result.error}")
        return 1


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="calyx",
        description="Station Calyx Ops Reflector CLI (v1.7 - Node Evidence Relay)",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # status
    status_parser = subparsers.add_parser("status", help="Show service status")
    status_parser.add_argument("--human", action="store_true", help="Show human-friendly status")
    status_parser.add_argument("--refresh", action="store_true", help="Regenerate status (with --human)")
    status_parser.set_defaults(func=cmd_status)
    
    # snapshot
    snapshot_parser = subparsers.add_parser("snapshot", help="Capture system snapshot")
    snapshot_parser.add_argument("--json", action="store_true", help="Output as JSON")
    snapshot_parser.add_argument("--no-log", action="store_true", help="Don't log to evidence")
    snapshot_parser.set_defaults(func=cmd_snapshot)
    
    # reflect
    reflect_parser = subparsers.add_parser("reflect", help="Run reflection on recent events")
    reflect_parser.add_argument("--recent", type=int, default=100, help="Number of recent events to analyze")
    reflect_parser.add_argument("--json", action="store_true", help="Output as JSON")
    reflect_parser.set_defaults(func=cmd_reflect)
    
    # ingest (legacy - single event from JSON file)
    # Kept for backwards compatibility
    ingest_legacy_parser = subparsers.add_parser("ingest-event", help="Ingest single event from JSON file")
    ingest_legacy_parser.add_argument("--file", required=True, help="Path to event file (JSON)")
    ingest_legacy_parser.set_defaults(func=cmd_ingest)
    
    # events
    events_parser = subparsers.add_parser("events", help="List recent events")
    events_parser.add_argument("--recent", type=int, default=20, help="Number of events to show")
    events_parser.set_defaults(func=cmd_events)
    
    # intent (with subcommands)
    intent_parser = subparsers.add_parser("intent", help="Manage user intent")
    intent_subparsers = intent_parser.add_subparsers(dest="intent_command", help="Intent commands")
    
    # intent set
    set_parser = intent_subparsers.add_parser("set", help="Set user intent")
    set_parser.add_argument("--profile", required=True, 
                           help="Profile: STABILITY_FIRST, PERFORMANCE_SENSITIVE, RESOURCE_CONSTRAINED, DEVELOPER_WORKSTATION")
    set_parser.add_argument("--desc", default="", help="Description of intent")
    set_parser.set_defaults(func=cmd_intent_set)
    
    # intent show
    show_parser = intent_subparsers.add_parser("show", help="Show current intent")
    show_parser.set_defaults(func=cmd_intent_show)
    
    # advise
    advise_parser = subparsers.add_parser("advise", help="Generate advisory based on intent")
    advise_parser.add_argument("--recent", type=int, default=100, help="Number of recent events")
    advise_parser.add_argument("--json", action="store_true", help="Output as JSON")
    advise_parser.set_defaults(func=cmd_advise)
    
    # trends
    trends_parser = subparsers.add_parser("trends", help="Show recent temporal trends")
    trends_parser.set_defaults(func=cmd_trends)
    
    # analyze (with temporal subcommand)
    analyze_parser = subparsers.add_parser("analyze", help="Run analysis")
    analyze_subparsers = analyze_parser.add_subparsers(dest="analyze_command", help="Analysis commands")
    
    # analyze temporal
    temporal_parser = analyze_subparsers.add_parser("temporal", help="Run temporal trend analysis")
    temporal_parser.add_argument("--recent", type=int, default=1000, help="Number of recent events to analyze")
    temporal_parser.add_argument("--json", action="store_true", help="Output as JSON")
    temporal_parser.set_defaults(func=cmd_analyze_temporal)
    
    # notify (test)
    notify_parser = subparsers.add_parser("notify", help="Notification commands")
    notify_parser.add_argument("notify_command", choices=["test"], help="Notification command")
    notify_parser.set_defaults(func=cmd_notify_test)
    
    # notifications
    notifications_parser = subparsers.add_parser("notifications", help="Show recent notifications")
    notifications_parser.set_defaults(func=cmd_notifications)
    
    # start
    start_parser = subparsers.add_parser("start", help="Start the service")
    start_parser.add_argument("--host", default="127.0.0.1", help="Host to bind the service")
    start_parser.add_argument("--port", type=int, default=8420, help="Port to bind the service")
    start_parser.add_argument("--background", action="store_true", help="Start in background mode")
    start_parser.add_argument("--skip-checks", action="store_true", help="Skip health checks")
    start_parser.set_defaults(func=cmd_start)
    
    # stop
    stop_parser = subparsers.add_parser("stop", help="Stop the service")
    stop_parser.set_defaults(func=cmd_stop)
    
    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="Run health checks")
    doctor_parser.set_defaults(func=cmd_doctor)
    
    # assess - human translation layer
    assess_parser = subparsers.add_parser("assess", help="Generate human-readable system assessment")
    assess_parser.add_argument("--recent", type=int, default=500, help="Number of recent events to analyze")
    assess_parser.add_argument("--json", action="store_true", help="Output as JSON")
    assess_parser.add_argument("--save", action="store_true", help="Save to summaries directory")
    assess_parser.add_argument("--node", type=str, default="local", help="Node to assess (local|all|<node_id>)")
    assess_parser.set_defaults(func=cmd_assess)
    
    # ingest - evidence relay
    ingest_evidence_parser = subparsers.add_parser("ingest", help="Ingest evidence from file")
    ingest_evidence_parser.add_argument("file", type=str, help="Path to .jsonl evidence bundle")
    ingest_evidence_parser.add_argument("--dry-run", action="store_true", help="Validate only, don't ingest")
    ingest_evidence_parser.set_defaults(func=cmd_ingest_evidence)
    
    # nodes - list known nodes
    nodes_parser = subparsers.add_parser("nodes", help="List known evidence nodes")
    nodes_parser.add_argument("--json", action="store_true", help="Output as JSON")
    nodes_parser.set_defaults(func=cmd_nodes)
    
    # export-evidence - create bundle for relay
    export_parser = subparsers.add_parser("export-evidence", help="Export evidence bundle for relay transfer")
    export_parser.add_argument("--recent", type=int, default=1000, help="Number of recent events to consider")
    export_parser.add_argument("--all", action="store_true", dest="include_all", help="Export all events (ignore last export)")
    export_parser.add_argument("--status", action="store_true", help="Show export status only")
    export_parser.set_defaults(func=cmd_export_evidence)
    
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Handle intent subcommands
    if args.command == "intent" and not hasattr(args, 'func'):
        intent_parser.print_help()
        return 0
    
    # Handle analyze subcommands
    if args.command == "analyze" and not hasattr(args, 'func'):
        analyze_parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
