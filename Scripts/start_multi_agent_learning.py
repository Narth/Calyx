#!/usr/bin/env python3
"""Start multi-agent learning deployment for 4x acceleration.

This script deploys Agent2-4 alongside Agent1 for parallel learning,
testing, and planning tasks.

Usage:
    python Scripts/start_multi_agent_learning.py
    python Scripts/start_multi_agent_learning.py --dry-run
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
POLICY = ROOT.parent / "outgoing" / "policies" / "cbo_multi_agent_policy.json"

def check_capacity() -> bool:
    """Check if system has capacity for multi-agent deployment."""
    try:
        result = subprocess.run(
            ["python", "-u", "tools/cbo_overseer.py", "--status"],
            capture_output=True,
            text=True,
            cwd=str(ROOT.parent)
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            score = data.get("capacity", {}).get("score", 0)
            cpu = data.get("metrics", {}).get("cpu_pct", 100)
            mem = data.get("metrics", {}).get("mem_used_pct", 100)
            
            print(f"[Multi-Agent] Capacity check: score={score:.3f}, CPU={cpu:.1f}%, Mem={mem:.1f}%")
            
            # Require capacity score > 0.25 and reasonable resources
            if score > 0.25 and cpu < 90 and mem < 92:
                return True
            else:
                print(f"[Multi-Agent] Insufficient capacity. Skipping deployment.")
                return False
    except Exception as e:
        print(f"[Multi-Agent] Capacity check failed: {e}")
        return False
    return False

def start_agent(agent_id: int, interval: int, dry_run: bool = False) -> bool:
    """Start an agent scheduler."""
    if agent_id == 1:
        print(f"[Multi-Agent] Agent1 already active, skipping")
        return True
    
    hb_name = f"agent{agent_id}"
    cmd = [
        "python", "-u", "tools/agent_scheduler.py",
        "--agent-id", str(agent_id),
        "--interval", str(interval),
        "--heartbeat-name", hb_name,
        "--auto-promote",
        "--adaptive-backoff"
    ]
    
    if dry_run:
        print(f"[Multi-Agent] Would start: {' '.join(cmd)}")
        return True
    
    try:
        # Start in background
        subprocess.Popen(
            cmd,
            cwd=str(ROOT.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"[Multi-Agent] Started Agent{agent_id} scheduler (interval={interval}s)")
        return True
    except Exception as e:
        print(f"[Multi-Agent] Failed to start Agent{agent_id}: {e}")
        return False

def main():
    ap = argparse.ArgumentParser(description="Start multi-agent learning deployment")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = ap.parse_args()
    
    print("[Multi-Agent] Starting 4x learning acceleration deployment")
    
    # Check capacity
    if not check_capacity():
        print("[Multi-Agent] Aborting: insufficient capacity")
        return 1
    
    # Load policy
    if POLICY.exists():
        policy = json.loads(POLICY.read_text())
        agents = policy.get("multi_agent_deployment", {}).get("agents", {})
    else:
        print("[Multi-Agent] Policy not found, using defaults")
        agents = {
            "agent2": {"interval_sec": 300},
            "agent3": {"interval_sec": 360},
            "agent4": {"interval_sec": 420}
        }
    
    # Start agents sequentially
    print("[Multi-Agent] Sequential startup...")
    for agent_name in ["agent2", "agent3", "agent4"]:
        agent_id = int(agent_name[-1])
        config = agents.get(agent_name, {})
        interval = config.get("interval_sec", 300)
        
        if start_agent(agent_id, interval, args.dry_run):
            print(f"[Multi-Agent] Agent{agent_id} deployment initiated")
            if not args.dry_run:
                time.sleep(2)  # Small delay between starts
        else:
            print(f"[Multi-Agent] Failed to deploy Agent{agent_id}")
            return 1
    
    print("[Multi-Agent] Deployment complete. Multi-agent learning active.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

