#!/usr/bin/env python3
"""
SVF Adaptive Communication Frequency
Part of SVF v2.0 Phase 3 (implemented 2025-10-26)
Enables agents to adjust reporting frequency based on importance
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
CONFIG_DIR = OUT / "agent_configs"
SVF_AUDIT_DIR = ROOT / "logs" / "svf_audit"


class FrequencyPreset(Enum):
    """Frequency presets for agent communication"""
    CRITICAL = "critical"  # Every cycle
    IMPORTANT = "important"  # Every 5 cycles
    ROUTINE = "routine"  # Every 20 cycles
    BACKUP = "backup"  # On change only


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


def configure_agent_frequency(agent_name: str, preset: str, 
                              triggers: Optional[List[str]] = None,
                              cycle_interval: int = 60) -> bool:
    """
    Configure agent communication frequency
    
    Args:
        agent_name: Agent name
        preset: Frequency preset (critical, important, routine, backup)
        triggers: Events that trigger immediate reporting
        cycle_interval: Base interval in seconds
        
    Returns:
        True if successful
    """
    config_file = CONFIG_DIR / f"{agent_name}_frequency.json"
    
    preset_intervals = {
        "critical": 1,
        "important": 5,
        "routine": 20,
        "backup": 999999  # Effectively "never" unless triggered
    }
    
    config = {
        "agent": agent_name,
        "preset": preset,
        "cycle_interval": cycle_interval,
        "report_every_n_cycles": preset_intervals.get(preset, 20),
        "triggers": triggers or [],
        "last_report": None,
        "cycle_count": 0,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    _write_json(config_file, config)
    return True


def should_report(agent_name: str, trigger_event: Optional[str] = None) -> bool:
    """
    Determine if agent should report based on frequency and triggers
    
    Args:
        agent_name: Agent name
        trigger_event: Optional trigger event
        
    Returns:
        True if should report
    """
    config_file = CONFIG_DIR / f"{agent_name}_frequency.json"
    config = _read_json(config_file)
    
    if not config:
        # Default: report every cycle
        return True
    
    # Check for trigger event
    if trigger_event and trigger_event in config.get("triggers", []):
        return True
    
    # Check cycle count
    cycle_count = config.get("cycle_count", 0)
    report_every = config.get("report_every_n_cycles", 20)
    
    if cycle_count % report_every == 0:
        return True
    
    return False


def record_communication(agent_name: str, message_type: str, channel: str,
                       priority: str, should_report_result: bool) -> None:
    """
    Record communication decision for audit trail
    
    Args:
        agent_name: Agent name
        message_type: Type of message
        channel: Communication channel
        priority: Message priority
        should_report_result: Whether reporting occurred
    """
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "action": "frequency_check",
        "message_type": message_type,
        "channel": channel,
        "priority": priority,
        "should_report": should_report_result,
        "result": "reported" if should_report_result else "skipped"
    }
    
    audit_file = SVF_AUDIT_DIR / f"svf_frequency_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    with audit_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry) + "\n")


def increment_cycle(agent_name: str) -> None:
    """Increment cycle count for agent"""
    config_file = CONFIG_DIR / f"{agent_name}_frequency.json"
    config = _read_json(config_file)
    
    if config:
        config["cycle_count"] = config.get("cycle_count", 0) + 1
        config["last_report"] = datetime.now(timezone.utc).isoformat()
        _write_json(config_file, config)


def get_frequency_stats(agent_name: str) -> Dict[str, Any]:
    """Get frequency statistics for agent"""
    config_file = CONFIG_DIR / f"{agent_name}_frequency.json"
    config = _read_json(config_file)
    
    if not config:
        return {"status": "not_configured"}
    
    return {
        "preset": config.get("preset"),
        "report_every_n_cycles": config.get("report_every_n_cycles"),
        "cycle_count": config.get("cycle_count", 0),
        "last_report": config.get("last_report"),
        "triggers": config.get("triggers", [])
    }


def main():
    parser = argparse.ArgumentParser(description="SVF Adaptive Communication Frequency")
    parser.add_argument("--configure", action="store_true", help="Configure agent frequency")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--preset", choices=["critical", "important", "routine", "backup"], help="Frequency preset")
    parser.add_argument("--triggers", nargs="+", help="Trigger events")
    parser.add_argument("--interval", type=int, default=60, help="Cycle interval in seconds")
    
    parser.add_argument("--check", action="store_true", help="Check if should report")
    parser.add_argument("--trigger", help="Trigger event")
    
    parser.add_argument("--increment", action="store_true", help="Increment cycle count")
    
    parser.add_argument("--stats", help="Get frequency stats for agent")
    
    args = parser.parse_args()
    
    if args.configure:
        if not args.agent or not args.preset:
            parser.error("--agent and --preset required for --configure")
        
        success = configure_agent_frequency(
            agent_name=args.agent,
            preset=args.preset,
            triggers=args.triggers,
            cycle_interval=args.interval
        )
        print(f"Configuration {'successful' if success else 'failed'}")
    
    elif args.check:
        if not args.agent:
            parser.error("--agent required for --check")
        
        should_report_result = should_report(args.agent, args.trigger)
        print(f"Should report: {should_report_result}")
    
    elif args.increment:
        if not args.agent:
            parser.error("--agent required for --increment")
        
        increment_cycle(args.agent)
        print("Cycle incremented")
    
    elif args.stats:
        stats = get_frequency_stats(args.stats)
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

