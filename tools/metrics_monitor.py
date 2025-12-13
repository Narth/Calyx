#!/usr/bin/env python3
"""
Metrics Monitor - Continuous TES and Capacity Score Tracking
Monitors TES trends and capacity metrics for Phase II conditional track activation.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"


class MetricsMonitor:
    """Monitor TES and capacity scores for system health assessment."""
    
    def __init__(self):
        self.state_dir = STATE_DIR
        self.logs_dir = LOGS_DIR
        self.metrics_file = STATE_DIR / "metrics_tracking.json"
    
    def load_tracking_data(self) -> Dict[str, Any]:
        """Load metrics tracking data."""
        if self.metrics_file.exists():
            return json.loads(self.metrics_file.read_text())
        return {
            'tes_history': [],
            'capacity_history': [],
            'pulse_count': 0,
            'last_update': None
        }
    
    def save_tracking_data(self, data: Dict[str, Any]) -> None:
        """Save metrics tracking data."""
        data['last_update'] = datetime.now().isoformat()
        self.metrics_file.write_text(json.dumps(data, indent=2))
    
    def get_latest_tes(self) -> Optional[float]:
        """Get latest TES score from agent metrics."""
        metrics_file = self.logs_dir / "agent_metrics.csv"
        if not metrics_file.exists():
            return None
        
        try:
            with open(metrics_file, 'r') as f:
                lines = f.readlines()
                if len(lines) < 2:
                    return None
                
                # Get last line
                last_line = lines[-1].strip()
                parts = last_line.split(',')
                
                # TES is typically column 1 or 2
                if len(parts) > 1:
                    try:
                        return float(parts[1])
                    except (ValueError, IndexError):
                        return None
        except Exception:
            return None
        
        return None
    
    def calculate_capacity_score(self, cpu: float, ram: float) -> float:
        """Calculate capacity score from CPU and RAM metrics."""
        # Simple headroom calculation: higher score = more capacity
        cpu_headroom = max(0, 1 - (cpu / 100))
        ram_headroom = max(0, 1 - (ram / 100))
        
        # Average of both (can be weighted)
        capacity_score = (cpu_headroom + ram_headroom) / 2
        return round(capacity_score, 3)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            
            return {
                'cpu': cpu,
                'ram': mem.percent,
                'ram_available_gb': mem.available / (1024**3),
                'capacity_score': self.calculate_capacity_score(cpu, mem.percent)
            }
        except Exception as e:
            print(f"[MetricsMonitor] Error getting system metrics: {e}")
            return {}
    
    def update_metrics(self) -> Dict[str, Any]:
        """Update metrics tracking."""
        data = self.load_tracking_data()
        
        # Get current metrics
        tes = self.get_latest_tes()
        system_metrics = self.get_system_metrics()
        
        # Add to history
        timestamp = time.time()
        
        if tes is not None:
            data['tes_history'].append({
                'timestamp': timestamp,
                'tes': tes
            })
            # Keep last 100 entries
            data['tes_history'] = data['tes_history'][-100:]
        
        if system_metrics:
            data['capacity_history'].append({
                'timestamp': timestamp,
                'capacity_score': system_metrics.get('capacity_score'),
                'cpu': system_metrics.get('cpu'),
                'ram': system_metrics.get('ram')
            })
            # Keep last 100 entries
            data['capacity_history'] = data['capacity_history'][-100:]
        
        data['pulse_count'] += 1
        
        self.save_tracking_data(data)
        
        return {
            'tes': tes,
            'capacity_score': system_metrics.get('capacity_score'),
            'cpu': system_metrics.get('cpu'),
            'ram': system_metrics.get('ram'),
            'pulse_count': data['pulse_count']
        }
    
    def analyze_tes_trend(self, history: List[Dict[str, Any]], lookback: int = 10) -> Dict[str, Any]:
        """Analyze TES trend over recent pulses."""
        if len(history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent = history[-lookback:]
        tes_values = [h['tes'] for h in recent if 'tes' in h]
        
        if len(tes_values) < 2:
            return {'trend': 'insufficient_data'}
        
        latest = tes_values[-1]
        previous = tes_values[0]
        
        delta = latest - previous
        trend = 'stable' if abs(delta) < 2 else ('improving' if delta > 0 else 'declining')
        
        return {
            'trend': trend,
            'latest': latest,
            'avg': sum(tes_values) / len(tes_values),
            'min': min(tes_values),
            'max': max(tes_values),
            'delta': delta,
            'samples': len(tes_values)
        }
    
    def check_track_eligibility(self) -> Dict[str, Any]:
        """Check eligibility for conditional tracks (B, C, F)."""
        data = self.load_tracking_data()
        
        # Analyze TES trend
        tes_analysis = self.analyze_tes_trend(data.get('tes_history', []))
        
        # Get current capacity
        current_metrics = self.get_system_metrics()
        capacity_score = current_metrics.get('capacity_score', 0)
        
        # Track B eligibility: TES ≥95 for 5 pulses
        track_b_eligible = (
            tes_analysis.get('trend') == 'improving' and
            tes_analysis.get('latest', 0) >= 95 and
            tes_analysis.get('samples', 0) >= 5
        )
        
        # Track C eligibility: CPU <50%, RAM <75%, capacity >0.5
        track_c_eligible = (
            current_metrics.get('cpu', 100) < 50 and
            current_metrics.get('ram', 100) < 75 and
            capacity_score > 0.5
        )
        
        # Track F eligibility: Track C must be active
        track_f_eligible = track_c_eligible
        
        return {
            'track_b': {
                'eligible': track_b_eligible,
                'reason': 'TES improvement and capacity sufficient' if track_b_eligible else 'TES below 95 or insufficient data',
                'tes_latest': tes_analysis.get('latest'),
                'tes_trend': tes_analysis.get('trend')
            },
            'track_c': {
                'eligible': track_c_eligible,
                'reason': 'CPU, RAM, and capacity within thresholds' if track_c_eligible else f'CPU: {current_metrics.get("cpu"):.1f}%, RAM: {current_metrics.get("ram"):.1f}%, Capacity: {capacity_score:.3f}',
                'capacity_score': capacity_score
            },
            'track_f': {
                'eligible': track_f_eligible,
                'reason': 'Available when Track C active' if track_c_eligible else 'Blocked by Track C requirement'
            }
        }


def main():
    """Test the metrics monitor."""
    print("[MetricsMonitor] Testing metrics monitoring...")
    
    monitor = MetricsMonitor()
    
    # Update metrics
    print("\n[Test] Updating metrics...")
    current = monitor.update_metrics()
    print(f"  TES: {current.get('tes')}")
    print(f"  Capacity Score: {current.get('capacity_score')}")
    print(f"  CPU: {current.get('cpu'):.1f}%")
    print(f"  RAM: {current.get('ram'):.1f}%")
    
    # Check eligibility
    print("\n[Test] Checking track eligibility...")
    eligibility = monitor.check_track_eligibility()
    
    print(f"  Track B: {'ELIGIBLE' if eligibility['track_b']['eligible'] else 'DEFERRED'}")
    print(f"    Reason: {eligibility['track_b']['reason']}")
    
    print(f"  Track C: {'ELIGIBLE' if eligibility['track_c']['eligible'] else 'DEFERRED'}")
    print(f"    Reason: {eligibility['track_c']['reason']}")
    
    print(f"  Track F: {'ELIGIBLE' if eligibility['track_f']['eligible'] else 'DEFERRED'}")
    print(f"    Reason: {eligibility['track_f']['reason']}")
    
    print("\n[MetricsMonitor] [OK] Tests complete!")


if __name__ == "__main__":
    main()

