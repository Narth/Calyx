#!/usr/bin/env python3
"""
Foresight Deployment Scheduler - Coordinate all foresight components
Runs predictive analytics, anomaly detection, and synthetic training in automated cycles
"""
from __future__ import annotations
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_prediction():
    """Run predictive analytics"""
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "predictive_analytics.py")], 
                      cwd=str(ROOT), timeout=30)
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")


def run_anomaly_detection():
    """Run anomaly detection"""
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "anomaly_detector.py")], 
                      cwd=str(ROOT), timeout=30)
    except Exception as e:
        print(f"[ERROR] Anomaly detection failed: {e}")


def run_synthetic_training():
    """Run synthetic training"""
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "accelerated_training.py")], 
                      cwd=str(ROOT), timeout=60)
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")


def main():
    """Coordinate foresight components"""
    print("[INFO] Foresight Deployment Scheduler started")
    print("[INFO] Running all foresight components in parallel")
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running foresight cycle...")
            
            # Run all components
            run_prediction()
            run_anomaly_detection()
            
            # Run training less frequently
            if datetime.now().minute % 30 == 0:
                run_synthetic_training()
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle complete")
            
            # Sleep for 5 minutes
            time.sleep(300)
            
        except KeyboardInterrupt:
            print("\n[INFO] Scheduler stopped")
            break
        except Exception as e:
            print(f"[ERROR] Scheduler error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()

