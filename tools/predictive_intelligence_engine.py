#!/usr/bin/env python3
"""
Predictive Intelligence Engine — Phase III Track A
Predictive capabilities for proactive decision-making in Station Calyx
"""
import json
import csv
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import deque
import statistics

ROOT = Path(__file__).resolve().parents[1]

class PredictiveIntelligenceEngine:
    """Predictive intelligence for proactive Station Calyx operation"""
    
    def __init__(self):
        self.root = ROOT
        self.metrics_history = deque(maxlen=100)
        self.prediction_history = []
        
    def _load_tes_history(self) -> List[Dict[str, Any]]:
        """Load TES history from agent_metrics.csv"""
        tes_history = []
        csv_path = self.root / "logs" / "agent_metrics.csv"
        
        if not csv_path.exists():
            return tes_history
        
        try:
            with csv_path.open('r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        tes_history.append({
                            'timestamp': row.get('iso_ts', ''),
                            'tes': float(row.get('tes', 0)),
                            'mode': row.get('autonomy_mode', 'safe')
                        })
                    except:
                        continue
        except Exception as e:
            print(f"Error loading TES history: {e}")
        
        return tes_history[-50:]  # Last 50 runs
    
    def _load_resource_history(self) -> List[Dict[str, Any]]:
        """Load resource history from system_snapshots.jsonl"""
        resource_history = []
        jsonl_path = self.root / "logs" / "system_snapshots.jsonl"
        
        if not jsonl_path.exists():
            return resource_history
        
        try:
            with jsonl_path.open('r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        resource_history.append({
                            'timestamp': data.get('timestamp', ''),
                            'cpu_pct': data.get('cpu_pct', 0),
                            'ram_pct': data.get('ram_pct', 0)
                        })
        except Exception as e:
            print(f"Error loading resource history: {e}")
        
        return resource_history[-100:]  # Last 100 snapshots
    
    def predict_tes_trend(self, horizon_minutes: int = 60) -> Dict[str, Any]:
        """Predict TES trend over next N minutes"""
        tes_history = self._load_tes_history()
        
        if len(tes_history) < 10:
            return {'confidence': 0.0, 'trend': 'insufficient_data'}
        
        recent_tes = [h['tes'] for h in tes_history[-20:]]
        
        # Simple trend analysis
        trend = 'stable'
        if len(recent_tes) >= 2:
            avg_first_half = statistics.mean(recent_tes[:len(recent_tes)//2])
            avg_second_half = statistics.mean(recent_tes[len(recent_tes)//2:])
            
            if avg_second_half > avg_first_half * 1.05:
                trend = 'improving'
            elif avg_second_half < avg_first_half * 0.95:
                trend = 'declining'
        
        # Predict future TES
        current_tes = recent_tes[-1]
        predicted_tes = current_tes
        
        if trend == 'improving':
            predicted_tes = current_tes * 1.02  # 2% improvement
        elif trend == 'declining':
            predicted_tes = current_tes * 0.98  # 2% decline
        
        confidence = 0.7 if len(recent_tes) >= 20 else 0.5
        
        return {
            'trend': trend,
            'current_tes': current_tes,
            'predicted_tes': round(predicted_tes, 1),
            'confidence': confidence,
            'horizon_minutes': horizon_minutes
        }
    
    def predict_resource_constraints(self, horizon_minutes: int = 120) -> Dict[str, Any]:
        """Predict resource constraints over next N minutes"""
        resource_history = self._load_resource_history()
        
        if len(resource_history) < 20:
            return {'confidence': 0.0, 'constraints': []}
        
        recent_cpu = [h['cpu_pct'] for h in resource_history[-30:]]
        recent_ram = [h['ram_pct'] for h in resource_history[-30:]]
        
        constraints = []
        
        # CPU constraint prediction
        avg_cpu = statistics.mean(recent_cpu)
        cpu_trend = 'stable'
        if len(recent_cpu) >= 2:
            if recent_cpu[-1] > recent_cpu[-2]:
                cpu_trend = 'increasing'
            elif recent_cpu[-1] < recent_cpu[-2]:
                cpu_trend = 'decreasing'
        
        predicted_cpu = avg_cpu
        if cpu_trend == 'increasing':
            predicted_cpu = avg_cpu * 1.05
        
        if predicted_cpu > 50:
            constraints.append({
                'resource': 'CPU',
                'current': recent_cpu[-1],
                'predicted': round(predicted_cpu, 1),
                'threshold': 50,
                'risk': 'high' if predicted_cpu > 60 else 'medium',
                'time_horizon_minutes': horizon_minutes
            })
        
        # RAM constraint prediction
        avg_ram = statistics.mean(recent_ram)
        ram_trend = 'stable'
        if len(recent_ram) >= 2:
            if recent_ram[-1] > recent_ram[-2]:
                ram_trend = 'increasing'
            elif recent_ram[-1] < recent_ram[-2]:
                ram_trend = 'decreasing'
        
        predicted_ram = avg_ram
        if ram_trend == 'increasing':
            predicted_ram = avg_ram * 1.02
        
        if predicted_ram > 80:
            constraints.append({
                'resource': 'RAM',
                'current': recent_ram[-1],
                'predicted': round(predicted_ram, 1),
                'threshold': 80,
                'risk': 'high' if predicted_ram > 85 else 'medium',
                'time_horizon_minutes': horizon_minutes
            })
        
        confidence = 0.75 if len(resource_history) >= 50 else 0.6
        
        return {
            'constraints': constraints,
            'confidence': confidence,
            'horizon_minutes': horizon_minutes
        }
    
    def predict_failures(self) -> Dict[str, Any]:
        """Predict potential system failures"""
        tes_history = self._load_tes_history()
        resource_history = self._load_resource_history()
        
        predictions = []
        
        # TES failure prediction
        if len(tes_history) >= 10:
            recent_tes = [h['tes'] for h in tes_history[-10:]]
            if len(recent_tes) >= 3:
                if all(t < 50 for t in recent_tes[-3:]):
                    predictions.append({
                        'type': 'TES degradation',
                        'probability': 0.7,
                        'severity': 'medium',
                        'symptoms': ['Consecutive low TES scores'],
                        'recommendation': 'Review recent agent runs, check for systematic failures'
                    })
        
        # Resource exhaustion prediction
        if len(resource_history) >= 20:
            recent_cpu = [h['cpu_pct'] for h in resource_history[-20:]]
            recent_ram = [h['ram_pct'] for h in resource_history[-20:]]
            
            if statistics.mean(recent_cpu) > 60:
                predictions.append({
                    'type': 'CPU exhaustion',
                    'probability': 0.6,
                    'severity': 'high',
                    'symptoms': ['High CPU load sustained'],
                    'recommendation': 'Reduce teaching intensity, defer non-critical tasks'
                })
            
            if statistics.mean(recent_ram) > 85:
                predictions.append({
                    'type': 'RAM exhaustion',
                    'probability': 0.7,
                    'severity': 'high',
                    'symptoms': ['High RAM utilization'],
                    'recommendation': 'Optimize memory usage, reduce active sessions'
                })
        
        return {
            'predictions': predictions,
            'confidence': 0.7 if predictions else 0.0
        }
    
    def generate_predictions(self) -> Dict[str, Any]:
        """Generate comprehensive predictions"""
        tes_prediction = self.predict_tes_trend(horizon_minutes=60)
        resource_prediction = self.predict_resource_constraints(horizon_minutes=120)
        failure_prediction = self.predict_failures()
        
        # Overall system health prediction
        health_score = 100
        if resource_prediction['constraints']:
            health_score -= len(resource_prediction['constraints']) * 10
        
        if failure_prediction['predictions']:
            health_score -= len(failure_prediction['predictions']) * 15
        
        health_status = 'excellent' if health_score >= 80 else 'good' if health_score >= 60 else 'fair' if health_score >= 40 else 'poor'
        
        predictions = {
            'timestamp': datetime.now().isoformat(),
            'tes_trend': tes_prediction,
            'resource_constraints': resource_prediction,
            'potential_failures': failure_prediction,
            'system_health': {
                'score': health_score,
                'status': health_status,
                'confidence': 0.75
            }
        }
        
        # Store prediction
        self.prediction_history.append(predictions)
        if len(self.prediction_history) > 100:
            self.prediction_history.pop(0)
        
        return predictions
    
    def save_predictions(self, predictions: Dict[str, Any]):
        """Save predictions to file"""
        predictions_dir = self.root / "outgoing" / "predictions"
        predictions_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = predictions_dir / f"prediction_{timestamp}.json"
        
        file_path.write_text(json.dumps(predictions, indent=2))
        print(f"[OK] Predictions saved to {file_path}")
    
    def generate_report(self) -> str:
        """Generate human-readable prediction report"""
        predictions = self.generate_predictions()
        
        report = []
        report.append("="*80)
        report.append("PREDICTIVE INTELLIGENCE REPORT")
        report.append("="*80)
        report.append(f"Generated: {predictions['timestamp']}")
        report.append("")
        
        # TES Trend
        report.append("TES Trend Prediction:")
        tes = predictions['tes_trend']
        report.append(f"  Current: {tes.get('current_tes', 'N/A')}")
        report.append(f"  Predicted: {tes.get('predicted_tes', 'N/A')}")
        report.append(f"  Trend: {tes.get('trend', 'N/A')}")
        report.append(f"  Confidence: {tes.get('confidence', 0):.0%}")
        report.append("")
        
        # Resource Constraints
        report.append("Resource Constraint Predictions:")
        constraints = predictions['resource_constraints']['constraints']
        if constraints:
            for c in constraints:
                report.append(f"  {c['resource']}: {c['current']:.1f}% -> {c['predicted']:.1f}% (risk: {c['risk']})")
        else:
            report.append("  No constraints predicted")
        report.append(f"  Confidence: {predictions['resource_constraints']['confidence']:.0%}")
        report.append("")
        
        # Potential Failures
        report.append("Potential Failure Predictions:")
        failures = predictions['potential_failures']['predictions']
        if failures:
            for f in failures:
                report.append(f"  {f['type']}: {f['probability']:.0%} probability ({f['severity']} severity)")
                report.append(f"    Recommendation: {f['recommendation']}")
        else:
            report.append("  No failures predicted")
        report.append("")
        
        # System Health
        health = predictions['system_health']
        report.append(f"Overall System Health: {health['status'].upper()} ({health['score']}/100)")
        report.append("")
        
        report.append("="*80)
        
        return "\n".join(report)

def main():
    print("="*80)
    print("PHASE III TRACK A: Predictive Intelligence Engine")
    print("="*80)
    print()
    
    engine = PredictiveIntelligenceEngine()
    
    print("Generating predictions...")
    predictions = engine.generate_predictions()
    
    print()
    print(engine.generate_report())
    
    # Save predictions
    engine.save_predictions(predictions)
    
    print()
    print("="*80)
    print("[SUCCESS] Predictive Intelligence Engine operational")
    print("="*80)

if __name__ == "__main__":
    main()

