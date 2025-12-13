#!/usr/bin/env python3
"""
Coordinator CLI (coordinatorctl) - Command-line interface for Station Calyx Coordinator

Usage:
  python tools/coordinatorctl.py status
  python tools/coordinatorctl.py pulse
  python tools/coordinatorctl.py add-intent "description" --origin human --priority 60
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from calyx.cbo.coordinator import Coordinator


def cmd_status(coordinator: Coordinator) -> int:
    """Show coordinator status"""
    status = coordinator.get_status()
    
    print("\n[COORDINATOR STATUS]")
    print("=" * 60)
    print(f"Intents Queued: {status['intents_count']}")
    print(f"Autonomy Mode: {status['autonomy_mode']}")
    print(f"\nConfidence Scores:")
    for capability, score in status['confidence'].items():
        print(f"  {capability}: {score:.2f}")
    print("=" * 60)
    
    return 0


def cmd_pulse(coordinator: Coordinator) -> int:
    """Execute one coordinator pulse"""
    report = coordinator.pulse()
    
    print("\n[COORDINATOR PULSE]")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Events Ingested: {report['events_ingested']}")
    print(f"Guardrails OK: {report['guardrails']['ok']}")
    if report['guardrails']['violations']:
        print(f"Violations: {', '.join(report['guardrails']['violations'])}")
    print(f"Intents Queued: {report['intents_queued']}")
    print(f"Top Priorities: {len(report['top_intents'])}")
    print(f"Autonomy Mode: {report['autonomy_mode']}")
    
    if report.get('stalls'):
        print(f"\nStalls Detected: {len(report['stalls'])}")
        for stall in report['stalls']:
            print(f"  Intent {stall['intent_id']}: {stall['elapsed_minutes']:.1f} minutes")
    
    if report.get('active_escalations', 0) > 0:
        print(f"\nActive Escalations: {report['active_escalations']}")
    
    if report.get('executions'):
        print(f"\nExecutions: {len(report['executions'])}")
        for exec_data in report['executions']:
            intent_id = exec_data['intent_id']
            result = exec_data['result']
            print(f"  Intent {intent_id}: {result.get('status', 'unknown')}")
            if result.get('manifest_id'):
                print(f"    Manifest: {result['manifest_id']}")
            if result.get('domain'):
                print(f"    Domain: {result['domain']}")
            if result.get('error'):
                print(f"    Error: {result['error']}")
    
    print("=" * 60)
    
    return 0


def cmd_add_intent(coordinator: Coordinator, description: str, **kwargs) -> int:
    """Add a new intent"""
    intent_id = coordinator.add_intent(
        description=description,
        origin=kwargs.get('origin', 'human'),
        required_capabilities=kwargs.get('capabilities', []),
        desired_outcome=kwargs.get('outcome', ''),
        priority_hint=kwargs.get('priority', 50),
        autonomy_required=kwargs.get('autonomy', 'suggest')
    )
    
    if intent_id:
        print(f"[OK] Intent added: {intent_id}")
        print(f"     Description: {description}")
    else:
        print("[INFO] Intent was duplicate (not added)")
    
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Station Calyx Coordinator CLI")
    subparsers = ap.add_subparsers(dest='command', help='Command to execute')
    
    # Status command
    subparsers.add_parser('status', help='Show coordinator status')
    
    # Pulse command
    subparsers.add_parser('pulse', help='Execute one coordinator pulse')
    
    # Add intent command
    intent_parser = subparsers.add_parser('add-intent', help='Add a new intent')
    intent_parser.add_argument('description', help='Intent description')
    intent_parser.add_argument('--origin', default='human', help='Intent origin')
    intent_parser.add_argument('--capabilities', nargs='+', default=[], help='Required capabilities')
    intent_parser.add_argument('--outcome', default='', help='Desired outcome')
    intent_parser.add_argument('--priority', type=int, default=50, help='Priority hint (0-100)')
    intent_parser.add_argument('--autonomy', default='suggest', help='Autonomy required')
    
    args = ap.parse_args(argv)
    
    if not args.command:
        ap.print_help()
        return 1
    
    # Initialize coordinator
    coordinator = Coordinator(ROOT)
    
    # Execute command
    if args.command == 'status':
        return cmd_status(coordinator)
    elif args.command == 'pulse':
        return cmd_pulse(coordinator)
    elif args.command == 'add-intent':
        return cmd_add_intent(
            coordinator,
            args.description,
            origin=args.origin,
            capabilities=args.capabilities,
            outcome=args.outcome,
            priority=args.priority,
            autonomy=args.autonomy
        )
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

