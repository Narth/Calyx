#!/usr/bin/env python3
"""
System Dashboard Generator with Embedded Data
Creates a standalone HTML dashboard with data embedded directly
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parents[1]

def read_json(path: Path) -> Dict[str, Any]:
    """Read JSON file"""
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def read_jsonl(path: Path, last_n: int = 100) -> List[Dict[str, Any]]:
    """Read last N lines from JSONL file"""
    lines = []
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except Exception:
                            pass
    except Exception:
        pass
    return lines[-last_n:] if lines else []

def get_cbo_status() -> Dict[str, Any]:
    """Get CBO lock status"""
    cbo_lock = ROOT / "outgoing" / "cbo.lock"
    data = read_json(cbo_lock)
    
    return {
        "timestamp": data.get("iso", "N/A"),
        "cpu_pct": data.get("metrics", {}).get("cpu_pct", 0),
        "ram_pct": data.get("metrics", {}).get("mem_used_pct", 0),
        "disk_free_pct": data.get("metrics", {}).get("disk_free_pct", 0),
        "gpu_util": data.get("metrics", {}).get("gpu", {}).get("gpus", [{}])[0].get("util_pct", 0) if data.get("metrics", {}).get("gpu") else 0,
        "gpu_temp": data.get("metrics", {}).get("gpu", {}).get("gpus", [{}])[0].get("temp_c", 0) if data.get("metrics", {}).get("gpu") else 0,
        "active_locks": [k for k, v in data.get("locks", {}).items() if v],
        "gates": data.get("gates", {}),
    }

def get_active_agents() -> List[Dict[str, Any]]:
    """Collect active agent information"""
    agents = []
    agent_lock_files = [
        "agent1.lock", "agent2.lock", "agent3.lock", "agent4.lock",
        "triage.lock", "svf.lock", "sysint.lock", "navigator.lock",
        "scheduler.lock", "cp6.lock", "cp7.lock", "cp8.lock", "cp9.lock", "cp10.lock"
    ]
    
    for lock_file in agent_lock_files:
        lock_path = ROOT / "outgoing" / lock_file
        if lock_path.exists():
            data = read_json(lock_path)
            if data:
                agent_name = lock_file.replace(".lock", "")
                agents.append({
                    "name": agent_name,
                    "status": data.get("status", "unknown"),
                    "phase": data.get("phase", "unknown"),
                    "timestamp": data.get("iso", data.get("ts", "N/A")),
                    "status_message": data.get("status_message", ""),
                    "run_dir": data.get("run_dir"),
                })
    
    return agents

def get_cbo_tasks() -> List[Dict[str, Any]]:
    """Get CBO task queue"""
    task_queue = ROOT / "calyx" / "cbo" / "task_queue.jsonl"
    tasks = read_jsonl(task_queue, last_n=50)
    
    task_summary = []
    for task in tasks:
        task_summary.append({
            "task_id": task.get("task_id", "unknown"),
            "action": task.get("action", "unknown"),
            "assignee": task.get("assignee", "unassigned"),
            "status": task.get("status", "unknown"),
            "objective_id": task.get("objective_id", "unknown"),
            "created_at": task.get("created_at", "N/A"),
        })
    
    return task_summary

def get_recent_pulses() -> List[Dict[str, Any]]:
    """Get recent bridge pulse data"""
    pulse_csv = ROOT / "metrics" / "bridge_pulse.csv"
    pulses = []
    
    try:
        if pulse_csv.exists():
            with pulse_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for row in rows[-10:]:
                    pulses.append({
                        "timestamp": row.get("timestamp", "N/A"),
                        "status": row.get("status", "N/A"),
                        "details": row.get("details", "N/A"),
                    })
    except Exception:
        pass
    
    return pulses

def get_tes_metrics() -> Dict[str, Any]:
    """Get TES metrics from agent_metrics.csv"""
    metrics_csv = ROOT / "logs" / "agent_metrics.csv"
    
    try:
        if metrics_csv.exists():
            with metrics_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    tes_values = [float(row.get('tes', 0)) for row in rows if row.get('tes')]
                    if tes_values:
                        avg_tes = sum(tes_values) / len(tes_values)
                        latest_tes = tes_values[-1] if tes_values else 0
                        return {
                            "mean": round(avg_tes, 1),
                            "latest": round(latest_tes, 1),
                            "samples": len(tes_values),
                        }
    except Exception:
        pass
    
    return {"mean": 0, "latest": 0, "samples": 0}

def generate_dashboard_data() -> Dict[str, Any]:
    """Generate dashboard data"""
    cbo_status = get_cbo_status()
    agents = get_active_agents()
    tasks = get_cbo_tasks()
    pulses = get_recent_pulses()
    tes = get_tes_metrics()
    
    task_counts = {}
    for task in tasks:
        status = task.get("status", "unknown")
        task_counts[status] = task_counts.get(status, 0) + 1
    
    assignee_counts = {}
    for task in tasks:
        assignee = task.get("assignee", "unassigned")
        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "cbo_status": cbo_status,
        "agents": agents,
        "tasks": tasks,
        "pulses": pulses,
        "tes": tes,
        "task_counts": task_counts,
        "assignee_counts": assignee_counts,
        "summary": {
            "active_agents": len([a for a in agents if a.get("status") == "running"]),
            "total_agents": len(agents),
            "total_tasks": len(tasks),
            "pending_tasks": task_counts.get("pending", 0),
            "dispatched_tasks": task_counts.get("dispatched", 0),
            "completed_tasks": task_counts.get("completed", 0),
        }
    }

def main():
    """Generate dashboard with embedded data"""
    data = generate_dashboard_data()
    
    # Read the HTML template
    html_path = ROOT / "outgoing" / "system_dashboard.html"
    html_content = html_path.read_text(encoding='utf-8')
    
    # Embed the data as a JavaScript variable
    data_json = json.dumps(data, indent=2)
    
    # Replace the fetch call with embedded data
    new_script = f"""
        const DASHBOARD_DATA = {data_json};
        
        function loadDashboard() {{
            // Use embedded data instead of fetching
            updateDashboard(DASHBOARD_DATA);
        }}
        
        function updateDashboard(data) {{
            // Update timestamp
            document.getElementById('timestamp').textContent = 
                `Last updated: ${{new Date(data.timestamp).toLocaleString()}}`;
            
            // Update resources
            const cpu = data.cbo_status.cpu_pct || 0;
            const ram = data.cbo_status.ram_pct || 0;
            const gpu = data.cbo_status.gpu_util || 0;
            const disk = data.cbo_status.disk_free_pct || 0;
            
            document.getElementById('cpu').textContent = `${{cpu.toFixed(1)}}%`;
            document.getElementById('ram').textContent = `${{ram.toFixed(1)}}%`;
            document.getElementById('gpu').textContent = `${{gpu.toFixed(1)}}%`;
            document.getElementById('disk').textContent = `${{disk.toFixed(1)}}%`;
            
            updateProgressBar('cpu-bar', cpu, 70, 85);
            updateProgressBar('ram-bar', ram, 75, 90);
            updateProgressBar('gpu-bar', gpu, 80, 90);
            updateProgressBar('disk-bar', disk, 20, 10);
            
            // Update TES
            const tesMean = data.tes.mean || 0;
            const tesLatest = data.tes.latest || 0;
            const tesSamples = data.tes.samples || 0;
            
            document.getElementById('tes-mean').textContent = tesMean.toFixed(1);
            document.getElementById('tes-latest').textContent = tesLatest.toFixed(1);
            document.getElementById('tes-samples').textContent = tesSamples;
            updateProgressBar('tes-bar', tesMean, 85, 95);
            
            // Update summary
            document.getElementById('active-agents').textContent = data.summary.active_agents;
            document.getElementById('total-tasks').textContent = data.summary.total_tasks;
            document.getElementById('pending-tasks').textContent = data.summary.pending_tasks;
            document.getElementById('dispatched-tasks').textContent = data.summary.dispatched_tasks;
            
            // Update agents
            const agentsHtml = data.agents.map(agent => `
                <div class="metric">
                    <div>
                        <span class="metric-label">${{agent.name}}</span>
                        <span class="status-badge status-${{agent.status}}">${{agent.status}}</span>
                    </div>
                    <div class="metric-value">${{agent.phase || 'N/A'}}</div>
                </div>
            `).join('');
            document.getElementById('agents-list').innerHTML = agentsHtml || '<div class="no-data">No active agents</div>';
            
            // Update tasks
            const tasksHtml = data.tasks.slice(0, 10).map(task => `
                <div class="task-item">
                    <div class="task-header">${{task.action}}</div>
                    <div class="task-details">
                        Assignee: ${{task.assignee}} | Status: ${{task.status}} | Created: ${{task.created_at}}
                    </div>
                </div>
            `).join('');
            document.getElementById('tasks-list').innerHTML = tasksHtml || '<div class="no-data">No recent tasks</div>';
            
            // Update pulses
            const pulsesHtml = data.pulses.reverse().map(pulse => `
                <div class="pulse-item">
                    <div class="pulse-time">${{pulse.timestamp}}</div>
                    <div>${{pulse.status}}</div>
                    <div style="color: #666; font-size: 0.85em; margin-top: 5px;">${{pulse.details}}</div>
                </div>
            `).join('');
            document.getElementById('pulses-list').innerHTML = pulsesHtml || '<div class="no-data">No pulse data</div>';
        }}
        
        function updateProgressBar(id, value, warningThreshold, dangerThreshold) {{
            const bar = document.getElementById(id);
            bar.style.width = `${{Math.min(value, 100)}}%`;
            bar.textContent = `${{value.toFixed(1)}}%`;
            
            bar.className = 'progress-fill';
            if (value >= dangerThreshold) {{
                bar.classList.add('progress-danger');
            }} else if (value >= warningThreshold) {{
                bar.classList.add('progress-warning');
            }}
        }}
        
        // Load dashboard on page load
        loadDashboard();
    """
    
    # Replace the script section
    import re
    # Use a more specific pattern that captures everything between the script tags
    pattern = r'(<script>)(.*?)(</script>)'
    new_html = re.sub(pattern, r'\1' + new_script + r'\3', html_content, flags=re.DOTALL)
    
    # Write the updated HTML
    output_path = ROOT / "outgoing" / "system_dashboard.html"
    output_path.write_text(new_html, encoding='utf-8')
    
    print(f"[OK] Dashboard generated with embedded data: {output_path}")
    print(f"     Active agents: {data['summary']['active_agents']}")
    print(f"     Total tasks: {data['summary']['total_tasks']}")
    print(f"     CPU: {data['cbo_status']['cpu_pct']:.1f}%")
    print(f"     RAM: {data['cbo_status']['ram_pct']:.1f}%")

if __name__ == "__main__":
    main()

