#!/usr/bin/env python3
"""
Live Heartbeat Monitor
Generates a dashboard that updates every 2-3 seconds to show real-time heartbeats
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parents[1]

def get_lock_timestamps() -> Dict[str, Any]:
    """Get last heartbeat time for each agent/service"""
    locks = {}
    agent_files = [
        "agent1", "agent2", "agent3", "agent4", "triage", "svf", "sysint",
        "navigator", "scheduler", "cp6", "cp7", "cp8", "cp9", "cp10", "cbo"
    ]
    
    for name in agent_files:
        lock_path = ROOT / "outgoing" / f"{name}.lock"
        if lock_path.exists():
            try:
                data = json.loads(lock_path.read_text(encoding='utf-8'))
                ts = data.get('ts', 0)
                iso = data.get('iso', '')
                status = data.get('status', 'unknown')
                phase = data.get('phase', 'unknown')
                
                # Calculate seconds since last heartbeat
                now = time.time()
                seconds_ago = now - ts if ts else 999
                
                locks[name] = {
                    'timestamp': ts,
                    'iso': iso,
                    'status': status,
                    'phase': phase,
                    'seconds_ago': seconds_ago,
                    'active': seconds_ago < 60  # Active if heard from in last minute
                }
            except Exception:
                pass
    
    return locks

def collect_heartbeat_data() -> Dict[str, Any]:
    """Collect real-time heartbeat data"""
    locks = get_lock_timestamps()
    
    # Count by status
    active_count = sum(1 for l in locks.values() if l['active'])
    running_count = sum(1 for l in locks.values() if l['status'] == 'running')
    
    # Get recent heartbeat activity
    recent_heartbeats = []
    for name, lock in sorted(locks.items(), key=lambda x: x[1]['timestamp'], reverse=True):
        if lock['seconds_ago'] < 120:  # Last 2 minutes
            recent_heartbeats.append({
                'name': name,
                'seconds_ago': lock['seconds_ago'],
                'status': lock['status'],
                'phase': lock['phase']
            })
    
    return {
        'timestamp': datetime.now().isoformat(),
        'total_services': len(locks),
        'active_services': active_count,
        'running_services': running_count,
        'heartbeats': locks,
        'recent_activity': recent_heartbeats[:10],
        'pulse_rate': active_count / len(locks) if locks else 0
    }

def generate_heartbeat_html(data: Dict[str, Any]) -> str:
    """Generate HTML with embedded heartbeat data"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Station Calyx — Live Heartbeat Monitor</title>
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
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }}
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
        .heartbeat-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            border-left: 3px solid #667eea;
            transition: all 0.3s ease;
        }}
        .heartbeat-item:hover {{ background: rgba(255, 255, 255, 0.08); }}
        .service-name {{ font-weight: 600; color: #667eea; }}
        .heartbeat-status {{ font-size: 0.85em; color: #bbb; }}
        .pulse-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #fa4251;
            animation: pulse 2s ease-in-out infinite;
        }}
        .pulse-indicator.active {{
            background: #2ed573;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.5; transform: scale(1.2); }}
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 0.85em; color: #888; margin-top: 5px; }}
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
    </style>
</head>
<body>
    <div class="refresh-indicator" id="refresh-indicator">Heartbeat Monitor</div>
    <div class="container">
        <header>
            <h1>💓 Station Calyx — Live Heartbeat Monitor</h1>
            <div class="timestamp">Monitoring system pulses in real-time</div>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Pulse Status</h2>
                <div style="text-align: center; padding: 20px;">
                    <div class="stat-value">{data['active_services']}/{data['total_services']}</div>
                    <div class="stat-label">Active Services</div>
                </div>
                <div style="text-align: center; padding: 20px;">
                    <div class="stat-value">{data['running_services']}</div>
                    <div class="stat-label">Running Tasks</div>
                </div>
                <div style="text-align: center; padding: 20px;">
                    <div class="stat-value">{data['pulse_rate']:.0%}</div>
                    <div class="stat-label">System Pulse Rate</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔄 Recent Heartbeats</h2>
                {''.join([f'''
                <div class="heartbeat-item">
                    <div>
                        <span class="service-name">{hb['name']}</span>
                        <div class="heartbeat-status">{hb['status']} · {hb['phase']}</div>
                    </div>
                    <div>
                        <span class="pulse-indicator {'active' if hb['seconds_ago'] < 30 else ''}"></span>
                        <span style="font-size: 0.85em; color: #888; margin-left: 8px;">{hb['seconds_ago']:.0f}s ago</span>
                    </div>
                </div>
                ''' for hb in data['recent_activity']])}
            </div>
            
            <div class="card full-width" style="grid-column: 1 / -1;">
                <h2>💗 All Service Heartbeats</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px;">
                    {''.join([f'''
                    <div class="heartbeat-item">
                        <div>
                            <span class="service-name">{name}</span>
                            <div class="heartbeat-status">{lock['status']}</div>
                        </div>
                        <div>
                            <span class="pulse-indicator {'active' if lock['active'] else ''}"></span>
                            <span style="font-size: 0.75em; color: #888;">{lock['seconds_ago']:.0f}s</span>
                        </div>
                    </div>
                    ''' for name, lock in sorted(data['heartbeats'].items())])}
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Refresh every 3 seconds to show live heartbeats
        setTimeout(() => {{
            window.location.reload(true);
        }}, 3000);
    </script>
</body>
</html>"""
    return html

def main():
    data = collect_heartbeat_data()
    html = generate_heartbeat_html(data)
    
    output_path = ROOT / "outgoing" / "live_heartbeat.html"
    output_path.write_text(html, encoding='utf-8')
    
    print(f"[OK] Live heartbeat monitor: {output_path}")
    print(f"     Active: {data['active_services']}/{data['total_services']}")
    print(f"     Running: {data['running_services']}")
    print(f"     Pulse rate: {data['pulse_rate']:.0%}")

if __name__ == "__main__":
    main()

