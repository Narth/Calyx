#!/usr/bin/env python3
"""
SVF Filtered Views per Agent
Part of SVF v2.0 Phase 3 (implemented 2025-10-26)
Enables agents to configure what communications they see
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
CONFIG_DIR = OUT / "agent_configs"


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


def configure_filters(agent_name: str, read_channels: List[str],
                     query_for: List[str], respond_to: List[str],
                     ignore: List[str]) -> bool:
    """
    Configure communication filters for agent
    
    Args:
        agent_name: Agent name
        read_channels: Channels to read (urgent, standard, casual)
        query_for: Types of queries to ask
        respond_to: Agents to respond to
        ignore: Channels/messages to ignore
        
    Returns:
        True if successful
    """
    config_file = CONFIG_DIR / f"{agent_name}_filters.json"
    
    config = {
        "agent": agent_name,
        "read_channels": read_channels,
        "query_for": query_for,
        "respond_to": respond_to,
        "ignore": ignore,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    _write_json(config_file, config)
    return True


def get_filters(agent_name: str) -> Dict[str, Any]:
    """Get filter configuration for agent"""
    config_file = CONFIG_DIR / f"{agent_name}_filters.json"
    config = _read_json(config_file)
    
    if not config:
        # Default: read all channels
        return {
            "read_channels": ["urgent", "standard", "casual"],
            "query_for": [],
            "respond_to": [],
            "ignore": []
        }
    
    return config


def should_handle_message(agent_name: str, channel: str, sender: str) -> bool:
    """
    Determine if agent should handle a message
    
    Args:
        agent_name: Agent name
        channel: Message channel
        sender: Message sender
        
    Returns:
        True if should handle
    """
    filters = get_filters(agent_name)
    
    # Check if channel is ignored
    if channel in filters.get("ignore", []):
        return False
    
    # Check if reading this channel
    if channel not in filters.get("read_channels", []):
        return False
    
    # Check if should respond to sender
    respond_to = filters.get("respond_to", [])
    if respond_to and sender not in respond_to:
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="SVF Filtered Views per Agent")
    parser.add_argument("--configure", action="store_true", help="Configure filters")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--channels", nargs="+", help="Channels to read")
    parser.add_argument("--query-for", nargs="+", help="Query types")
    parser.add_argument("--respond-to", nargs="+", help="Agents to respond to")
    parser.add_argument("--ignore", nargs="+", help="Things to ignore")
    
    parser.add_argument("--get", help="Get filters for agent")
    
    parser.add_argument("--check", action="store_true", help="Check if should handle")
    parser.add_argument("--channel", help="Message channel")
    parser.add_argument("--sender", help="Message sender")
    
    args = parser.parse_args()
    
    if args.configure:
        if not args.agent:
            parser.error("--agent required for --configure")
        
        success = configure_filters(
            agent_name=args.agent,
            read_channels=args.channels or [],
            query_for=args.query_for or [],
            respond_to=args.respond_to or [],
            ignore=args.ignore or []
        )
        print(f"Filter configuration {'successful' if success else 'failed'}")
    
    elif args.get:
        filters = get_filters(args.get)
        print(json.dumps(filters, indent=2))
    
    elif args.check:
        if not args.agent or not args.channel or not args.sender:
            parser.error("--agent, --channel, and --sender required for --check")
        
        should_handle = should_handle_message(args.agent, args.channel, args.sender)
        print(f"Should handle: {should_handle}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

