#!/usr/bin/env python3
"""
Calyx Agent Watcher

Purpose:
- Real-time monitoring and observation of all Calyx Terminal agents
- Provides comprehensive visibility into agent activity, health, and interactions
- Emits watcher-compatible heartbeats and detailed status reports
- Integrates with coordinator for system-wide observability

Behavior:
- Polls all registered agents from calyx/core/registry.jsonl
- Monitors lock files, process status, and resource usage
- Tracks agent interactions and coordination events
- Generates real-time status reports and alerts
- Writes observation data to outgoing/agent_watcher/

Outputs:
- outgoing/agent_watcher/status.json (current state snapshot)
- outgoing/agent_watcher/history.jsonl (activity log)
- outgoing/agent_watcher/alerts.jsonl (alert stream)
- outgoing/agent_watcher.lock (heartbeat)
"""

from __future__ import annotations

import argparse
import json
import os
import psutil
import signal
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
REGISTRY = ROOT / "calyx" / "core" / "registry.jsonl"
WATCHER_DIR = OUT / "agent_watcher"
LOCK_FILE = OUT / "agent_watcher.lock"
STATUS_FILE = WATCHER_DIR / "status.json"
HISTORY_FILE = WATCHER_DIR / "history.jsonl"
ALERTS_FILE = WATCHER_DIR / "alerts.jsonl"
BRIDGE_DIALOG = OUT / "bridge" / "dialog.log"

try:
    from tools.svf_util import ensure_svf_running
except Exception:
    def ensure_svf_running(*args, **kwargs):
        return False


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    role: str
    skills: List[str]
    executable: str
    autonomy: str
    interval_sec: Optional[int] = None
    parameters: Optional[str] = None


@dataclass
class AgentState:
    """Current state of an agent"""
    agent_id: str
    role: str
    is_active: bool
    last_seen: Optional[float]
    process_info: Optional[Dict[str, Any]]
    lock_file_exists: bool
    lock_file_age: Optional[float]
    health_score: float
    status_message: str
    resource_usage: Dict[str, Any]


@dataclass
class Observation:
    """Single observation record"""
    timestamp: float
    agents_observed: int
    agents_active: int
    agents_idle: int
    agents_unhealthy: int
    system_health_score: float
    agent_states: Dict[str, Dict[str, Any]]
    alerts: List[str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ts() -> float:
    return time.time()


def _ensure_dirs() -> None:
    WATCHER_DIR.mkdir(parents=True, exist_ok=True)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file"""
    if not path.exists():
        return []
    entries = []
    try:
        content = path.read_text(encoding='utf-8-sig')  # utf-8-sig strips BOM
        for line in content.split('\n'):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
    except Exception:
        pass
    return entries


def _append_jsonl(path: Path, data: Dict[str, Any]) -> None:
    """Append JSON object to JSONL file"""
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    """Write heartbeat lock file"""
    try:
        payload: Dict[str, Any] = {
            "name": "agent_watcher",
            "role": "System Observer",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": _ts(),
            "version": "1.0.0",
        }
        if extra:
            payload.update(extra)
        OUT.mkdir(parents=True, exist_ok=True)
        LOCK_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def _append_dialog(line: str) -> None:
    """Append to bridge dialog log"""
    try:
        BRIDGE_DIALOG.parent.mkdir(parents=True, exist_ok=True)
        with BRIDGE_DIALOG.open("a", encoding="utf-8") as fh:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"{ts} AGENT_WATCHER> {line}\n")
    except Exception:
        pass


def load_registered_agents() -> Dict[str, AgentInfo]:
    """Load all registered agents from registry"""
    agents = {}
    entries = _read_jsonl(REGISTRY)
    
    for entry in entries:
        agent_id = entry.get('agent_id', '')
        if not agent_id:
            continue
            
        agent_info = AgentInfo(
            agent_id=agent_id,
            role=entry.get('role', 'unknown'),
            skills=entry.get('skills', []),
            executable=entry.get('executable', ''),
            autonomy=entry.get('autonomy', 'unknown'),
            interval_sec=entry.get('interval_sec'),
            parameters=entry.get('parameters')
        )
        agents[agent_id] = agent_info
    
    return agents


def find_agent_process(agent_id: str, executable: str) -> Optional[Dict[str, Any]]:
    """Find process info for an agent"""
    try:
        search_terms = [agent_id, executable]
        if '/' in executable or '\\' in executable:
            # Extract just the script name
            script_name = Path(executable).name
            search_terms.append(script_name)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'cpu_percent', 'memory_info']):
            try:
                proc_info = proc.info
                if not proc_info['cmdline']:
                    continue
                
                cmd_str = ' '.join(proc_info['cmdline']).lower()
                
                # Check if any search term matches
                for term in search_terms:
                    if term.lower() in cmd_str:
                        return {
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'status': proc_info.get('status', 'unknown'),
                            'cpu_percent': proc_info.get('cpu_percent', 0),
                            'memory_mb': proc_info.get('memory_info', {}).rss / 1024 / 1024 if proc_info.get('memory_info') else 0,
                            'cmdline': ' '.join(proc_info['cmdline'])
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    
    return None


def check_lock_file(agent_id: str) -> tuple[bool, Optional[float]]:
    """Check if agent has a lock file and how old it is"""
    lock_path = OUT / f"{agent_id}.lock"
    
    if not lock_path.exists():
        return False, None
    
    try:
        mtime = lock_path.stat().st_mtime
        age = _ts() - mtime
        return True, age
    except Exception:
        return False, None


def calculate_health_score(process_info: Optional[Dict], lock_exists: bool, lock_age: Optional[float]) -> float:
    """Calculate health score for an agent (0-100)"""
    if process_info and lock_exists:
        # Both present - check freshness
        if lock_age is not None and lock_age < 300:  # 5 minutes
            return 100.0
        elif lock_age is not None and lock_age < 600:  # 10 minutes
            return 80.0
        else:
            return 60.0
    elif process_info:
        # Process running but no lock file
        return 70.0
    elif lock_exists:
        # Lock file exists but no process
        return 50.0
    else:
        # Neither present
        return 0.0


def get_agent_state(agent_info: AgentInfo) -> AgentState:
    """Get current state of an agent"""
    process_info = find_agent_process(agent_info.agent_id, agent_info.executable)
    lock_exists, lock_age = check_lock_file(agent_info.agent_id)
    health_score = calculate_health_score(process_info, lock_exists, lock_age)
    
    # Determine status message
    if health_score >= 90:
        status_message = "Healthy and operational"
    elif health_score >= 70:
        status_message = "Operational"
    elif health_score >= 50:
        status_message = "Degraded"
    else:
        status_message = "Unhealthy or offline"
    
    # Get resource usage
    resource_usage = {}
    if process_info:
        resource_usage = {
            'cpu_percent': process_info.get('cpu_percent', 0),
            'memory_mb': process_info.get('memory_mb', 0),
            'status': process_info.get('status', 'unknown')
        }
    
    return AgentState(
        agent_id=agent_info.agent_id,
        role=agent_info.role,
        is_active=health_score >= 70,
        last_seen=_ts() - lock_age if lock_age else None,
        process_info=process_info,
        lock_file_exists=lock_exists,
        lock_file_age=lock_age,
        health_score=health_score,
        status_message=status_message,
        resource_usage=resource_usage
    )


def observe_agents(agents: Dict[str, AgentInfo]) -> Observation:
    """Perform one observation cycle"""
    timestamp = _ts()
    agent_states = {}
    alerts = []
    
    for agent_id, agent_info in agents.items():
        state = get_agent_state(agent_info)
        agent_states[agent_id] = asdict(state)
        
        # Generate alerts for unhealthy agents
        if state.health_score < 50:
            alerts.append(f"{agent_id} ({agent_info.role}) is unhealthy (score: {state.health_score:.1f})")
    
    # Calculate summary statistics
    total_agents = len(agent_states)
    active_agents = sum(1 for s in agent_states.values() if s['is_active'])
    idle_agents = sum(1 for s in agent_states.values() if not s['is_active'] and s['health_score'] >= 50)
    unhealthy_agents = sum(1 for s in agent_states.values() if s['health_score'] < 50)
    
    # Calculate system health score
    if total_agents > 0:
        system_health_score = (active_agents / total_agents) * 100
    else:
        system_health_score = 0
    
    return Observation(
        timestamp=timestamp,
        agents_observed=total_agents,
        agents_active=active_agents,
        agents_idle=idle_agents,
        agents_unhealthy=unhealthy_agents,
        system_health_score=system_health_score,
        agent_states=agent_states,
        alerts=alerts
    )


def process_observation(obs: Observation) -> None:
    """Process and record an observation"""
    # Write current status
    status_data = {
        'timestamp': _utc_now_iso(),
        'observation': asdict(obs)
    }
    _write_json(STATUS_FILE, status_data)
    
    # Append to history
    _append_jsonl(HISTORY_FILE, status_data)
    
    # Process alerts
    if obs.alerts:
        for alert in obs.alerts:
            alert_data = {
                'timestamp': _utc_now_iso(),
                'level': 'warning',
                'message': alert,
                'system_health': obs.system_health_score
            }
            _append_jsonl(ALERTS_FILE, alert_data)
            _append_dialog(alert)
    
    # Update heartbeat
    _write_hb("observe", "running", {
        "agents_active": obs.agents_active,
        "agents_total": obs.agents_observed,
        "system_health": obs.system_health_score
    })


def loop(interval: float, max_iters: int, quiet: bool) -> int:
    """Main observation loop"""
    _ensure_dirs()
    
    # Ensure SVF is running
    try:
        ensure_svf_running(grace_sec=10.0, interval=5.0)
    except Exception:
        pass
    
    agents = load_registered_agents()
    
    if not quiet:
        print(f"[AGENT_WATCHER] Loaded {len(agents)} registered agents")
        _append_dialog(f"Agent Watcher online; monitoring {len(agents)} agents")
    
    _write_hb("init", "starting")
    
    try:
        i = 0
        while True:
            i += 1
            
            # Reload agents periodically (every 10 iterations)
            if i % 10 == 0:
                agents = load_registered_agents()
            
            # Perform observation
            obs = observe_agents(agents)
            process_observation(obs)
            
            if not quiet:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Active: {obs.agents_active}/{obs.agents_observed} "
                      f"(Health: {obs.system_health_score:.1f}%)")
                if obs.alerts:
                    for alert in obs.alerts:
                        print(f"  [WARNING] {alert}")
            
            if max_iters > 0 and i >= max_iters:
                break
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        if not quiet:
            print("\n[AGENT_WATCHER] Interrupted by user")
    finally:
        _write_hb("done", "stopped")
        if not quiet:
            print("[AGENT_WATCHER] Stopped")
    
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point"""
    ap = argparse.ArgumentParser(description="Calyx Agent Watcher - Real-time agent monitoring")
    ap.add_argument("--interval", type=float, default=10.0, help="Observation interval in seconds (default: 10)")
    ap.add_argument("--max-iters", type=int, default=0, help="Stop after N iterations (0 = run forever)")
    ap.add_argument("--quiet", action="store_true", help="Suppress console output")
    args = ap.parse_args(argv)
    
    return loop(interval=args.interval, max_iters=args.max_iters, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())

