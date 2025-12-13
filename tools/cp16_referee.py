#!/usr/bin/env python3
"""
CP16 — The Referee
Conflict Resolution & Mediation Agent
Part of Station Calyx Coordination & Mediation Team
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
LOCK = OUT / "cp16.lock"

# SVF v2.0 imports
try:
    from tools.svf_query import create_query, get_pending_queries, respond_to_query
    from tools.svf_channels import send_message
    from tools.svf_registry import register_agent, get_agent_capabilities
    from tools.svf_handshake import announce_presence
    from tools.svf_frequency import should_report, increment_cycle
    from tools.svf_audit import log_communication
    SVF_AVAILABLE = True
except ImportError:
    SVF_AVAILABLE = False
    print("Warning: SVF v2.0 not available, running in compatibility mode")


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON file"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error writing {path}: {e}")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read JSON file"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    """Write heartbeat"""
    try:
        payload: Dict[str, Any] = {
            "name": "cp16",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": "1.0.0",
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def detect_conflicts() -> List[Dict[str, Any]]:
    """Detect resource conflicts and agent contention"""
    conflicts = []
    
    # Check for stale locks (resource contention indicator)
    lock_files = list(OUT.glob("*.lock"))
    stale_agents = []
    
    for lock_file in lock_files:
        try:
            lock_data = _read_json(lock_file)
            if lock_data:
                age = time.time() - lock_data.get("ts", 0)
                if age > 300:  # Older than 5 minutes
                    stale_agents.append({
                        "agent": lock_file.stem,
                        "age_seconds": age,
                        "status": lock_data.get("status", "unknown")
                    })
        except Exception:
            continue
    
    if len(stale_agents) > 3:
        conflicts.append({
            "type": "stale_agents",
            "count": len(stale_agents),
            "agents": stale_agents,
            "severity": "medium"
        })
    
    # Check for multiple agents with same data source (contention)
    cbo_lock = OUT / "cbo.lock"
    if cbo_lock.exists():
        cbo_data = _read_json(cbo_lock)
        if cbo_data:
            cpu_pct = cbo_data.get("metrics", {}).get("cpu_pct", 0)
            if cpu_pct > 90:
                conflicts.append({
                    "type": "resource_exhaustion",
                    "resource": "cpu",
                    "usage": cpu_pct,
                    "severity": "high"
                })
    
    return conflicts


def mediate_conflict(conflict: Dict[str, Any]) -> Dict[str, Any]:
    """Mediate a detected conflict"""
    conflict_type = conflict.get("type")
    
    if conflict_type == "stale_agents":
        return {
            "resolution": "recommend_restart",
            "agents": conflict.get("agents", []),
            "priority": "medium"
        }
    elif conflict_type == "resource_exhaustion":
        return {
            "resolution": "throttle_dispatch",
            "resource": conflict.get("resource"),
            "priority": "high"
        }
    
    return {
        "resolution": "monitor",
        "priority": "low"
    }


def check_pending_queries() -> None:
    """Check and respond to pending queries"""
    if not SVF_AVAILABLE:
        return
    
    queries = get_pending_queries("cp16")
    
    for query in queries:
        if query.get("to") == "cp16":
            question = query.get("question", "")
            
            if "conflict" in question.lower() or "contention" in question.lower():
                conflicts = detect_conflicts()
                resolution = {"conflicts": conflicts, "count": len(conflicts)}
                
                respond_to_query(
                    query_id=query.get("query_id"),
                    responder="cp16",
                    answer=f"Detected {len(conflicts)} conflict(s)",
                    data=resolution
                )
                log_communication("cp16", "respond", query.get("from"), "Conflict status", "success")


def run_conflict_monitoring() -> Dict[str, Any]:
    """Run conflict monitoring cycle"""
    conflicts = detect_conflicts()
    
    # Check if should report
    should_send = True
    if SVF_AVAILABLE:
        should_send = should_report("cp16", trigger_event="conflict_detected" if conflicts else None)
    
    # Check pending queries
    check_pending_queries()
    
    # Mediate conflicts
    resolutions = []
    for conflict in conflicts:
        resolution = mediate_conflict(conflict)
        resolutions.append(resolution)
    
    # Report if needed
    if should_send and conflicts:
        high_severity = [c for c in conflicts if c.get("severity") == "high"]
        
        if high_severity:
            priority = "urgent"
            channel = "urgent"
        else:
            priority = "medium"
            channel = "standard"
        
        if SVF_AVAILABLE:
            send_message(
                sender="cp16",
                message=f"⚠️ Conflict detected: {len(conflicts)} issue(s) found",
                channel=channel,
                priority=priority,
                context={"conflicts": conflicts, "resolutions": resolutions}
            )
            log_communication("cp16", "conflict", channel, f"{len(conflicts)} conflicts", "success")
    
    # Increment cycle
    if SVF_AVAILABLE:
        increment_cycle("cp16")
    
    return {
        "conflicts": conflicts,
        "resolutions": resolutions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="CP16 Referee - Conflict Resolution Agent")
    parser.add_argument("--interval", type=float, default=120.0, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    # Register with SVF v2.0
    if SVF_AVAILABLE:
        register_agent(
            agent_name="cp16",
            capabilities=["conflict_resolution", "mediation", "arbitration"],
            data_sources=["outgoing/*.lock", "logs/system_snapshots.jsonl", "logs/agent_metrics.csv"],
            update_frequency="120s",
            contact_policy="respond_to_queries"
        )
        
        announce_presence(
            agent_name="cp16",
            version="1.0.0",
            status="running",
            capabilities=["conflict_resolution", "mediation", "arbitration"],
            uptime_seconds=0.0
        )
    
    print("CP16 Referee started")
    
    def _shutdown(*args):
        _write_hb("shutdown", status="done")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    try:
        while True:
            result = run_conflict_monitoring()
            
            if result["conflicts"]:
                status_msg = f"⚠️ {len(result['conflicts'])} conflict(s) detected"
                status = "warn"
            else:
                status_msg = "System harmony: No conflicts"
                status = "running"
            
            _write_hb("monitoring", status=status, extra={
                "status_message": status_msg,
                "summary": result
            })
            
            if args.once:
                break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()

