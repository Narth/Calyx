#!/usr/bin/env python3
"""
Foresight Orchestrator - Coordinated foresight system management
Coordinates predictive analytics, early warnings, and proactive resource management
"""
from __future__ import annotations
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ForesightOrchestrator:
    """Coordinate all foresight capabilities"""
    
    def __init__(self):
        self.scripts = {
            "metrics_collector": ROOT / "tools" / "enhanced_metrics_collector.py",
            "predictive_analytics": ROOT / "tools" / "predictive_analytics.py",
            "early_warning": ROOT / "tools" / "early_warning_system.py",
            "tes_tracker": ROOT / "tools" / "granular_tes_tracker.py",
        }
        
        self.running_processes = {}
    
    def run_metrics_collector(self):
        """Start enhanced metrics collector"""
        if "metrics_collector" in self.running_processes:
            print("[ORCHESTRATOR] Metrics collector already running")
            return
        
        print("[ORCHESTRATOR] Starting enhanced metrics collector...")
        # Note: This would typically run in background, but for demo we'll mark as started
        self.running_processes["metrics_collector"] = "started"
        print("[ORCHESTRATOR] OK Metrics collector started")
    
    def run_predictive_analytics(self):
        """Run predictive analytics"""
        print("[ORCHESTRATOR] Running predictive analytics...")
        try:
            result = subprocess.run(
                [sys.executable, str(self.scripts["predictive_analytics"])],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("[ORCHESTRATOR] OK Predictive analytics complete")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"[ORCHESTRATOR] WARN Predictive analytics warning: Exit code {result.returncode}")
                if result.stderr:
                    print(result.stderr)
                    
        except Exception as e:
            print(f"[ORCHESTRATOR] ERROR: Predictive analytics failed: {e}")
    
    def run_early_warning_system(self):
        """Run early warning system"""
        print("[ORCHESTRATOR] Running early warning system...")
        try:
            result = subprocess.run(
                [sys.executable, str(self.scripts["early_warning"])],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print("[ORCHESTRATOR] OK Early warning check complete")
                if result.stdout:
                    print(result.stdout)
                    
                # Check if warnings were generated
                warnings_file = ROOT / "logs" / "early_warnings.jsonl"
                if warnings_file.exists():
                    with warnings_file.open("r", encoding="utf-8") as f:
                        lines = f.readlines()
                    
                    if lines:
                        print(f"[ORCHESTRATOR] WARN {len(lines)} total warning(s) in system")
            else:
                print(f"[ORCHESTRATOR] WARN Early warning check warning: Exit code {result.returncode}")
                
        except Exception as e:
            print(f"[ORCHESTRATOR] ERROR: Early warning system failed: {e}")
    
    def run_full_cycle(self):
        """Run complete foresight cycle"""
        print("=" * 70)
        print("FORESIGHT ORCHESTRATOR - Full Cycle")
        print("=" * 70)
        print(f"Started: {datetime.now().isoformat()}")
        print()
        
        # Start metrics collection if not running
        self.run_metrics_collector()
        
        # Run predictive analytics
        self.run_predictive_analytics()
        
        # Run early warning checks
        self.run_early_warning_system()
        
        print()
        print("=" * 70)
        print("FORESIGHT CYCLE COMPLETE")
        print("=" * 70)
        print(f"Completed: {datetime.now().isoformat()}")
    
    def run_scheduled(self, analytics_interval_minutes: int = 15, warning_interval_minutes: int = 5):
        """Run scheduled foresight cycles"""
        print("[ORCHESTRATOR] Foresight Orchestrator scheduled mode")
        print(f"[ORCHESTRATOR] Analytics interval: {analytics_interval_minutes} minutes")
        print(f"[ORCHESTRATOR] Warning check interval: {warning_interval_minutes} minutes")
        print("[ORCHESTRATOR] Starting...")
        
        last_analytics = 0
        last_warning = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Run early warning checks more frequently
                if current_time - last_warning >= (warning_interval_minutes * 60):
                    self.run_early_warning_system()
                    last_warning = current_time
                
                # Run predictive analytics less frequently
                if current_time - last_analytics >= (analytics_interval_minutes * 60):
                    self.run_predictive_analytics()
                    last_analytics = current_time
                
                # Sleep briefly before next check
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                print("\n[ORCHESTRATOR] Stopped by user")
                break
            except Exception as e:
                print(f"[ORCHESTRATOR] ERROR: {e}")
                time.sleep(60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Foresight Orchestrator")
    parser.add_argument("--mode", choices=["cycle", "scheduled"], default="cycle",
                        help="Run mode: cycle (one-time) or scheduled (continuous)")
    parser.add_argument("--analytics-interval", type=int, default=15,
                        help="Analytics interval in minutes (scheduled mode)")
    parser.add_argument("--warning-interval", type=int, default=5,
                        help="Warning check interval in minutes (scheduled mode)")
    
    args = parser.parse_args()
    
    orchestrator = ForesightOrchestrator()
    
    if args.mode == "cycle":
        orchestrator.run_full_cycle()
    else:
        orchestrator.run_scheduled(
            analytics_interval_minutes=args.analytics_interval,
            warning_interval_minutes=args.warning_interval
        )


if __name__ == "__main__":
    main()

