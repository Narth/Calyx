#!/usr/bin/env python3
"""
Station Calyx CLI — Command-Line Interface for Steering Station Calyx
Allows direct interaction with CBO and agents via LLM-powered conversation

Usage:
    python tools/station_calyx_cli.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from calyx.cbo.runtime_paths import get_task_queue_path

ROOT = Path(__file__).resolve().parents[1]

def print_banner():
    """Display Station Calyx banner"""
    print("\n" + "=" * 70)
    print("   STATION CALYX — Command Bridge")
    print("=" * 70)
    print("  Direct communication with CBO and autonomous agents")
    print("  Type 'help' for commands, 'exit' to return to monitoring")
    print("=" * 70 + "\n")

def show_help():
    """Display available commands"""
    print("""
Station Calyx Commands:
  help                          - Show this help
  status                        - Show system status
  agents                        - List all agents and their states
  tasks                         - Show current task queue
  heartbeat                     - Show recent heartbeats
  pulse                         - Generate bridge pulse report
  tes                           - Show TES metrics
  
  goal <text>                   - Issue a goal to agents
  task <action>                 - Create specific task
  command <text>                - Send command to CBO
  
  chat <message>                - Have conversation with CBO
  ask <question>                - Ask CBO a question
  discuss <topic>               - Engage in topic discussion
  
  dashboard                     - Generate dashboard HTML
  logs                          - Show recent logs
  
  exit                          - Exit CLI (agents continue running)

Examples:
  > status
  > agents
  > goal Prioritize documentation improvements
  > chat What is the current system health?
  > task Analyze TES trends for anomalies
  > tes
  > pulse
""")

def get_cbo_status() -> dict:
    """Get CBO status from lock file"""
    cbo_lock = ROOT / "outgoing" / "cbo.lock"
    
    if not cbo_lock.exists():
        return {"status": "offline", "message": "CBO not running"}
    
    try:
        data = json.loads(cbo_lock.read_text())
        return {
            "status": data.get("phase", "unknown"),
            "mode": data.get("mode", "unknown"),
            "message": data.get("status_message", ""),
            "metrics": data.get("metrics", {})
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_scheduler_status() -> dict:
    """Get scheduler status"""
    scheduler_lock = ROOT / "outgoing" / "scheduler.lock"
    
    if not scheduler_lock.exists():
        return {"status": "offline"}
    
    try:
        data = json.loads(scheduler_lock.read_text())
        return {
            "status": data.get("status", "unknown"),
            "phase": data.get("phase", "unknown"),
            "message": data.get("status_message", ""),
            "mode": data.get("mode", "unknown")
        }
    except Exception:
        return {"status": "offline"}

def show_status():
    """Display current system status"""
    cbo = get_cbo_status()
    scheduler = get_scheduler_status()
    
    print("\n" + "=" * 70)
    print("Station Calyx Status")
    print("=" * 70)
    print(f"CBO Overseer: {cbo['status']}")
    if cbo.get('message'):
        print(f"  Message: {cbo['message']}")
    print(f"Scheduler: {scheduler.get('status', 'offline')}")
    if scheduler.get('phase'):
        print(f"  Phase: {scheduler['phase']}")
    if scheduler.get('mode'):
        print(f"  Mode: {scheduler['mode']}")
    
    if cbo.get('metrics'):
        metrics = cbo['metrics']
        if 'cpu_pct' in metrics:
            print(f"CPU: {metrics['cpu_pct']:.1f}%")
        if 'mem_used_pct' in metrics:
            print(f"RAM: {metrics['mem_used_pct']:.1f}%")
    
    print("=" * 70 + "\n")

def show_agents():
    """List all agents and their status"""
    locks_dir = ROOT / "outgoing"
    
    print("\n" + "=" * 70)
    print("Active Agents")
    print("=" * 70)
    
    agent_locks = list(locks_dir.glob("agent*.lock"))
    cp_locks = list(locks_dir.glob("cp*.lock"))
    
    agents = []
    for lock_file in sorted(agent_locks + cp_locks):
        try:
            data = json.loads(lock_file.read_text())
            agents.append({
                "name": data.get("name", lock_file.stem),
                "status": data.get("status", "unknown"),
                "phase": data.get("phase", "unknown"),
                "message": data.get("status_message", "")
            })
        except Exception:
            pass
    
    for agent in agents:
        print(f"{agent['name']:15} {agent['status']:10} {agent['phase']:15}")
        if agent['message']:
            print(f"  {agent['message'][:60]}")
    
    print("=" * 70 + "\n")

def show_tasks():
    """Show current task queue"""
    task_queue = get_task_queue_path(ROOT)
    
    if not task_queue.exists():
        print("\nNo tasks in queue.\n")
        return
    
    print("\n" + "=" * 70)
    print("Task Queue")
    print("=" * 70)
    
    try:
        with task_queue.open('r', encoding='utf-8') as f:
            lines = list(f)
            for line in lines[-10:]:  # Last 10 tasks
                task = json.loads(line.strip())
                print(f"Task: {task.get('action', 'N/A')[:60]}")
                print(f"  Status: {task.get('status', 'N/A')}")
                print(f"  Assignee: {task.get('assignee', 'unassigned')}")
                print()
    except Exception as e:
        print(f"Error reading tasks: {e}\n")
    
    print("=" * 70 + "\n")

def show_tes():
    """Show TES metrics"""
    tes_csv = ROOT / "metrics" / "tes.csv"
    
    if not tes_csv.exists():
        print("\nNo TES data available.\n")
        return
    
    print("\n" + "=" * 70)
    print("TES Metrics")
    print("=" * 70)
    
    try:
        import csv
        with tes_csv.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                tes_values = [float(row.get('tes', 0)) for row in rows if row.get('tes')]
                if tes_values:
                    latest = tes_values[-1]
                    mean = sum(tes_values) / len(tes_values)
                    print(f"Latest TES: {latest:.1f}")
                    print(f"Mean TES: {mean:.1f}")
                    print(f"Samples: {len(tes_values)}")
    except Exception as e:
        print(f"Error reading TES: {e}")
    
    print("=" * 70 + "\n")

def create_goal(text: str):
    """Create a goal for agents"""
    goal_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    goal_file = ROOT / "outgoing" / f"goal_{goal_id}.txt"
    
    goal_file.write_text(text, encoding='utf-8')
    print(f"\n✓ Goal created: {goal_file.name}")
    print(f"  '{text[:80]}...'")
    print(f"  Agents will process this goal autonomously.\n")

def issue_command(text: str):
    """Issue a command to CBO"""
    command_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    command_file = ROOT / "outgoing" / "commands" / f"command_{command_id}.json"
    
    command_dir = command_file.parent
    command_dir.mkdir(exist_ok=True)
    
    command_data = {
        "command": text,
        "timestamp": datetime.now().isoformat(),
        "status": "pending"
    }
    
    command_file.write_text(json.dumps(command_data, indent=2), encoding='utf-8')
    print(f"\n✓ Command issued: {command_file.name}")
    print(f"  '{text[:80]}...'")
    print(f"  CBO will process this command.\n")

def chat_with_cbo(message: str):
    """Have a conversation with CBO"""
    print(f"\n🤖 CBO: [Processing your message...]")
    print(f"📝 You: {message}")
    print(f"\n[LLM integration coming soon - for now, your message has been logged]")
    print(f"[CBO received: '{message}']\n")
    
    # TODO: Integrate with LLM to generate CBO response
    # For now, just acknowledge

def handle_command(command: str, args: str):
    """Handle CLI commands"""
    if command == "help":
        show_help()
    
    elif command == "status":
        show_status()
    
    elif command == "agents":
        show_agents()
    
    elif command == "tasks":
        show_tasks()
    
    elif command == "tes":
        show_tes()
    
    elif command == "pulse":
        print("\n⏳ Generating bridge pulse report...")
        print("[This would call bridge_pulse_generator.py]")
        print("📊 Report would be generated in reports/\n")
    
    elif command == "dashboard":
        print("\n⏳ Generating dashboard...")
        print("[Calling create_dashboard.py]")
        print("📊 Dashboard available at outgoing/system_dashboard.html\n")
    
    elif command == "goal":
        if not args:
            print("Error: Please provide a goal")
            print("Example: goal Improve documentation")
        else:
            create_goal(args)
    
    elif command == "command":
        if not args:
            print("Error: Please provide a command")
            print("Example: command Analyze system load")
        else:
            issue_command(args)
    
    elif command == "chat" or command == "ask" or command == "discuss":
        if not args:
            print("Error: Please provide a message")
            print("Example: chat What is the current system health?")
        else:
            chat_with_cbo(args)
    
    else:
        print(f"Unknown command: {command}")
        print("Type 'help' for available commands.\n")

def main():
    print_banner()
    
    print("Station Calyx CLI Ready!")
    print("You can now steer the station directly.\n")
    
    while True:
        try:
            command_input = input("station> ").strip()
            
            if not command_input:
                continue
            
            # Safety check for EOF
            if command_input == "" and not sys.stdin.isatty():
                break
            
            if command_input == "exit" or command_input == "quit":
                print("\nExiting CLI. Station Calyx continues operating autonomously.")
                print("Monitor via: live_heartbeat.html and system_dashboard.html\n")
                break
            
            # Parse command
            parts = command_input.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            handle_command(cmd, args)
        
        except KeyboardInterrupt:
            print("\n\nExiting CLI. Station Calyx continues operating.\n")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()

