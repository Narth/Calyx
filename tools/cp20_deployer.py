#!/usr/bin/env python3
"""
CP20 — The Deployer
Deployment & Release Management Agent
Part of Station Calyx Deployment Team
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
LOCK = OUT / "cp20.lock"
DEPLOYMENTS_DIR = ROOT / "deployments"

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


def _write_hb(phase: str, status: str = "running", our: Optional[Dict[str, Any]] = None) -> None:
    """Write heartbeat"""
    try:
        payload: Dict[str, Any] = {
            "name": "cp20",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": "1.0.0",
        }
        if our:
            payload.update(our)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def cleanup_stale_locks() -> Dict[str, Any]:
    """Clean up stale lock files"""
    cleanup_result = {
        "locks_removed": 0,
        "locks_kept": 0,
        "errors": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    STALE_THRESHOLD = 300  # 5 minutes
    
    for lock_file in OUT.glob("*.lock"):
        try:
            lock_data = _read_json(lock_file)
            if lock_data:
                age = time.time() - lock_data.get("ts", 0)
                
                # Keep recent locks
                if age < STALE_THRESHOLD:
                    cleanup_result["locks_kept"] += 1
                    continue
                
                # Check if agent is actually running
                agent_name = lock_file.stem
                if agent_name in ["cbo", "scheduler", "llm_ready", "navigator", "svf", "triage", "sysint"]:
                    # Keep critical locks
                    cleanup_result["locks_kept"] += 1
                    continue
                
                # Remove stale lock
                try:
                    lock_file.unlink()
                    cleanup_result["locks_removed"] += 1
                except Exception as e:
                    cleanup_result["errors"].append(str(e))
                    
        except Exception as e:
            cleanup_result["errors"].append(str(e))
    
    return cleanup_result


def deploy_cleanup_operation() -> Dict[str, Any]:
    """Deploy cleanup operation"""
    cleanup_result = cleanup_stale_locks()
    
    # Check if should report
    should_send = True
    if SVF_AVAILABLE:
        should_send = should_report("cp20", trigger_event="cleanup_deployed")
    
    # Report if needed
    if should_send and cleanup_result["locks_removed"] > 0:
        if SVF_AVAILABLE:
            send_message(
                sender="cp20",
                message=f"🧹 Cleanup deployed: Removed {cleanup_result['locks_removed']} stale lock(s)",
                channel="standard",
                priority="medium",
                context=cleanup_result
            )
            log_communication("cp20", "deploy", "standard", f"{cleanup_result['locks_removed']} locks removed", "success")
    
    # Increment cycle
    if SVF_AVAILABLE:
        increment_cycle("cp20")
    
    return cleanup_result


def check_pending_queries() -> None:
    """Check and respond to pending queries"""
    if not SVF_AVAILABLE:
        return
    
    queries = get_pending_queries("cp20")
    
    for query in queries:
        if query.get("to") == "cp20":
            question = query.get("question", "")
            
            if "deploy" in question.lower() or "cleanup" in question.lower():
                # Check what needs deploying
                result = cleanup_stale_locks()
                respond_to_query(
                    query_id=query.get("query_id"),
                    responder="cp20",
                    answer=f"Ready to deploy: {result['locks_removed']} stale lock(s) identified",
                    data=result
                )
                log_communication("cp20", "respond", query.get("from"), "Deployment readiness", "success")


def main():
    parser = argparse.ArgumentParser(description="CP20 Deployer - Deployment Agent")
    parser.add_argument("--interval", type=float, default=3600.0, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--cleanup", action="store_true", help="Run cleanup operation")
    
    args = parser.parse_args()
    
    # Register with SVF v2.0
    if SVF_AVAILABLE:
        register_agent(
            agent_name="cp20",
            capabilities=["deployment", "release_management", "automation"],
            data_sources=["deploy/", "config.yaml"],
            update_frequency="3600s",
            contact_policy="respond_to_queries"
        )
        
        announce_presence(
            agent_name="cp20",
            version="1.0.0",
            status="running",
            capabilities=["deployment", "release_management", "automation"],
            uptime_seconds=0.0
        )
    
    print("CP20 Deployer started")
    
    def _shutdown(*args):
        _write_hb("shutdown", status="done")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    try:
        while True:
            # Check pending queries
            check_pending_queries()
            
            # Run cleanup if requested
            if args.cleanup or args.once:
                result = deploy_cleanup_operation()
                status_msg = f"🧹 Cleanup: {result['locks_removed']} removed, {result['locks_kept']} kept"
            else:
                status_msg = "Ready for deployment operations"
            
            _write_hb("ready", status="running", our={
                "status_message": status_msg
            })
            
            if args.once:
                break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()

