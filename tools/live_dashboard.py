#!/usr/bin/env python3
"""
Live Performance Dashboard - Real-time system health monitoring
Generates auto-refreshing HTML dashboard for operational awareness
"""
from __future__ import annotations
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent


def _calc_quantiles(values: List[float], qs: List[float]) -> List[float]:
    if not values:
        return [0.0 for _ in qs]
    ordered = sorted(values)
    n = len(ordered)
    out: List[float] = []
    for q in qs:
        if n == 1:
            out.append(ordered[0])
            continue
        pos = q * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(ordered[lo] * (1 - frac) + ordered[hi] * frac)
    return out


def get_current_metrics() -> Dict[str, Any]:
    """Collect current system metrics"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "tes": 0.0,
        "memory_usage": 0.0,
        "active_processes": 0,
        "recent_completions": 0,
        "llm_latency_count": 0,
        "llm_latency_p50": 0.0,
        "llm_latency_p95": 0.0,
        "active_agents": [],
        "resource_health": "unknown"
    }
    
    # Get TES from recent metrics
    try:
        import csv
        metrics_file = ROOT / "logs" / "agent_metrics.csv"
        if metrics_file.exists():
            with metrics_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    latest = rows[-1]
                    metrics["tes"] = float(latest.get("tes", 0))
                    metrics["recent_completions"] = len([r for r in rows if r.get("exit_code") == "0"])
    except:
        pass
    
    # Get memory usage
    try:
        import psutil
        memory = psutil.virtual_memory()
        metrics["memory_usage"] = memory.percent
    except:
        pass
    
    # Get active processes
    try:
        import psutil
        python_procs = [p for p in psutil.process_iter(['name']) if p.info['name'] == 'python.exe']
        metrics["active_processes"] = len(python_procs)
    except:
        pass
    
    # LLM latency sampling (p50/p95)
    try:
        decisions = ROOT / "logs" / "autonomy_decisions.jsonl"
        if decisions.exists():
            latencies: List[float] = []
            with decisions.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("event") != "run_complete":
                        continue
                    llm_time = entry.get("llm_time_s")
                    if isinstance(llm_time, (int, float)) and llm_time >= 0:
                        latencies.append(float(llm_time))
            if len(latencies) > 200:
                latencies = latencies[-200:]
            metrics["llm_latency_count"] = len(latencies)
            if latencies:
                metrics["llm_latency_p50"], metrics["llm_latency_p95"] = _calc_quantiles(
                    latencies, [0.5, 0.95]
                )
    except Exception:
        pass

    # Get active agents from heartbeats
    try:
        heartbeat_dir = ROOT / "outgoing"
        for hb_file in heartbeat_dir.glob("*.lock"):
            if hb_file.stat().st_mtime > time.time() - 300:  # Active in last 5 minutes
                metrics["active_agents"].append(hb_file.stem)
    except:
        pass
    
    # Determine resource health
    if metrics["memory_usage"] < 70:
        metrics["resource_health"] = "healthy"
    elif metrics["memory_usage"] < 80:
        metrics["resource_health"] = "caution"
    else:
        metrics["resource_health"] = "critical"
    
    return metrics


def generate_dashboard_html(metrics: Dict[str, Any]) -> str:
    """Generate HTML dashboard"""
    health_color = {
        "healthy": "#28a745",
        "caution": "#ffc107",
        "critical": "#dc3545"
    }.get(metrics["resource_health"], "#6c757d")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Station Calyx - Live Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .metric-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-label {{ color: #666; font-size: 14px; margin-bottom: 8px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
        .health-indicator {{ width: 20px; height: 20px; border-radius: 50%; display: inline-block; margin-left: 10px; }}
        .status-healthy {{ background: #28a745; }}
        .status-caution {{ background: #ffc107; }}
        .status-critical {{ background: #dc3545; }}
        .agent-list {{ background: white; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .agent-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .timestamp {{ color: #999; font-size: 12px; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Station Calyx - Live Performance Dashboard</h1>
            <p>Auto-refreshing every 30 seconds</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">Task Execution Score</div>
                <div class="metric-value">{metrics['tes']:.1f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Memory Usage</div>
                <div class="metric-value">{metrics['memory_usage']:.1f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Active Processes</div>
                <div class="metric-value">{metrics['active_processes']}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Resource Health</div>
                <div class="metric-value">
                    {metrics['resource_health'].upper()}
                    <span class="health-indicator status-{metrics['resource_health']}"></span>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Recent Completions</div>
                <div class="metric-value">{metrics['recent_completions']}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">LLM Latency p50 / p95 (s)</div>
                <div class="metric-value">{metrics['llm_latency_p50']:.1f} / {metrics['llm_latency_p95']:.1f}</div>
                <div class="metric-label">Samples: {metrics['llm_latency_count']}</div>
            </div>
        </div>
        
        <div class="agent-list">
            <h2>Active Agents</h2>
            {''.join(f'<div class="agent-item">{agent}</div>' for agent in metrics['active_agents'])}
            {'' if metrics['active_agents'] else '<div class="agent-item">No active agents</div>'}
        </div>
        
        <div class="timestamp">
            Last updated: {metrics['timestamp']}
        </div>
    </div>
</body>
</html>"""
    
    return html


def main():
    """Generate dashboard"""
    metrics = get_current_metrics()
    html = generate_dashboard_html(metrics)
    
    # Save dashboard
    dashboard_file = ROOT / "reports" / "live_dashboard.html"
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    with dashboard_file.open("w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Dashboard generated: {dashboard_file}")
    print(f"Open in browser for live monitoring (auto-refreshes every 30s)")


if __name__ == "__main__":
    main()

