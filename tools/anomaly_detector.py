#!/usr/bin/env python3
"""
Anomaly Detection System - Early warning capability
Detects unusual patterns before they become problems
"""
from __future__ import annotations
import json
import statistics
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


class AnomalyDetector:
    """Detect anomalies in system behavior"""
    
    def __init__(self, window_size: int = 50):
        """Initialize with 50 sample window for better baseline (updated 2025-10-26 per CBO team meeting)"""
        self.window_size = window_size
        self.tes_history = deque(maxlen=window_size)
        self.memory_history = deque(maxlen=window_size)
        self.baseline_file = ROOT / "logs" / "anomaly_baselines.json"
        
    def load_baselines(self) -> Dict:
        """Load baseline statistics"""
        if self.baseline_file.exists():
            with self.baseline_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def update_baselines(self, metrics: Dict):
        """Update baseline statistics"""
        self.tes_history.append(metrics.get("tes", 0))
        self.memory_history.append(metrics.get("memory", 0))
        
        if len(self.tes_history) >= 10:
            baselines = {
                "tes": {
                    "mean": statistics.mean(self.tes_history),
                    "std": statistics.stdev(self.tes_history) if len(self.tes_history) > 1 else 0,
                    "min": min(self.tes_history),
                    "max": max(self.tes_history)
                },
                "memory": {
                    "mean": statistics.mean(self.memory_history),
                    "std": statistics.stdev(self.memory_history) if len(self.memory_history) > 1 else 0,
                    "min": min(self.memory_history),
                    "max": max(self.memory_history)
                }
            }
            
            with self.baseline_file.open("w", encoding="utf-8") as f:
                json.dump(baselines, f, indent=2)
            
            return baselines
        
        return {}
    
    def detect_anomalies(self, current_metrics: Dict) -> List[Dict]:
        """Detect anomalies in current metrics"""
        baselines = self.load_baselines()
        anomalies = []
        
        # Check TES anomaly
        current_tes = current_metrics.get("tes", 0)
        if "tes" in baselines:
            tes_baseline = baselines["tes"]
            tes_mean = tes_baseline["mean"]
            tes_std = tes_baseline["std"]
            
            if tes_std > 0:
                z_score = abs((current_tes - tes_mean) / tes_std)
                if z_score > 2.0:  # 2 standard deviations
                    anomalies.append({
                        "type": "tes_anomaly",
                        "severity": "high" if z_score > 3 else "medium",
                        "current": current_tes,
                        "expected": tes_mean,
                        "deviation": z_score,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        
        # Check memory anomaly
        current_memory = current_metrics.get("memory", 0)
        if "memory" in baselines:
            mem_baseline = baselines["memory"]
            mem_mean = mem_baseline["mean"]
            mem_std = mem_baseline["std"]
            
            if mem_std > 0:
                z_score = abs((current_memory - mem_mean) / mem_std)
                if z_score > 2.0:
                    anomalies.append({
                        "type": "memory_anomaly",
                        "severity": "high" if z_score > 3 else "medium",
                        "current": current_memory,
                        "expected": mem_mean,
                        "deviation": z_score,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        
        return anomalies
    
    def early_warning_check(self, metrics: Dict) -> Optional[Dict]:
        """Generate early warning before thresholds breached"""
        current_tes = metrics.get("tes", 0)
        current_memory = metrics.get("memory", 0)
        
        warnings = []
        
        # TES decline warning
        if current_tes < 60 and current_tes > 0:
            warnings.append({
                "type": "tes_decline",
                "message": f"TES declining: {current_tes:.1f}",
                "action": "investigate_agent_performance"
            })
        
        # Memory pressure warning
        if current_memory > 70:
            warnings.append({
                "type": "memory_pressure",
                "message": f"Memory high: {current_memory:.1f}%",
                "action": "reduce_active_tasks"
            })
        
        if warnings:
            return {
                "severity": "warning",
                "warnings": warnings,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return None


def main():
    """Run anomaly detection"""
    detector = AnomalyDetector()
    
    # Get current metrics
    current = {
        "tes": 55.0,
        "memory": 71.4
    }
    
    # Update baselines
    baselines = detector.update_baselines(current)
    
    # Detect anomalies
    anomalies = detector.detect_anomalies(current)
    
    # Check for early warnings
    warnings = detector.early_warning_check(current)
    
    print("=" * 70)
    print("ANOMALY DETECTION REPORT")
    print("=" * 70)
    
    if baselines:
        print("\nBaselines:")
        print(f"  TES: {baselines['tes']['mean']:.1f} ± {baselines['tes']['std']:.1f}")
        print(f"  Memory: {baselines['memory']['mean']:.1f} ± {baselines['memory']['std']:.1f}")
    
    if anomalies:
        print("\nAnomalies Detected:")
        for anomaly in anomalies:
            print(f"  {anomaly['type']}: {anomaly['severity']} (deviation: {anomaly['deviation']:.2f})")
    else:
        print("\nNo anomalies detected")
    
    if warnings:
        print("\nEarly Warnings:")
        for warning in warnings['warnings']:
            print(f"  {warning['type']}: {warning['message']}")
            print(f"    Action: {warning['action']}")
    
    print("\n[INFO] Anomaly detection operational")


if __name__ == "__main__":
    main()

