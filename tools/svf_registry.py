#!/usr/bin/env python3
"""
SVF Agent Capability Registry
Part of SVF v2.0 enhancements (implemented 2025-10-26)
Enables agents to discover each other's capabilities
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
REGISTRY_FILE = OUT / "agent_capabilities.json"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    """Read JSON file"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON file"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"Error writing {path}: {e}")


def register_agent(agent_name: str, capabilities: List[str], 
                  data_sources: List[str], update_frequency: str,
                  contact_policy: str = "respond_to_queries",
                  additional_info: Optional[Dict[str, Any]] = None) -> bool:
    """
    Register an agent's capabilities
    
    Args:
        agent_name: Name of the agent
        capabilities: List of what agent can do
        data_sources: What data agent has access to
        update_frequency: How often agent updates
        contact_policy: How to contact agent
        additional_info: Extra metadata
        
    Returns:
        True if successful
    """
    registry = _read_json(REGISTRY_FILE) or {}
    
    registry[agent_name] = {
        "capabilities": capabilities,
        "data_sources": data_sources,
        "update_frequency": update_frequency,
        "contact_policy": contact_policy,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        **(additional_info or {})
    }
    
    _write_json(REGISTRY_FILE, registry)
    return True


def get_agent_capabilities(agent_name: str) -> Optional[Dict[str, Any]]:
    """Get capabilities for a specific agent"""
    registry = _read_json(REGISTRY_FILE) or {}
    return registry.get(agent_name)


def find_agents_by_capability(capability: str) -> List[str]:
    """Find all agents with a specific capability"""
    registry = _read_json(REGISTRY_FILE) or {}
    matching = []
    
    for agent, info in registry.items():
        if capability in info.get("capabilities", []):
            matching.append(agent)
    
    return matching


def get_all_capabilities() -> Dict[str, Any]:
    """Get the full capability registry"""
    return _read_json(REGISTRY_FILE) or {}


def main():
    parser = argparse.ArgumentParser(description="SVF Agent Capability Registry")
    parser.add_argument("--register", action="store_true", help="Register agent")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--capabilities", nargs="+", help="List of capabilities")
    parser.add_argument("--data-sources", nargs="+", help="List of data sources")
    parser.add_argument("--frequency", help="Update frequency")
    parser.add_argument("--policy", default="respond_to_queries", help="Contact policy")
    
    parser.add_argument("--find", help="Find agents with capability")
    parser.add_argument("--get", help="Get capabilities for agent")
    parser.add_argument("--list", action="store_true", help="List all agents")
    
    args = parser.parse_args()
    
    if args.register:
        success = register_agent(
            agent_name=args.agent,
            capabilities=args.capabilities or [],
            data_sources=args.data_sources or [],
            update_frequency=args.frequency or "unknown",
            contact_policy=args.policy
        )
        print(f"Registration {'successful' if success else 'failed'}")
    
    elif args.find:
        agents = find_agents_by_capability(args.find)
        print(f"Agents with '{args.find}': {', '.join(agents) if agents else 'None'}")
    
    elif args.get:
        caps = get_agent_capabilities(args.get)
        if caps:
            print(json.dumps(caps, indent=2))
        else:
            print(f"Agent '{args.get}' not found")
    
    elif args.list:
        registry = get_all_capabilities()
        for agent, info in registry.items():
            print(f"{agent}: {', '.join(info.get('capabilities', []))}")
        return
    
    # Require agent for register operations
    if args.register and not args.agent:
        parser.error("--agent required for --register")
    
    if not any([args.register, args.find, args.get, args.list]):
        parser.print_help()


if __name__ == "__main__":
    main()

