#!/usr/bin/env python3
"""
Reset agent scheduler backoff state to restore baseline intervals.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def reset_backoff():
    """Reset backoff state for all agents"""
    agents = [
        ("agent1", "agent_scheduler_state.json", 240),
        ("agent2", "agent_scheduler_state_agent2.json", 300),
        ("agent3", "agent_scheduler_state_agent3.json", 360),
    ]
    
    for agent_name, state_file, baseline in agents:
        state_path = ROOT / "logs" / state_file
        if state_path.exists():
            with open(state_path, 'r') as f:
                state = json.load(f)
            
            state['interval'] = baseline
            state['warn_streak'] = 0
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            print(f"{agent_name}: Reset to {baseline}s, cleared warnings")
        else:
            print(f"{agent_name}: State file not found")

if __name__ == "__main__":
    reset_backoff()

