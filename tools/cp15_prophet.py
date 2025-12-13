#!/usr/bin/env python3
"""
CP15 — The Prophet
Predictive Analytics & Forecasting Agent
Part of Station Calyx Analytics & Optimization Team
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outgoing"
LOGS = ROOT / "logs"
LOCK = OUT / "cp15.lock"
METRICS_CSV = LOGS / "agent_metrics.csv"
ENHANCED_METRICS = LOGS / "enhanced_metrics.jsonl"

# SVF v2.0 imports
try:
    from tools.svf_query import create_query, get_pending_queries, respond_to_query
    from tools.svf_channels import send_message
    from tools.svf_registry import register_agent, get_agent_capabilities
    from tools.svf_handshake import announce_presence
    from tools.svf_frequency import should_report, increment_cycle
    from tools.svf_audit import log_communication
    SVF_AVAILABLE = True
except ImportError:
    SVF_AVAILABLE = False
    print("Warning: SVF v2.0 not available, running in compatibility mode")


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


def _write_hb(phase: str, status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    """Write heartbeat"""
    try:
        payload: Dict[str, Any] = {
            "name": "cp15",
            "pid": os.getpid(),
            "phase": phase,
            "status": status,
            "ts": time.time(),
            "version": "1.0.0",
        }
        if extra:
            payload.update(extra)
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def generate_forecast() -> Dict[str, Any]:
    """Generate TES and resource forecasts"""
    import csv
    
    # Read recent TES data
    tes_values = []
    if METRICS_CSV.exists():
        with METRICS_CSV.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)[-50:]  # Last 50 runs
            tes_values = [float(r.get("tes", 0)) for r in rows if r.get("tes")]
    
    if not tes_values:
        return {"status": "insufficient_data"}
    
    # Simple trend analysis
    recent_avg = sum(tes_values[-10:]) / len(tes_values[-10:])
    older_avg = sum(tes_values[:-10]) / len(tes_values[:-10]) if len(tes_values) > 10 else recent_avg
    
    trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
    
    # Forecast next hour
    forecast_tes = recent_avg * 1.02 if trend == "improving" else recent_avg * 0.98 if trend == "declining" else recent_avg
    
    forecast = {
        "current_tes": recent_avg,
        "trend": trend,
        "forecast_1h": forecast_tes,
        "confidence": 0.75,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return forecast


def check_pending_queries() -> None:
    """Check and respond to pending queries"""
    if not SVF_AVAILABLE:
        return
    
    queries = get_pending_queries("cp15")
    
    for query in queries:
        if query.get("to") == "cp15":
            question = query.get("question", "")
            
            if "tes" in question.lower() or "forecast" in question.lower():
                forecast = generate_forecast()
                respond_to_query(
                    query_id=query.get("query_id"),
                    responder="cp15",
                    answer=f"Current TES average: {forecast.get('current_tes', 0):.1f}, Trend: {forecast.get('trend')}, Forecast 1h: {forecast.get('forecast_1h', 0):.1f}",
                    data=forecast
                )
                log_communication("cp15", "respond", query.get("from"), "TES forecast", "success")


def run_forecast_cycle() -> Dict[str, Any]:
    """Run forecasting cycle"""
    forecast = generate_forecast()
    
    # Check if should report
    should_send = True
    if SVF_AVAILABLE:
        should_send = should_report("cp15", trigger_event="forecast_generated")
    
    # Check pending queries
    check_pending_queries()
    
    # Report if needed
    if should_send and forecast.get("status") != "insufficient_data":
        trend = forecast.get("trend", "stable")
        
        if trend == "declining":
            priority = "high"
            channel = "standard"
        else:
            priority = "medium"
            channel = "casual"
        
        if SVF_AVAILABLE:
            send_message(
                sender="cp15",
                message=f"TES Forecast: {forecast.get('forecast_1h', 0):.1f} (trend: {trend})",
                channel=channel,
                priority=priority,
                context=forecast
            )
            log_communication("cp15", "forecast", channel, f"Trend: {trend}", "success")
    
    # Increment cycle
    if SVF_AVAILABLE:
        increment_cycle("cp15")
    
    return forecast


def main():
    parser = argparse.ArgumentParser(description="CP15 Prophet - Predictive Analytics Agent")
    parser.add_argument("--interval", type=float, default=300.0, help="Update interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    # Register with SVF v2.0
    if SVF_AVAILABLE:
        register_agent(
            agent_name="cp15",
            capabilities=["forecasting", "trend_analysis", "risk_assessment"],
            data_sources=["logs/enhanced_metrics.jsonl", "logs/predictive_forecasts.jsonl", "logs/agent_metrics.csv"],
            update_frequency="300s",
            contact_policy="respond_to_queries"
        )
        
        announce_presence(
            agent_name="cp15",
            version="1.0.0",
            status="running",
            capabilities=["forecasting", "trend_analysis", "risk_assessment"],
            uptime_seconds=0.0
        )
    
    print("CP15 Prophet started")
    
    def _shutdown(*args):
        _write_hb("shutdown", status="done")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    
    try:
        while True:
            forecast = run_forecast_cycle()
            
            status_msg = f"Forecast: TES trend {forecast.get('trend', 'unknown')}"
            status = "running"
            
            _write_hb("forecasting", status=status, extra={
                "status_message": status_msg,
                "forecast": forecast
            })
            
            if args.once:
                break
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        _shutdown()


if __name__ == "__main__":
    main()

