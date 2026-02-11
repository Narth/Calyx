#!/usr/bin/env python3
"""
Create System Dashboard with Auto-Refresh
Generates a standalone HTML file with embedded data and continuous monitoring
"""

import json
import csv
from pathlib import Path
from datetime import datetime

from calyx.cbo.runtime_paths import get_task_queue_path

ROOT = Path(__file__).resolve().parents[1]

def read_json(path: Path):
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def read_jsonl(path: Path, last_n: int = 100):
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

def collect_data():
    # Get CBO status
    cbo_lock = ROOT / "outgoing" / "cbo.lock"
    cbo_data = read_json(cbo_lock)
    
    cpu = cbo_data.get("metrics", {}).get("cpu_pct", 0)
    ram = cbo_data.get("metrics", {}).get("mem_used_pct", 0)
    disk = cbo_data.get("metrics", {}).get("disk_free_pct", 0)
    gpu_data = cbo_data.get("metrics", {}).get("gpu", {})
    gpu_util = gpu_data.get("gpus", [{}])[0].get("util_pct", 0) if gpu_data else 0
    gpu_temp = gpu_data.get("gpus", [{}])[0].get("temp_c", 0) if gpu_data else 0
    
    # Get agents with role categorization
    agent_roles = {
        "Core": ["agent1", "agent2", "agent3", "agent4", "scheduler"],
        "Infrastructure": ["triage", "svf", "sysint", "navigator"],
        "Observation": ["cp6", "cp7", "cp8", "cp9", "cp10"]
    }
    
    agents_by_role = {"Core": [], "Infrastructure": [], "Observation": []}
    
    for role, names in agent_roles.items():
        for name in names:
            lock_path = ROOT / "outgoing" / f"{name}.lock"
            if lock_path.exists():
                data = read_json(lock_path)
                if data:
                    status = data.get("status", "unknown")
                    phase = data.get("phase")
                    
                    # If no phase field, derive from status or status_message
                    if not phase:
                        status_msg = data.get("status_message", "")
                        if status == "monitoring":
                            phase = "active" if status_msg else "idle"
                        elif status in ["running", "done", "warn", "observing"]:
                            phase = status
                        else:
                            phase = status_msg[:20] if status_msg else "active"
                    
                    agents_by_role[role].append({
                        "name": name,
                        "status": status,
                        "phase": phase,
                        "message": data.get("status_message", "")[:60]
                    })
    
    # Flatten for summary counts
    agents = []
    for role_agents in agents_by_role.values():
        agents.extend(role_agents)
    
    # Get tasks
    task_queue = get_task_queue_path(ROOT)
    tasks = read_jsonl(task_queue, last_n=10)
    
    # Get TES
    tes_csv = ROOT / "logs" / "agent_metrics.csv"
    tes_mean = 0
    tes_latest = 0
    tes_samples = 0
    tes_last_10 = []
    try:
        if tes_csv.exists():
            with tes_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    tes_values = [float(row.get('tes', 0)) for row in rows if row.get('tes')]
                    if tes_values:
                        tes_mean = sum(tes_values) / len(tes_values)
                        tes_latest = tes_values[-1]
                        tes_samples = len(tes_values)
                        tes_last_10 = tes_values[-10:]  # Last 10 samples for sparkline
    except Exception:
        pass
    
    # Get pulses
    pulse_csv = ROOT / "metrics" / "bridge_pulse.csv"
    pulses = []
    try:
        if pulse_csv.exists():
            with pulse_csv.open('r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                for row in rows[-5:]:
                    pulses.append({
                        "time": row.get("timestamp", "N/A"),
                        "status": row.get("status", "N/A"),
                        "details": row.get("details", "N/A")
                    })
    except Exception:
        pass
    
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "gpu_util": gpu_util,
        "gpu_temp": gpu_temp,
        "agents": agents,
        "agents_by_role": agents_by_role,
        "tasks": tasks,
        "tes_mean": tes_mean,
        "tes_latest": tes_latest,
        "tes_samples": tes_samples,
        "tes_last_10": tes_last_10,
        "pulses": pulses,
        "timestamp": datetime.now().isoformat()
    }

def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def create_html(data):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Station Calyx — System Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #e0e0e0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .timestamp {{ color: #888; font-size: 0.9em; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .card h2 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #667eea;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            padding-bottom: 10px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ font-weight: 500; color: #bbb; }}
        .metric-value {{ font-weight: bold; font-size: 1.1em; }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .status-running {{ background: rgba(46, 213, 115, 0.2); color: #2ed573; }}
        .status-monitoring {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .status-done {{ background: rgba(108, 117, 125, 0.2); color: #6c757d; }}
        .status-warn {{ background: rgba(255, 206, 84, 0.2); color: #ffce54; }}
        .status-observing {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75em;
            font-weight: bold;
        }}
        .progress-warning {{ background: linear-gradient(90deg, #ffce54, #f0a500); }}
        .progress-danger {{ background: linear-gradient(90deg, #fa4251, #dc3545); }}
        .task-item {{
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}
        .pulse-item {{
            padding: 8px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            font-size: 0.9em;
        }}
        .full-width {{ grid-column: 1 / -1; }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-box {{
            background: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 0.85em; color: #888; margin-top: 5px; }}
        .agent-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .agent-card {{
            background: rgba(255, 255, 255, 0.03);
            padding: 15px;
            border-radius: 10px;
            border-left: 3px solid #667eea;
        }}
        .agent-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .agent-name {{
            font-weight: 600;
            color: #667eea;
            font-size: 1.1em;
        }}
        .agent-phase {{
            color: #bbb;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .refresh-indicator {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(102, 126, 234, 0.2);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 0.85em;
            color: #667eea;
            animation: pulse 2s ease-in-out infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .sparkline {{
            width: 100%;
            height: 40px;
            margin-top: 10px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 5px;
            position: relative;
            overflow: hidden;
        }}
        .sparkline-line {{
            fill: none;
            stroke: #667eea;
            stroke-width: 2;
        }}
        .sparkline-area {{
            fill: rgba(102, 126, 234, 0.1);
        }}
        .role-section {{
            margin-bottom: 25px;
        }}
        .role-header {{
            font-size: 1.1em;
            color: #667eea;
            margin-bottom: 10px;
            font-weight: 600;
            border-bottom: 1px solid rgba(102, 126, 234, 0.3);
            padding-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refresh-indicator">Monitoring...</div>
    <div class="container">
        <header>
            <h1>🛰 Station Calyx — System Dashboard</h1>
            <div class="timestamp" id="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Auto-refresh every 30s)</div>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>📊 System Resources</h2>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value">{data['cpu']:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(data['cpu'], 100)}%;">{data['cpu']:.1f}%</div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">RAM Usage</span>
                    <span class="metric-value">{data['ram']:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(data['ram'], 100)}%;">{data['ram']:.1f}%</div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">GPU Usage</span>
                    <span class="metric-value">{data['gpu_util']:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(data['gpu_util'], 100)}%;">{data['gpu_util']:.1f}%</div>
                </div>
                
                <div class="metric">
                    <span class="metric-label">Disk Free</span>
                    <span class="metric-value">{data['disk']:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(data['disk'], 100)}%;">{data['disk']:.1f}%</div>
                </div>
            </div>
            
            <div class="card">
                <h2>⚡ TES Metrics</h2>
                <div class="metric">
                    <span class="metric-label">Mean TES</span>
                    <span class="metric-value">{data['tes_mean']:.1f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Latest TES</span>
                    <span class="metric-value">{data['tes_latest']:.1f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Samples</span>
                    <span class="metric-value">{data['tes_samples']}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(data['tes_mean'], 100)}%;">{data['tes_mean']:.1f}</div>
                </div>
                {f'''
                <div class="sparkline">
                    <svg width="100%" height="40" viewBox="0 0 100 40" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="tesGradient" x1="0%" y1="0%" oppositeDirection="true">
                                <stop offset="0%" style="stop-color:#667eea;stop-opacity:0.3" />
                                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:0.1" />
                            </linearGradient>
                        </defs>
                        <path class="sparkline-area" d="M0,40 {' '.join([f'L{i*11},{40 - (val*0.35):.1f}' for i, val in enumerate(data['tes_last_10'])])} L100,40 Z" fill="url(#tesGradient)"/>
                        <path class="sparkline-line" d="M{' '.join([f'{i*11},{40 - (val*0.35):.1f}' for i, val in enumerate(data['tes_last_10'])])}" />
                    </svg>
                </div>
                ''' if data['tes_last_10'] else ''}
            </div>
            
            <div class="card">
                <h2>📈 Summary</h2>
                <div class="stat-grid">
                    <div class="stat-box">
                        <div class="stat-value">{len([a for a in data['agents'] if a['status'] == 'running'])}</div>
                        <div class="stat-label">Active Agents</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(data['agents'])}</div>
                        <div class="stat-label">Total Agents</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{len(data['tasks'])}</div>
                        <div class="stat-label">Tasks</div>
                    </div>
                </div>
            </div>
            
            <div class="card full-width">
                <h2>🤖 Active Agents</h2>
                {''.join([f'''
                <div class="role-section">
                    <div class="role-header">{role}</div>
                    <div class="agent-grid">
                        {''.join([f'''
                        <div class="agent-card">
                            <div class="agent-header">
                                <span class="agent-name">{agent['name']}</span>
                                <span class="status-badge status-{agent['status']}">{agent['status']}</span>
                            </div>
                            <div class="agent-phase">{escape_html(agent['phase'])}</div>
                            {'<div style="font-size: 0.8em; color: #888; margin-top: 5px;">' + escape_html(agent['message']) + '</div>' if agent['message'] else ''}
                        </div>
                        ''' for agent in role_agents])}
                    </div>
                </div>
                ''' for role, role_agents in data['agents_by_role'].items() if role_agents])}
            </div>
            
            <div class="card full-width">
                <h2>📋 Recent Tasks</h2>
                {''.join([f'''
                <div class="task-item">
                    <div style="font-weight: 600; color: #667eea; margin-bottom: 5px;">{task.get('action', 'Unknown')[:80]}</div>
                    <div style="font-size: 0.85em; color: #999;">
                        Assignee: {task.get('assignee', 'unassigned')} | Status: {task.get('status', 'unknown')}
                    </div>
                </div>
                ''' for task in data['tasks'][:10]])}
            </div>
            
            <div class="card full-width">
                <h2>💓 Recent Bridge Pulses</h2>
                {''.join([f'''
                <div class="pulse-item">
                    <div style="color: #888; font-size: 0.85em;">{pulse['time']}</div>
                    <div>{pulse['status']}</div>
                    <div style="color: #666; font-size: 0.85em; margin-top: 5px;">{pulse['details'][:100]}</div>
                </div>
                ''' for pulse in reversed(data['pulses'])])}
            </div>
        </div>
    </div>
    
    <script>
        let refreshCount = 0;
        
        function reloadDashboard() {{
            refreshCount++;
            const indicator = document.getElementById('refresh-indicator');
            indicator.textContent = `Refreshing... (${{refreshCount}})`;
            indicator.style.color = '#ffce54';
            
            // Force reload without cache to get fresh data
            window.location.reload(true);
        }}
        
        // Auto-refresh every 30 seconds - page reload gets fresh embedded data
        setInterval(reloadDashboard, 30000);
        
        // Update indicator to show monitoring state
        setTimeout(() => {{
            const indicator = document.getElementById('refresh-indicator');
            indicator.textContent = 'Monitoring (auto-refresh active)';
            indicator.style.color = '#667eea';
        }}, 2000);
    </script>
</body>
</html>"""
    return html

def main():
    print("[INFO] Collecting system data...")
    data = collect_data()
    
    print("[INFO] Generating HTML dashboard with auto-refresh...")
    html = create_html(data)
    
    output_path = ROOT / "outgoing" / "system_dashboard.html"
    output_path.write_text(html, encoding='utf-8')
    
    # Also write JSON data for live updates
    json_path = ROOT / "outgoing" / "system_dashboard_data.json"
    json_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    print(f"[OK] Dashboard created: {output_path}")
    print(f"[OK] Data file created: {json_path}")
    print(f"     Active agents: {len([a for a in data['agents'] if a['status'] == 'running'])}")
    print(f"     Total agents: {len(data['agents'])}")
    print(f"     Tasks: {len(data['tasks'])}")
    print(f"     CPU: {data['cpu']:.1f}% | RAM: {data['ram']:.1f}%")
    print(f"     Dashboard will auto-refresh every 30 seconds")

if __name__ == "__main__":
    main()
