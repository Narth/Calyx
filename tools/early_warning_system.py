#!/usr/bin/env python3
"""
Early Warning System - Proactive issue detection and alerting
Monitors system state and predicts issues before they occur
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from predictive_analytics import PredictiveEngine

ROOT = Path(__file__).resolve().parent.parent


class EarlyWarningSystem:
    """Proactive system monitoring and alerting"""
    
    def __init__(self):
        self.alerts_file = ROOT / "logs" / "early_warnings.jsonl"
        self.predictive_engine = PredictiveEngine()
        self.warning_thresholds = {
            "tes_decline": 5.0,  # TES drop by 5 points (calibrated 2025-10-26: baseline ~97, alert below 92)
            "memory_high": 75.0,  # Memory > 75%
            "risk_high": 0.3,  # Risk > 30%
            "anomaly_severity": "medium",  # Minimum severity
            "exhaustion_likely": True,
            "tes_baseline": 97.0  # Current baseline (updated 2025-10-26 per team meeting)
        }
    
    def check_system_health(self) -> List[Dict]:
        """Check system for early warning conditions"""
        warnings = []
        
        # Load history
        self.predictive_engine.load_history()
        
        # Check TES decline
        tes_warning = self._check_tes_decline()
        if tes_warning:
            warnings.append(tes_warning)
        
        # Check memory usage
        memory_warning = self._check_memory_usage()
        if memory_warning:
            warnings.append(memory_warning)
        
        # Check failure risk
        risk_warning = self._check_failure_risk()
        if risk_warning:
            warnings.append(risk_warning)
        
        # Check for anomalies
        anomaly_warnings = self._check_anomalies()
        warnings.extend(anomaly_warnings)
        
        # Check resource exhaustion
        exhaustion_warning = self._check_resource_exhaustion()
        if exhaustion_warning:
            warnings.append(exhaustion_warning)
        
        return warnings
    
    def _check_tes_decline(self) -> Optional[Dict]:
        """Check if TES is declining rapidly"""
        if len(self.predictive_engine.tes_history) < 10:
            return None
        
        recent = list(self.predictive_engine.tes_history)[-10:]
        decline = recent[0] - recent[-1]
        
        if decline >= self.warning_thresholds["tes_decline"]:
            return {
                "type": "tes_decline",
                "severity": "high" if decline >= 10 else "medium",
                "message": f"TES declining: {recent[-1]:.1f} -> {recent[0]:.1f} ({decline:.1f} point drop)",
                "current_tes": recent[-1],
                "decline": decline,
                "recommendation": "Review recent agent failures and resource constraints"
            }
        
        return None
    
    def _check_memory_usage(self) -> Optional[Dict]:
        """Check if memory usage is high"""
        enhanced_metrics_file = ROOT / "logs" / "enhanced_metrics.jsonl"
        
        if not enhanced_metrics_file.exists():
            return None
        
        try:
            # Get most recent memory reading
            with enhanced_metrics_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
                
            if not lines:
                return None
            
            latest = json.loads(lines[-1])
            memory_percent = latest.get("memory", {}).get("percent", 0)
            
            if memory_percent >= self.warning_thresholds["memory_high"]:
                return {
                    "type": "memory_high",
                    "severity": "high" if memory_percent >= 80 else "medium",
                    "message": f"Memory usage high: {memory_percent:.1f}%",
                    "memory_percent": memory_percent,
                    "recommendation": "Consider throttling agent dispatch or cleanup stale processes"
                }
        except:
            pass
        
        return None
    
    def _check_failure_risk(self) -> Optional[Dict]:
        """Check if failure risk is elevated"""
        risk_assessment = self.predictive_engine.assess_failure_risk()
        
        if risk_assessment["risk"] >= self.warning_thresholds["risk_high"]:
            return {
                "type": "failure_risk",
                "severity": "high" if risk_assessment["risk"] >= 0.5 else "medium",
                "message": f"Failure risk elevated: {risk_assessment['risk']*100:.1f}%",
                "risk": risk_assessment["risk"],
                "current_tes": risk_assessment["current_tes"],
                "recommendation": "Increase monitoring frequency and prepare for recovery"
            }
        
        return None
    
    def _check_anomalies(self) -> List[Dict]:
        """Check for system anomalies"""
        anomalies = self.predictive_engine.detect_anomalies()
        warnings = []
        
        for anomaly in anomalies:
            if anomaly["severity"] == "high" or (
                anomaly["severity"] == "medium" and self.warning_thresholds["anomaly_severity"] == "medium"
            ):
                warnings.append({
                    "type": "anomaly",
                    "severity": anomaly["severity"],
                    "message": f"Anomaly detected: TES={anomaly['value']:.1f}, Z-score={anomaly['z_score']:.2f}",
                    "anomaly": anomaly,
                    "recommendation": "Investigate unusual TES value"
                })
        
        return warnings
    
    def _check_resource_exhaustion(self) -> Optional[Dict]:
        """Check if resource exhaustion is likely"""
        prediction = self.predictive_engine.predict_resource_exhaustion()
        
        if prediction.get("exhaustion_likely") and self.warning_thresholds["exhaustion_likely"]:
            return {
                "type": "resource_exhaustion",
                "severity": "high",
                "message": f"Resource exhaustion predicted within {prediction.get('minutes_to_limit', 0):.0f} minutes",
                "prediction": prediction,
                "recommendation": "Take immediate action to reduce memory usage"
            }
        
        return None
    
    def log_warnings(self, warnings: List[Dict]):
        """Log warnings to file"""
        if not warnings:
            return
        
        for warning in warnings:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **warning
            }
            
            with self.alerts_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
    
    def generate_alert_summary(self, warnings: List[Dict]) -> str:
        """Generate human-readable alert summary"""
        if not warnings:
            return "[OK] No warnings - System healthy"
        
        summary = ["=" * 70]
        summary.append("EARLY WARNING SYSTEM ALERTS")
        summary.append("=" * 70)
        summary.append("")
        
        # Group by severity
        high_severity = [w for w in warnings if w["severity"] == "high"]
        medium_severity = [w for w in warnings if w["severity"] == "medium"]
        
        if high_severity:
            summary.append("[HIGH SEVERITY] ALERTS:")
            summary.append("-" * 70)
            for warning in high_severity:
                summary.append(f"  [{warning['type']}] {warning['message']}")
                summary.append(f"    Recommendation: {warning['recommendation']}")
                summary.append("")
        
        if medium_severity:
            summary.append("[MEDIUM SEVERITY] ALERTS:")
            summary.append("-" * 70)
            for warning in medium_severity:
                summary.append(f"  [{warning['type']}] {warning['message']}")
                summary.append(f"    Recommendation: {warning['recommendation']}")
                summary.append("")
        
        return "\n".join(summary)


def main():
    """Run early warning system"""
    print("[INFO] Early Warning System starting...")
    
    ews = EarlyWarningSystem()
    warnings = ews.check_system_health()
    
    # Log warnings
    ews.log_warnings(warnings)
    
    # Print summary
    summary = ews.generate_alert_summary(warnings)
    print(summary)
    
    if warnings:
        print(f"\n[INFO] {len(warnings)} warning(s) logged to {ews.alerts_file}")
    else:
        print("\n[INFO] No warnings - System healthy")


if __name__ == "__main__":
    main()

