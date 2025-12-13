#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telemetry Evidence Bridge - Hook telemetry snapshots into evidence journal.

[CBO Governance]: This bridge wraps existing compute_telemetry snapshots
in EvidenceEnvelopeV1 and writes them to the evidence journal. It does NOT
change telemetry semantics - only wraps and logs for distributed truth capture.

Can run standalone or be imported by other telemetry collectors.

Usage:
    # Standalone: capture and journal telemetry once
    python -u tools/telemetry_evidence_bridge.py
    
    # Loop mode: continuous capture
    python -u tools/telemetry_evidence_bridge.py --interval 30
    
    # Import and use programmatically
    from tools.telemetry_evidence_bridge import capture_telemetry_snapshot
    capture_telemetry_snapshot()
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from station_calyx.evidence import append_evidence, EvidenceType

# Import telemetry computation
from tools.compute_telemetry import run_once as compute_telemetry_once


def capture_telemetry_snapshot() -> Dict[str, Any]:
    """
    Capture telemetry snapshot and write to evidence journal.

    [CBO Governance]: This function wraps telemetry in evidence envelope
    without modifying the original telemetry semantics. The envelope provides:
    - Node attribution
    - Chronological sequence
    - Hash chain integrity

    Returns:
        Telemetry state dict (as returned by compute_telemetry)
    """
    # Run telemetry computation (existing behavior unchanged)
    state = compute_telemetry_once()
    
    # Wrap in evidence envelope and journal
    envelope = append_evidence(
        evidence_type=EvidenceType.TELEMETRY_SNAPSHOT,
        payload=state,
        tags=["telemetry", "system_health", "agent_state"],
        source="telemetry_evidence_bridge",
    )
    
    # Log summary
    active = state.get("active_count", 0)
    drift = state.get("drift", {}).get("agent1_scheduler", {}).get("latest")
    drift_str = f"{drift:.3f}" if drift is not None else "N/A"
    
    print(f"[EVIDENCE] seq={envelope.seq} | active={active} | drift={drift_str} | hash={envelope.envelope_hash[:12]}...")
    
    return state


def capture_agent_heartbeat(agent_name: str, heartbeat_data: Dict[str, Any]) -> None:
    """
    Capture individual agent heartbeat as evidence.

    [CBO Governance]: Use this for per-agent heartbeat evidence when
    finer granularity is needed than telemetry snapshots.
    
    Args:
        agent_name: Name of agent (e.g., "agent1", "scheduler")
        heartbeat_data: Heartbeat data dict
    """
    envelope = append_evidence(
        evidence_type=EvidenceType.AGENT_HEARTBEAT,
        payload={
            "agent": agent_name,
            "heartbeat": heartbeat_data,
            "captured_at": datetime.now().isoformat(),
        },
        tags=["heartbeat", agent_name],
        source="telemetry_evidence_bridge",
    )
    
    status = heartbeat_data.get("status", "unknown")
    print(f"[EVIDENCE] Heartbeat: {agent_name} status={status} seq={envelope.seq}")


def run_loop(interval: float) -> None:
    """
    Run telemetry capture in loop.
    
    Args:
        interval: Seconds between captures
    """
    print(f"[INFO] Telemetry Evidence Bridge started")
    print(f"[INFO] Interval: {interval}s")
    print(f"[INFO] Press Ctrl+C to stop\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            capture_telemetry_snapshot()
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n[INFO] Stopped after {iteration} captures")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bridge telemetry snapshots into evidence journal"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Run in loop with this interval in seconds (0 = one-shot)",
    )
    
    args = parser.parse_args(argv)
    
    try:
        if args.interval > 0:
            run_loop(args.interval)
        else:
            capture_telemetry_snapshot()
        return 0
    except Exception as e:
        print(f"[ERROR] Bridge failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
