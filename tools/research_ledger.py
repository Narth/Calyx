#!/usr/bin/env python3
"""
Research Ledger - Database management for Station Calyx learning loop
Tracks experiments, runs, RFCs, playbooks, and KPIs
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = ROOT / "research"
LEDGER_DB = RESEARCH_DIR / "ledger.sqlite"
SCHEMA_FILE = RESEARCH_DIR / "ledger.schema.sql"


class ResearchLedger:
    """Manage research database for experiments and learning loop."""
    
    def __init__(self, db_path: Path = LEDGER_DB):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with schema if it doesn't exist."""
        if not self.db_path.exists():
            # Read schema from file
            with open(SCHEMA_FILE, 'r') as f:
                schema = f.read()
            
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.executescript(schema)
            self.conn.commit()
            print(f"[ResearchLedger] Created new database: {self.db_path}")
        else:
            self.conn = sqlite3.connect(str(self.db_path))
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def record_experiment(self, exp_data: Dict[str, Any]) -> str:
        """Record a new experiment."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO experiments 
            (id, title, hypothesis, domain, metrics, safety, success_criteria, owner, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_data['id'],
            exp_data['title'],
            exp_data['hypothesis'],
            exp_data['domain'],
            json.dumps(exp_data['metrics']),
            json.dumps(exp_data['safety']),
            exp_data['success_criteria'],
            exp_data['owner'],
            exp_data.get('notes', '')
        ))
        self.conn.commit()
        return exp_data['id']
    
    def update_experiment_status(self, exp_id: str, status: str, notes: str = "") -> None:
        """Update experiment status."""
        cursor = self.conn.cursor()
        if status in ('completed', 'failed'):
            cursor.execute("""
                UPDATE experiments 
                SET status = ?, completed_at = julianday('now'), notes = notes || '\n' || ?
                WHERE id = ?
            """, (status, notes, exp_id))
        else:
            cursor.execute("""
                UPDATE experiments 
                SET status = ?, notes = notes || '\n' || ?
                WHERE id = ?
            """, (status, notes, exp_id))
        self.conn.commit()
    
    def record_run(self, exp_id: str, config: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> int:
        """Record an experiment run."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO runs (exp_id, config, result, status)
            VALUES (?, ?, ?, ?)
        """, (
            exp_id,
            json.dumps(config),
            json.dumps(result) if result else None,
            'completed' if result else 'running'
        ))
        run_id = cursor.lastrowid
        self.conn.commit()
        return run_id
    
    def record_incident(self, incident_type: str, ttrc_minutes: float, resolution_notes: str) -> int:
        """Record an incident with TTRC."""
        cursor = self.conn.cursor()
        now = time.time()
        cursor.execute("""
            INSERT INTO incidents (incident_type, detected_at, root_cause_identified_at, resolution_at, ttrc_minutes, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (incident_type, now, now, now, ttrc_minutes, resolution_notes))
        incident_id = cursor.lastrowid
        self.conn.commit()
        return incident_id
    
    def calculate_kpis(self) -> Dict[str, Any]:
        """Calculate research KPIs."""
        cursor = self.conn.cursor()
        
        # Plan→Exec Fidelity (completed_without_replan / total)
        cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM runs")
        total = cursor.fetchone()[0]
        fidelity = completed / total if total > 0 else 0.0
        
        # Hypothesis Win Rate (experiments meeting success / total)
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'completed'")
        successful_exps = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status IN ('completed', 'failed')")
        total_exps = cursor.fetchone()[0]
        win_rate = successful_exps / total_exps if total_exps > 0 else 0.0
        
        # Contradictions rate
        cursor.execute("SELECT COUNT(*) FROM contradictions WHERE resolved = 0")
        unresolved = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM contradictions")
        total_contradictions = cursor.fetchone()[0]
        contradiction_rate = unresolved / total_contradictions if total_contradictions > 0 else 0.0
        
        # TTRC (average time-to-root-cause)
        cursor.execute("SELECT AVG(ttrc_minutes) FROM incidents WHERE ttrc_minutes IS NOT NULL")
        avg_ttrc = cursor.fetchone()[0] or 0.0
        
        # Regret rate (rollbacks / total changes)
        cursor.execute("SELECT COUNT(*) FROM runs WHERE status = 'rolled_back'")
        rollbacks = cursor.fetchone()[0]
        regret_rate = rollbacks / total if total > 0 else 0.0
        
        return {
            'plan_exec_fidelity': round(fidelity, 3),
            'hypothesis_win_rate': round(win_rate, 3),
            'contradiction_rate': round(contradiction_rate, 3),
            'avg_ttrc_minutes': round(avg_ttrc, 2),
            'regret_rate': round(regret_rate, 3)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ledger statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Experiments
        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats['total_experiments'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM experiments WHERE status = 'running'")
        stats['active_experiments'] = cursor.fetchone()[0]
        
        # Runs
        cursor.execute("SELECT COUNT(*) FROM runs")
        stats['total_runs'] = cursor.fetchone()[0]
        
        # RFCs
        cursor.execute("SELECT COUNT(*) FROM rfcs")
        stats['total_rfcs'] = cursor.fetchone()[0]
        
        # Playbooks
        cursor.execute("SELECT COUNT(*) FROM playbooks")
        stats['total_playbooks'] = cursor.fetchone()[0]
        
        # Incidents
        cursor.execute("SELECT COUNT(*) FROM incidents")
        stats['total_incidents'] = cursor.fetchone()[0]
        
        return stats


def main():
    """Test the research ledger."""
    print("[ResearchLedger] Testing research ledger...")
    
    ledger = ResearchLedger()
    
    # Test: Record experiment
    print("\n[Test] Recording sample experiment...")
    exp_id = ledger.record_experiment({
        'id': 'EXP-TEST-001',
        'title': 'Test Experiment',
        'hypothesis': 'Testing research ledger functionality',
        'domain': 'infrastructure',
        'metrics': {'primary': {'name': 'test_metric', 'baseline': 1.0, 'target': 0.8}},
        'safety': {'offline_only': True},
        'success_criteria': 'Functionality verified',
        'owner': 'cheetah',
        'notes': 'Initial test'
    })
    print(f"  [OK] Recorded experiment: {exp_id}")
    
    # Test: Calculate KPIs
    print("\n[Test] Calculating KPIs...")
    kpis = ledger.calculate_kpis()
    print(f"  [OK] Plan->Exec Fidelity: {kpis['plan_exec_fidelity']}")
    print(f"  [OK] Hypothesis Win Rate: {kpis['hypothesis_win_rate']}")
    print(f"  [OK] Contradiction Rate: {kpis['contradiction_rate']}")
    print(f"  [OK] Avg TTRC: {kpis['avg_ttrc_minutes']}m")
    print(f"  [OK] Regret Rate: {kpis['regret_rate']}")
    
    # Test: Statistics
    print("\n[Test] Getting statistics...")
    stats = ledger.get_statistics()
    print(f"  [OK] Total experiments: {stats['total_experiments']}")
    print(f"  [OK] Total runs: {stats['total_runs']}")
    
    ledger.close()
    print("\n[ResearchLedger] [OK] All tests passed!")


if __name__ == "__main__":
    main()

