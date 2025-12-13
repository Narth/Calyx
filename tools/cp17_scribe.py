#!/usr/bin/env python3
"""
CP17 — The Scribe
Documentation & Knowledge Management Agent
Part of Station Calyx Quality & Documentation Team
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
DOCS = ROOT / "docs"
LOCK = OUT / "cp17.lock"

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
            "name": "cp17",
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


def scan_documentation_status() -> Dict[str, Any]:
    """Scan documentation for freshness and completeness"""
    docs_status = {
        "total_files": 0,
        "recent_updates": 0,
        "stale_files": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Scan docs directory
    if DOCS.exists():
        for doc_file in DOCS.rglob("*.md"):
            docs_status["total_files"] += 1
            age = time.time() - doc_file.stat().st_mtime
            
            if age < 604800:  # Updated in last week
                docs_status["recent_updates"] += 1
            elif age > 2592000:  # Older than 30 days
                docs_status["stale_files"].append({
                    "file": str(doc_file.relative_to(ROOT)),
                    "age_days": age / 86400
                })
    
    return docs_status


def generate_changelog() -> Dict[str, Any]:
    """Generate changelog from recent activity"""
    # This would scan reports/ and outgoing/shared_logs/ for recent changes
    changelog = {
        "period": "last_24h",
        "entries": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # TODO: Implement changelog generation
    return changelog


def check_pending_queries() -> None:
    """Check and respond to pending queries"""
    if not SVF_AVAILABLE:
        return
    
    queries = get_pending_queries("cp17")
    
    for query in queries:
        if query.get("to") == "cp17":
            question = query.get("question", "")
            
            if "documentation" in question.lower() or "docs" in question.lower():
                status = scan_documentation_status()
                respond_to_query(
                    query_id=query.get("query_id"),
                    responder="cp17",
                    answer=f"Documentation status: {status['total_files']} files, {status['recent_updates']} recent updates",
                    data=status
                )
                log_communication("cp17", "respond", query.get("from"), "Docs status", "success")


def run_doc_cycle() -> Dict[str, Any]:
    """Run documentation cycle"""
    status = scan_documentation_status()
    
    # Check if should report
    should_send = True
    if SVF_AVAILABLE:
        should_send = should_report("cp17", trigger_event="doc_scan")
    
    # Check pending queries
    check_pending_queries()
    
    # Report if needed
    if should_send and status.get("stale_files"):
        stale_count = len(status.get("stale_files", []))
        
        if SVF_AVAILABLE:
            send_message(
                sender="cp17",
                message=f"📝 Documentation update: {stale_count} stale file(s) detected",
                channel="casual",
                priority="low",
                context=status
            )
            log_communication("cp17", "doc_scan", "casual", f"{stale_count} stale files", "success")
    
    # Increment cycle
    if SVF_AVAILABLE:
        increment_cycle("cp17")
    
    return status


def main():
    parser = argparse.ArgumentParser(description="CP17 Scribe - Documentation Agent")
    parser.add_argument("--interval", type=float, default=600.0, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    # Register with SVF v2.0
    if SVF_AVAILABLE:
        register_agent(
            agent_name="cp17",
            capabilities=["documentation", "knowledge_extraction", "changelog_management"],
            data_sources=["docs/", "reports/", "outgoing/shared_logs/"],
            update_frequency="600s",
            contact_policy="respond_to_queries"
        )
        
        announce_presence(
            agent_name="cp17",
            version="1.0.0",
            status="running",
            capabilities=["documentation", "knowledge_extraction", "changelog_management"],
            uptime_seconds=0.0
        )
    
    print("CP17 Scribe started")
    
    def _shutdown(*args):
        _write_hb("shutdown", status="done")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    try:
        while True:
            status = run_doc_cycle()
            
            status_msg = f"📝 Docs: {status['total_files']} files, {status['recent_updates']} recent"
            
            _write_hb("scanning", status="running", extra={
                "status_message": status_msg,
                "summary": status
            })
            
            if args.once:
                break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()

