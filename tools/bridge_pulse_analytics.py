#!/usr/bin/env python3
"""
Bridge Pulse Analytics - Phase II Track D
Parse Bridge Pulse logs, generate trend analysis, feed insights to memory store.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
TRENDS_DIR = REPORTS_DIR / "trends"


class BridgePulseAnalytics:
    """Analyze Bridge Pulse reports and generate trend insights."""
    
    def __init__(self):
        self.reports_dir = REPORTS_DIR
        self.trends_dir = TRENDS_DIR
        self.trends_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_bridge_pulse(self, report_path: Path) -> Optional[Dict[str, Any]]:
        """Parse a Bridge Pulse report file."""
        try:
            content = report_path.read_text(encoding='utf-8')
            
            # Extract key metrics with regex
            metrics = {}
            
            # Timestamp
            ts_match = re.search(r'Timestamp: (.+)', content)
            if ts_match:
                metrics['timestamp'] = ts_match.group(1)
            
            # Pulse ID
            pulse_match = re.search(r'Pulse ID: (.+)', content)
            if pulse_match:
                metrics['pulse_id'] = pulse_match.group(1)
            
            # CPU
            cpu_match = re.search(r'CPU Load Avg\s+\|\s+([\d.]+)%', content)
            if cpu_match:
                metrics['cpu'] = float(cpu_match.group(1))
            
            # RAM
            ram_match = re.search(r'RAM Utilization\s+\|\s+([\d.]+)%', content)
            if ram_match:
                metrics['ram'] = float(ram_match.group(1))
            
            # TES
            tes_match = re.search(r'Mean TES\s+\|\s+([\d.]+)', content)
            if tes_match:
                metrics['tes'] = float(tes_match.group(1))
            
            # Uptime
            uptime_match = re.search(r'Uptime \(24h rolling\)\s+\|\s+([\d.]+)%', content)
            if uptime_match:
                metrics['uptime'] = float(uptime_match.group(1))
            
            # Overall status
            status_match = re.search(r'Overall status: (\w+)', content)
            if status_match:
                metrics['status'] = status_match.group(1)
            
            return metrics if metrics else None
            
        except Exception as e:
            print(f"[Analytics] Error parsing {report_path}: {e}")
            return None
    
    def analyze_trends(self, num_pulses: int = 20) -> Dict[str, Any]:
        """Analyze trends from recent Bridge Pulse reports."""
        pulse_files = sorted(self.reports_dir.glob("bridge_pulse_bp-*.md"), reverse=True)[:num_pulses]
        
        pulses = []
        for pulse_file in pulse_files:
            metrics = self.parse_bridge_pulse(pulse_file)
            if metrics:
                pulses.append(metrics)
        
        if not pulses:
            return {
                'error': 'No pulses found',
                'total_pulses': 0,
                'pulses': [],
                'trends': {},
                'summary': 'No data available'
            }
        
        # Calculate trends
        trends = {
            'cpu': {
                'latest': pulses[0].get('cpu'),
                'avg': sum(p.get('cpu', 0) for p in pulses) / len(pulses),
                'min': min(p.get('cpu', 0) for p in pulses),
                'max': max(p.get('cpu', 0) for p in pulses),
                'trend': 'stable' if abs(pulses[0].get('cpu', 0) - pulses[-1].get('cpu', 0)) < 5 else
                         'increasing' if pulses[0].get('cpu', 0) > pulses[-1].get('cpu', 0) else 'decreasing'
            },
            'ram': {
                'latest': pulses[0].get('ram'),
                'avg': sum(p.get('ram', 0) for p in pulses) / len(pulses),
                'min': min(p.get('ram', 0) for p in pulses),
                'max': max(p.get('ram', 0) for p in pulses),
                'trend': 'stable' if abs(pulses[0].get('ram', 0) - pulses[-1].get('ram', 0)) < 5 else
                         'increasing' if pulses[0].get('ram', 0) > pulses[-1].get('ram', 0) else 'decreasing'
            },
            'tes': {
                'latest': pulses[0].get('tes'),
                'avg': sum(p.get('tes', 0) for p in pulses) / len(pulses),
                'min': min(p.get('tes', 0) for p in pulses),
                'max': max(p.get('tes', 0) for p in pulses),
                'trend': 'stable' if abs(pulses[0].get('tes', 0) - pulses[-1].get('tes', 0)) < 3 else
                         'improving' if pulses[0].get('tes', 0) > pulses[-1].get('tes', 0) else 'declining'
            },
            'uptime': {
                'latest': pulses[0].get('uptime'),
                'avg': sum(p.get('uptime', 0) for p in pulses) / len(pulses),
                'min': min(p.get('uptime', 0) for p in pulses),
                'max': max(p.get('uptime', 0) for p in pulses)
            }
        }
        
        return {
            'total_pulses': len(pulses),
            'pulses': pulses,
            'trends': trends,
            'summary': self._generate_summary(trends)
        }
    
    def _generate_summary(self, trends: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        cpu_trend = trends['cpu']['trend']
        ram_trend = trends['ram']['trend']
        tes_trend = trends['tes']['trend']
        
        lines = [
            f"CPU: {trends['cpu']['latest']:.1f}% ({cpu_trend})",
            f"RAM: {trends['ram']['latest']:.1f}% ({ram_trend})",
            f"TES: {trends['tes']['latest']:.1f} ({tes_trend})",
            f"Uptime: {trends['uptime']['latest']:.1f}%"
        ]
        
        return " | ".join(lines)
    
    def save_trend_report(self, analysis: Dict[str, Any]) -> Path:
        """Save trend analysis to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.trends_dir / f"trends_{timestamp}.json"
        
        report_path.write_text(json.dumps(analysis, indent=2))
        return report_path


def main():
    """Test the analytics implementation."""
    print("[Analytics] Testing Bridge Pulse Analytics...")
    
    analytics = BridgePulseAnalytics()
    
    # Analyze trends
    print("\n[Test] Analyzing trends...")
    analysis = analytics.analyze_trends(num_pulses=10)
    
    if 'error' in analysis:
        print(f"  Error: {analysis['error']}")
    else:
        print(f"  [OK] Analyzed {analysis['total_pulses']} pulses")
        print(f"  Summary: {analysis['summary']}")
        
        # Save report
        report_path = analytics.save_trend_report(analysis)
        print(f"  [OK] Saved report: {report_path}")
    
    print("\n[Analytics] [OK] Tests complete!")


if __name__ == "__main__":
    main()

