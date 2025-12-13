#!/usr/bin/env python3
"""
SVF Agent Handshaking Protocol
Part of SVF v2.0 Phase 2 (implemented 2025-10-26)
Enables agents to announce presence and sync capabilities
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
HANDSHAKES_DIR = OUT / "handshakes"
REGISTRY_FILE = OUT / "agent_capabilities.json"
SHARED_LOGS = OUT / "shared_logs"


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


def announce_presence(agent_name: str, version: str, status: str,
                     capabilities: List[str], uptime_seconds: float = 0.0,
                     requested_sync: Optional[List[str]] = None) -> str:
    """
    Announce agent presence to Station
    
    Args:
        agent_name: Name of agent
        version: Agent version
        status: Current status
        capabilities: List of capabilities
        uptime_seconds: How long agent has been running
        requested_sync: Agents to sync with
        
    Returns:
        Handshake ID
    """
    handshake_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    handshake_data = {
        "handshake_id": handshake_id,
        "agent": agent_name,
        "version": version,
        "timestamp": timestamp,
        "status": status,
        "capabilities": capabilities,
        "uptime_seconds": uptime_seconds,
        "requested_sync": requested_sync or [],
        "handshake_type": "presence_announcement"
    }
    
    handshake_file = HANDSHAKES_DIR / f"{agent_name}_{timestamp.replace(':', '-')}.handshake.json"
    _write_json(handshake_file, handshake_data)
    
    # Update registry with presence info
    registry = _read_json(REGISTRY_FILE) or {}
    if agent_name not in registry:
        registry[agent_name] = {}
    
    registry[agent_name].update({
        "last_seen": timestamp,
        "status": status,
        "version": version,
        "uptime_seconds": uptime_seconds
    })
    _write_json(REGISTRY_FILE, registry)
    
    # Log handshake
    log_file = SHARED_LOGS / f"svf_handshake_{handshake_id}.md"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as f:
        f.write(f"# Agent Handshake: {agent_name}\n\n")
        f.write(f"**Handshake ID:** {handshake_id}\n")
        f.write(f"**Version:** {version}\n")
        f.write(f"**Status:** {status}\n")
        f.write(f"**Uptime:** {uptime_seconds:.1f}s\n")
        f.write(f"**Capabilities:** {', '.join(capabilities)}\n\n")
        if requested_sync:
            f.write(f"**Requested Sync:** {', '.join(requested_sync)}\n")
    
    return handshake_id


def sync_with_agent(source_agent: str, target_agent: str, sync_data: Dict[str, Any]) -> str:
    """
    Create a sync message for target agent
    
    Args:
        source_agent: Agent initiating sync
        target_agent: Agent to sync with
        sync_data: Data to sync
        
    Returns:
        Sync ID
    """
    sync_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    sync_data_full = {
        "sync_id": sync_id,
        "from": source_agent,
        "to": target_agent,
        "timestamp": timestamp,
        "data": sync_data,
        "handshake_type": "explicit_sync"
    }
    
    sync_file = HANDSHAKES_DIR / f"sync_{sync_id}.handshake.json"
    _write_json(sync_file, sync_data_full)
    
    return sync_id


def get_recent_handshakes(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent handshakes"""
    handshakes = []
    
    if not HANDSHAKES_DIR.exists():
        return handshakes
    
    for handshake_file in sorted(HANDSHAKES_DIR.glob("*.handshake.json"), 
                                key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            handshake = json.loads(handshake_file.read_text(encoding="utf-8"))
            handshakes.append(handshake)
        except Exception:
            continue
    
    return handshakes


def get_agent_handshakes(agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get handshakes for a specific agent"""
    all_handshakes = get_recent_handshakes(limit * 2)
    agent_handshakes = [h for h in all_handshakes if h.get("agent") == agent_name]
    return agent_handshakes[:limit]


def main():
    parser = argparse.ArgumentParser(description="SVF Agent Handshaking Protocol")
    parser.add_argument("--announce", action="store_true", help="Announce presence")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--version", help="Agent version")
    parser.add_argument("--status", help="Current status")
    parser.add_argument("--capabilities", nargs="+", help="Agent capabilities")
    parser.add_argument("--uptime", type=float, default=0.0, help="Uptime in seconds")
    parser.add_argument("--sync-with", nargs="+", help="Agents to sync with")
    
    parser.add_argument("--sync", action="store_true", help="Create sync message")
    parser.add_argument("--from", dest="from_agent", help="Source agent")
    parser.add_argument("--to", dest="to_agent", help="Target agent")
    parser.add_argument("--data", help="JSON data file")
    
    parser.add_argument("--get-recent", type=int, help="Get recent handshakes")
    parser.add_argument("--get-agent", help="Get handshakes for agent")
    
    args = parser.parse_args()
    
    # Handle non-agent operations first
    if args.get_recent:
        handshakes = get_recent_handshakes(args.get_recent)
        print(f"Found {len(handshakes)} recent handshakes")
        for h in handshakes:
            print(f"\n{h.get('handshake_type')}: {h.get('agent', 'unknown')} - {h.get('timestamp')}")
        return
    
    if args.get_agent:
        handshakes = get_agent_handshakes(args.get_agent)
        print(f"Found {len(handshakes)} handshakes for {args.get_agent}")
        for h in handshakes:
            print(f"\n{h.get('timestamp')}: {h.get('status')} - {', '.join(h.get('capabilities', []))}")
        return
    
    if args.sync:
        sync_data = {}
        if args.data:
            sync_data = _read_json(Path(args.data)) or {}
        
        sync_id = sync_with_agent(args.from_agent or "unknown", args.to_agent or "unknown", sync_data)
        print(f"Sync created: {sync_id}")
        return
    
    if args.announce:
        if not args.agent:
            parser.error("--agent required for --announce")
        handshake_id = announce_presence(
            agent_name=args.agent,
            version=args.version or "1.0.0",
            status=args.status or "running",
            capabilities=args.capabilities or [],
            uptime_seconds=args.uptime,
            requested_sync=args.sync_with
        )
        print(f"Handshake announced: {handshake_id}")
        return
    
    # If no operation specified, print help
    parser.print_help()


if __name__ == "__main__":
    main()

