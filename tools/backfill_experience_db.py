#!/usr/bin/env python3
"""Backfill experience database with recent Bridge Pulse data"""
import sys
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from memory_loop import MemoryLoop

ROOT = Path(__file__).resolve().parents[1]

def main():
    print("Backfilling experience database with recent Bridge Pulse data...")
    
    ml = MemoryLoop()
    
    # Recent Bridge Pulse data (manually extracted to avoid encoding issues)
    pulses = [
        {
            "pulse_id": "bp-0007",
            "summary": "TES scoring fixed with graduated stability",
            "cpu": 20.7,
            "ram": 81.5,
            "tes": 76.6,
            "confidence_delta": 5.2,
            "outcome": "success"
        },
        {
            "pulse_id": "bp-0006",
            "summary": "Research infrastructure activated",
            "cpu": 20.7,
            "ram": 81.5,
            "tes": 46.6,
            "confidence_delta": 2.8,
            "outcome": "success"
        },
        {
            "pulse_id": "bp-0005",
            "summary": "Phase II foundation tracks operational",
            "cpu": 23.3,
            "ram": 78.1,
            "tes": 89.1,
            "confidence_delta": 2.5,
            "outcome": "success"
        },
        {
            "pulse_id": "bp-0004",
            "summary": "Phase II implementation status",
            "cpu": 16.0,
            "ram": 76.1,
            "tes": 92.6,
            "confidence_delta": 1.8,
            "outcome": "success"
        },
        {
            "pulse_id": "bp-cleanup",
            "summary": "System cleanup operations",
            "cpu": 23.2,
            "ram": 72.0,
            "tes": 89.1,
            "confidence_delta": 1.5,
            "outcome": "success"
        },
        {
            "pulse_id": "bp-diagnostic",
            "summary": "Diagnostic pulse",
            "cpu": 8.7,
            "ram": 77.3,
            "tes": 89.1,
            "confidence_delta": 1.0,
            "outcome": "success"
        }
    ]
    
    added = 0
    for pulse in pulses:
        try:
            # Check if already exists
            cursor = ml.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM event WHERE pulse_id = ?", (pulse['pulse_id'],))
            if cursor.fetchone()[0] > 0:
                continue
            
            ml.record_bridge_pulse(
                pulse_id=pulse['pulse_id'],
                timestamp=time.time(),
                summary=pulse['summary'],
                cpu_pct=pulse['cpu'],
                ram_pct=pulse['ram'],
                gpu_pct=None,
                capacity_score=0.489,
                autonomy_mode="guide",
                active_agents=7,
                gates_state={"network": True, "llm": True, "cbo_authority": True},
                tes_score=pulse['tes'],
                confidence_delta=pulse['confidence_delta'],
                outcome=pulse['outcome']
            )
            added += 1
            print(f"Added pulse {pulse['pulse_id']}")
        except Exception as e:
            print(f"Error adding {pulse['pulse_id']}: {e}")
    
    ml.close()
    print(f"\nAdded {added} new pulse records")

if __name__ == "__main__":
    main()

