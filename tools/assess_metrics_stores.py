#!/usr/bin/env python3
"""
Assess Station Calyx Metrics Stores
Audit all databases and data stores for autonomy/intelligence metrics
"""
import sqlite3
import csv
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def check_experience_db():
    """Check experience.sqlite database"""
    db_path = ROOT / "memory" / "experience.sqlite"
    if not db_path.exists():
        return {"exists": False, "tables": [], "records": 0}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) FROM event")
    event_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM confidence")
    confidence_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "exists": True,
        "tables": tables,
        "event_records": event_count,
        "confidence_records": confidence_count
    }

def check_research_ledger():
    """Check research ledger.sqlite database"""
    db_path = ROOT / "research" / "ledger.sqlite"
    if not db_path.exists():
        return {"exists": False, "tables": [], "records": 0}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*) FROM experiments")
    exp_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM runs")
    runs_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "exists": True,
        "tables": tables,
        "experiments": exp_count,
        "runs": runs_count
    }

def check_agent_metrics():
    """Check agent_metrics.csv"""
    csv_path = ROOT / "logs" / "agent_metrics.csv"
    if not csv_path.exists():
        return {"exists": False, "records": 0}
    
    count = 0
    latest = None
    with csv_path.open('r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            count += 1
            latest = row
    
    return {
        "exists": True,
        "records": count,
        "latest": latest
    }

def check_system_snapshots():
    """Check system_snapshots.jsonl"""
    jsonl_path = ROOT / "logs" / "system_snapshots.jsonl"
    if not jsonl_path.exists():
        return {"exists": False, "records": 0}
    
    count = 0
    with jsonl_path.open('r') as f:
        for line in f:
            if line.strip():
                count += 1
    
    return {
        "exists": True,
        "records": count
    }

def check_capacity_alerts():
    """Check capacity_alerts.jsonl"""
    jsonl_path = ROOT / "logs" / "capacity_alerts.jsonl"
    if not jsonl_path.exists():
        return {"exists": False, "records": 0}
    
    count = 0
    latest = None
    with jsonl_path.open('r') as f:
        for line in f:
            if line.strip():
                count += 1
                latest = json.loads(line)
    
    return {
        "exists": True,
        "records": count,
        "latest": latest
    }

def main():
    print("="*80)
    print("Station Calyx Metrics Stores Assessment")
    print("="*80)
    print()
    
    results = {}
    
    # Check experience database
    print("1. Experience Database (memory/experience.sqlite)")
    print("-" * 80)
    exp_db = check_experience_db()
    results['experience_db'] = exp_db
    if exp_db['exists']:
        print(f"   Tables: {', '.join(exp_db['tables'])}")
        print(f"   Events: {exp_db['event_records']}")
        print(f"   Confidence: {exp_db['confidence_records']}")
    else:
        print("   Status: NOT CREATED")
    print()
    
    # Check research ledger
    print("2. Research Ledger (research/ledger.sqlite)")
    print("-" * 80)
    research_db = check_research_ledger()
    results['research_ledger'] = research_db
    if research_db['exists']:
        print(f"   Tables: {', '.join(research_db['tables'])}")
        print(f"   Experiments: {research_db['experiments']}")
        print(f"   Runs: {research_db['runs']}")
    else:
        print("   Status: NOT CREATED")
    print()
    
    # Check agent metrics
    print("3. Agent Metrics (logs/agent_metrics.csv)")
    print("-" * 80)
    agent_metrics = check_agent_metrics()
    results['agent_metrics'] = agent_metrics
    if agent_metrics['exists']:
        print(f"   Records: {agent_metrics['records']}")
        if agent_metrics['latest']:
            print(f"   Latest TES: {agent_metrics['latest'].get('tes', 'N/A')}")
            print(f"   Latest Mode: {agent_metrics['latest'].get('autonomy_mode', 'N/A')}")
    else:
        print("   Status: NOT FOUND")
    print()
    
    # Check system snapshots
    print("4. System Snapshots (logs/system_snapshots.jsonl)")
    print("-" * 80)
    snapshots = check_system_snapshots()
    results['snapshots'] = snapshots
    if snapshots['exists']:
        print(f"   Records: {snapshots['records']}")
    else:
        print("   Status: NOT FOUND")
    print()
    
    # Check capacity alerts
    print("5. Capacity Alerts (logs/capacity_alerts.jsonl)")
    print("-" * 80)
    alerts = check_capacity_alerts()
    results['alerts'] = alerts
    if alerts['exists']:
        print(f"   Records: {alerts['records']}")
        if alerts['latest']:
            print(f"   Latest CPU: {alerts['latest'].get('cpu_pct', 'N/A')}%")
            print(f"   Latest RAM: {alerts['latest'].get('ram_pct', 'N/A')}%")
    else:
        print("   Status: NOT FOUND")
    print()
    
    # Summary
    print("="*80)
    print("Assessment Summary")
    print("="*80)
    
    total_records = (
        (exp_db.get('event_records', 0) or 0) +
        (research_db.get('experiments', 0) or 0) +
        (agent_metrics.get('records', 0) or 0) +
        (snapshots.get('records', 0) or 0) +
        (alerts.get('records', 0) or 0)
    )
    
    print(f"Total historical records: {total_records}")
    print(f"Experience DB operational: {exp_db['exists']}")
    print(f"Research Ledger operational: {research_db['exists']}")
    print(f"Agent metrics tracking: {agent_metrics['exists']}")
    print()
    
    # Recommendations
    print("Recommendations:")
    if not exp_db['exists'] or exp_db['event_records'] == 0:
        print("  ⚠️  Initialize experience.sqlite with first Bridge Pulse")
    if not research_db['exists']:
        print("  ⚠️  Initialize research ledger.sqlite")
    if agent_metrics['exists'] and agent_metrics['records'] > 0:
        print("  ✅ Agent metrics tracking active")
    print()
    
    return results

if __name__ == "__main__":
    main()

