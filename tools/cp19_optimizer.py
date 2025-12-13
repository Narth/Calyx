#!/usr/bin/env python3
"""
CP19 — The Optimizer
Resource Optimization Agent
Part of Station Calyx Analytics & Optimization Team
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
LOCK = OUT / "cp19.lock"

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
            "name": "cp19",
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


def analyze_resource_usage() -> Dict[str, Any]:
    """Analyze current resource usage and optimization opportunities"""
    analysis = {
        "opportunities": [],
        "recommendations": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check CBO lock for resource info
    cbo_lock = OUT / "cbo.lock"
    if cbo_lock.exists():
        cbo_data = _read_json(cbo_lock)
        if cbo_data:
            cpu_pct = cbo_data.get("metrics", {}).get("cpu_pct", 0)
            mem_pct = cbo_data.get("metrics", {}).get("mem_used_pct", 0)
            
            # CPU optimization opportunity
            if cpu_pct > 80:
                analysis["opportunities"].append({
                    "resource": "cpu",
                    "current": cpu_pct,
                    "severity": "high" if cpu_pct > 90 else "medium",
                    "recommendation": "throttle_agent_dispatch"
                })
            
            # Memory optimization opportunity
            if mem_pct > 75:
                analysis["opportunities"].append({
                    "resource": "memory",
                    "current": mem_pct,
                    "severity": "high" if mem_pct > 85 else "medium",
                    "recommendation": "cleanup_stale_data"
                })
    
    return analysis


def check_pending_queries() -> None:
    """Check and respond to pending queries"""
    if not SVF_AVAILABLE:
        return
    
    queries = get_pending_queries("cp19")
    
    for query in queries:
        if query.get("to") == "cp19":
            question = query.get("question", "")
            
            if "optimization" in question.lower() or "resource" in question.lower():
                analysis = analyze_resource_usage()
                respond_to_query(
                    query_id=query.get("query_id"),
                    responder="cp19",
                    answer=f"Found {len(analysis['opportunities'])} optimization opportunity/ies",
                    data=analysis
                )
                log_communication("cp19", "respond", query.get("from"), "Optimization status", "success")


def run_optimization_cycle() -> Dict[str, Any]:
    """Run optimization cycle"""
    analysis = analyze_resource_usage()
    
    # Check if should report
    should_send = True
    if SVF_AVAILABLE:
        should_send = should_report("cp19", trigger_event="optimization_opportunity" if analysis["opportunities"] else None)
    
    # Check pending queries
    check_pending_queries()
    
    # Report if needed
    if should_send and analysis["opportunities"]:
        high_severity = [o for o in analysis["opportunities"] if o.get("severity") == "high"]
        
        if high_severity:
            priority = "high"
            channel = "standard"
        else:
            priority = "medium"
            channel = "casual"
        
        if SVF_AVAILABLE:
            send_message(
                sender="cp19",
                message=f"🔧 Optimization: {len(analysis['opportunities'])} opportunity/ies found",
                channel=channel,
                priority=priority,
                context=analysis
            )
            log_communication("cp19", "optimization", channel, f"{len(analysis['opportunities'])} opportunities", "success")
    
    # Increment cycle
    if SVF_AVAILABLE:
        increment_cycle("cp19")
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="CP19 Optimizer - Resource Optimization Agent")
    parser.add_argument("--interval", type=float, default=300.0, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    # Register with SVF v2.0
    if SVF_AVAILABLE:
        register_agent(
            agent_name="cp19",
            capabilities=["resource_optimization", "capacity_planning", "efficiency_tuning"],
            data_sources=["logs/system_snapshots.jsonl", "outgoing/capacity.flags.json", "logs/enhanced_metrics.jsonl"],
            update_frequency="300s",
            contact_policy="respond_to_queries"
        )
        
        announce_presence(
            agent_name="cp19",
            version="1.0.0",
            status="running",
            capabilities=["resource_optimization", "capacity_planning", "efficiency_tuning"],
            uptime_seconds=0.0
        )
    
    print("CP19 Optimizer started")
    
    def _shutdown(*args):
        _write_hb("shutdown", status="done")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    try:
        while True:
            analysis = run_optimization_cycle()
            
            if analysis["opportunities"]:
                status_msg = f"🔧 {len(analysis['opportunities'])} optimization opportunity/ies"
                status = "running"
            else:
                status_msg = "Resources optimal"
                status = "running"
            
            _write_hb("optimizing", status=status, extra={
                "status_message": status_msg,
                "summary": analysis
            })
            
            if args.once:
                break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()

