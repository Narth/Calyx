#!/usr/bin/env python3
"""
Predictive Analytics Engine - Core forecasting capability
Takes historical data and generates predictions for future system states
"""
from __future__ import annotations
import json
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Try to import statsmodels for ARIMA (optional)
try:
    from statsmodels.tsa.arima.model import ARIMA
    HAS_ARIMA = True
except ImportError:
    HAS_ARIMA = False
    print("[WARN] statsmodels not available. Using simple forecasting.")

ROOT = Path(__file__).resolve().parent.parent


class PredictiveEngine:
    """Forecast future system states"""
    
    def __init__(self, history_window: int = 100):
        self.history_window = history_window
        self.tes_history = deque(maxlen=history_window)
        self.memory_history = deque(maxlen=history_window)
        self.timestamp_history = deque(maxlen=history_window)
        
    def load_history(self):
        """Load historical data"""
        metrics_file = ROOT / "logs" / "agent_metrics.csv"
        
        try:
            import csv
            if metrics_file.exists():
                with metrics_file.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    for row in rows[-self.history_window:]:
                        tes = float(row.get("tes", 0) or 0)
                        self.tes_history.append(tes)
                        self.timestamp_history.append(row.get("timestamp", ""))
        except Exception as e:
            print(f"[WARN] Could not load history: {e}")
    
    def forecast_tes(self, horizon_minutes: int = 60) -> Dict:
        """Forecast TES N minutes ahead using ARIMA if available, else linear"""
        if len(self.tes_history) < 3:
            return {"forecast": 55.0, "confidence": 0.0, "trend": "insufficient_data"}
        
        y = np.array(self.tes_history)
        
        # Try ARIMA if available and enough data
        if HAS_ARIMA and len(self.tes_history) >= 10:
            try:
                return self._forecast_arima(y, horizon_minutes)
            except Exception as e:
                print(f"[WARN] ARIMA failed: {e}, falling back to linear")
        
        # Fallback to linear regression
        return self._forecast_linear(y, horizon_minutes)
    
    def _forecast_arima(self, y: np.ndarray, horizon_minutes: int) -> Dict:
        """Forecast using ARIMA model"""
        # Fit ARIMA(1,1,1) model
        model = ARIMA(y, order=(1, 1, 1))
        fitted_model = model.fit()
        
        # Forecast ahead
        steps = max(1, int(horizon_minutes / 60))
        forecast_result = fitted_model.forecast(steps=steps)
        forecast = float(forecast_result[-1])
        
        # Get confidence intervals
        conf_int = fitted_model.get_forecast(steps=steps).conf_int()
        confidence = float((conf_int.iloc[-1, 1] - conf_int.iloc[-1, 0]) / 100)
        
        # Determine trend
        trend_slope = forecast - y[-1]
        if trend_slope > 0.1:
            trend = "improving"
        elif trend_slope < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "forecast": max(0, min(100, forecast)),
            "confidence": confidence,
            "trend": trend,
            "horizon_minutes": horizon_minutes,
            "baseline": float(np.mean(y)),
            "method": "ARIMA"
        }
    
    def _forecast_linear(self, y: np.ndarray, horizon_minutes: int) -> Dict:
        """Forecast using linear regression"""
        x = np.arange(len(y))
        
        # Fit linear trend
        coeffs = np.polyfit(x, y, 1)
        trend_slope = coeffs[0]
        
        # Forecast
        future_x = len(y) + (horizon_minutes / 60.0)
        forecast = np.polyval(coeffs, future_x)
        
        # Clamp to reasonable range
        forecast = max(0, min(100, forecast))
        
        # Calculate confidence based on data stability
        variance = np.var(y)
        confidence = max(0, min(1, 1 - (variance / 1000)))
        
        # Determine trend
        if trend_slope > 0.1:
            trend = "improving"
        elif trend_slope < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "forecast": float(forecast),
            "confidence": float(confidence),
            "trend": trend,
            "horizon_minutes": horizon_minutes,
            "baseline": float(np.mean(y)),
            "method": "linear"
        }
    
    def predict_resource_demand(self, window_minutes: int = 60) -> Dict:
        """Predict resource needs N minutes ahead"""
        if len(self.memory_history) < 3:
            return {"memory": 70.0, "confidence": 0.0}
        
        # Simple moving average forecast
        recent = list(self.memory_history)[-10:]
        avg_memory = sum(recent) / len(recent)
        
        # Add trend component
        if len(self.memory_history) >= 5:
            trend = (self.memory_history[-1] - self.memory_history[-5]) / 5
            forecast = avg_memory + (trend * (window_minutes / 10))
        else:
            forecast = avg_memory
        
        forecast = max(0, min(100, forecast))
        
        return {
            "memory": float(forecast),
            "confidence": 0.7,
            "window_minutes": window_minutes
        }
    
    def assess_failure_risk(self) -> Dict:
        """Calculate current failure probability"""
        if len(self.tes_history) < 5:
            return {"risk": 0.5, "confidence": 0.0}
        
        recent_tes = list(self.tes_history)[-5:]
        avg_tes = sum(recent_tes) / len(recent_tes)
        
        # Risk increases as TES decreases
        risk = max(0, min(1, (100 - avg_tes) / 100))
        
        # Calculate confidence
        variance = np.var(recent_tes)
        confidence = max(0, min(1, 1 - (variance / 500)))
        
        return {
            "risk": float(risk),
            "confidence": float(confidence),
            "current_tes": float(avg_tes)
        }
    
    def detect_anomalies(self, threshold_std: float = 2.0) -> List[Dict]:
        """Detect anomalies in TES history"""
        if len(self.tes_history) < 10:
            return []
        
        y = np.array(self.tes_history)
        mean = np.mean(y)
        std = np.std(y)
        
        anomalies = []
        
        for i, value in enumerate(y):
            z_score = abs((value - mean) / std) if std > 0 else 0
            
            if z_score > threshold_std:
                anomalies.append({
                    "index": i,
                    "value": float(value),
                    "z_score": float(z_score),
                    "severity": "high" if z_score > 3 else "medium",
                    "timestamp": self.timestamp_history[i] if i < len(self.timestamp_history) else None
                })
        
        return anomalies
    
    def predict_resource_exhaustion(self, lookahead_minutes: int = 240) -> Dict:
        """Predict when resources might be exhausted"""
        enhanced_metrics_file = ROOT / "logs" / "enhanced_metrics.jsonl"
        
        if not enhanced_metrics_file.exists():
            return {"prediction": "insufficient_data"}
        
        try:
            # Read recent memory metrics
            memory_history = []
            current_time = datetime.now(timezone.utc).timestamp()
            
            with enhanced_metrics_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        
                        # Only consider recent history
                        if current_time - entry_time < 3600:  # Last hour
                            mem_percent = entry.get("memory", {}).get("percent", 0)
                            memory_history.append(mem_percent)
                    except:
                        continue
            
            if len(memory_history) < 3:
                return {"prediction": "insufficient_data"}
            
            # Calculate trend
            recent_avg = sum(memory_history[-5:]) / len(memory_history[-5:])
            older_avg = sum(memory_history[:5]) / len(memory_history[:5]) if len(memory_history) >= 5 else recent_avg
            
            trend_rate = (recent_avg - older_avg) / len(memory_history)
            
            # Predict exhaustion
            current_mem = memory_history[-1]
            if trend_rate > 0:
                minutes_to_limit = (75 - current_mem) / (trend_rate * 6)  # Per 5-min interval
            else:
                minutes_to_limit = None
            
            return {
                "current_memory": float(current_mem),
                "trend_rate": float(trend_rate),
                "minutes_to_limit": float(minutes_to_limit) if minutes_to_limit else None,
                "exhaustion_likely": float(minutes_to_limit) < lookahead_minutes if minutes_to_limit else False,
                "confidence": min(1.0, len(memory_history) / 20.0)
            }
            
        except Exception as e:
            return {"prediction": "error", "error": str(e)}


def main():
    """Run predictive analytics"""
    engine = PredictiveEngine()
    engine.load_history()
    
    # Generate forecasts
    tes_forecast = engine.forecast_tes(horizon_minutes=60)
    resource_forecast = engine.predict_resource_demand(window_minutes=60)
    risk_assessment = engine.assess_failure_risk()
    
    # Detect anomalies
    anomalies = engine.detect_anomalies()
    
    # Predict resource exhaustion
    exhaustion_prediction = engine.predict_resource_exhaustion()
    
    # Output results
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tes_forecast": tes_forecast,
        "resource_forecast": resource_forecast,
        "risk_assessment": risk_assessment,
        "anomalies": anomalies,
        "exhaustion_prediction": exhaustion_prediction
    }
    
    print("=" * 70)
    print("PREDICTIVE ANALYTICS FORECAST")
    print("=" * 70)
    print(f"\nTES Forecast (1 hour):")
    print(f"  Forecast: {tes_forecast['forecast']:.1f}")
    print(f"  Trend: {tes_forecast['trend']}")
    print(f"  Confidence: {tes_forecast['confidence']*100:.1f}%")
    print(f"  Method: {tes_forecast.get('method', 'unknown')}")
    
    print(f"\nResource Forecast (1 hour):")
    print(f"  Memory: {resource_forecast['memory']:.1f}%")
    print(f"  Confidence: {resource_forecast['confidence']*100:.1f}%")
    
    print(f"\nFailure Risk Assessment:")
    print(f"  Risk Level: {risk_assessment['risk']*100:.1f}%")
    print(f"  Current TES: {risk_assessment['current_tes']:.1f}")
    print(f"  Confidence: {risk_assessment['confidence']*100:.1f}%")
    
    if anomalies:
        print(f"\n[ALERT] Anomalies Detected: {len(anomalies)}")
        for anomaly in anomalies[:5]:  # Show first 5
            print(f"  - Value: {anomaly['value']:.1f}, Z-score: {anomaly['z_score']:.2f}, Severity: {anomaly['severity']}")
    else:
        print(f"\n[OK] No anomalies detected")
    
    if exhaustion_prediction.get("prediction") == "insufficient_data":
        print(f"\n[WARN] Resource exhaustion prediction: {exhaustion_prediction['prediction']}")
    elif exhaustion_prediction.get("prediction") == "error":
        print(f"\n[WARN] Resource exhaustion prediction error: {exhaustion_prediction.get('error', 'unknown')}")
    else:
        print(f"\nResource Exhaustion Prediction:")
        print(f"  Current Memory: {exhaustion_prediction.get('current_memory', 0):.1f}%")
        if exhaustion_prediction.get('minutes_to_limit'):
            print(f"  Estimated Time to Limit: {exhaustion_prediction['minutes_to_limit']:.1f} minutes")
            if exhaustion_prediction.get('exhaustion_likely'):
                print(f"  [WARNING] Resource exhaustion likely!")
            else:
                print(f"  [OK] Resource exhaustion unlikely")
        print(f"  Confidence: {exhaustion_prediction.get('confidence', 0)*100:.1f}%")
    
    # Save results
    results_file = ROOT / "logs" / "predictive_forecasts.jsonl"
    with results_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(results) + "\n")
    
    print("\n[INFO] Forecasts saved to logs/predictive_forecasts.jsonl")


if __name__ == "__main__":
    main()

