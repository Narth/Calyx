#!/usr/bin/env python3
"""
Enhanced Metrics Collector - Collect comprehensive system metrics every 5 minutes
Feeds data to predictive analytics engine for forecasting and anomaly detection
"""
from __future__ import annotations
import json
import psutil
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


class EnhancedMetricsCollector:
    """Collect detailed system metrics for foresight capability"""
    
    def __init__(self):
        self.metrics_file = ROOT / "logs" / "enhanced_metrics.jsonl"
        self.collection_interval = 300  # 5 minutes
        self.metrics_window = deque(maxlen=1000)  # Keep last 1000 readings
        
    def collect_full_metrics(self) -> Dict:
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Process metrics
            processes = list(psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']))
            python_processes = [p for p in processes if 'python' in p.info['name'].lower()]
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Agent scheduler state
            scheduler_state = self._get_scheduler_state()
            
            # TES metrics
            tes_data = self._get_current_tes()
            
            metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None,
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "percent": memory.percent,
                    "swap_total_gb": swap.total / (1024**3),
                    "swap_used_gb": swap.used / (1024**3),
                    "swap_percent": swap.percent,
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "percent": disk.percent,
                },
                "processes": {
                    "total": len(processes),
                    "python": len(python_processes),
                    "python_memory_percent": sum(p.info['memory_percent'] or 0 for p in python_processes),
                    "python_cpu_percent": sum(p.info['cpu_percent'] or 0 for p in python_processes),
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "agent_scheduler": scheduler_state,
                "tes": tes_data,
            }
            
            return metrics
            
        except Exception as e:
            print(f"[ERROR] Failed to collect metrics: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    def _get_scheduler_state(self) -> Dict:
        """Get current agent scheduler state"""
        state_file = ROOT / "logs" / "agent_scheduler_state.json"
        
        if not state_file.exists():
            return {"status": "unknown"}
        
        try:
            with state_file.open("r", encoding="utf-8") as f:
                state = json.load(f)
            return state
        except:
            return {"status": "unknown"}
    
    def _get_current_tes(self) -> Dict:
        """Get current TES metrics"""
        metrics_file = ROOT / "logs" / "agent_metrics.csv"
        
        if not metrics_file.exists():
            return {"current": None, "trend": "unknown"}
        
        try:
            import csv
            with metrics_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            if not rows:
                return {"current": None, "trend": "unknown"}
            
            # Get last 10 TES values
            recent_tes = [float(row.get("tes", 0) or 0) for row in rows[-10:]]
            
            if len(recent_tes) < 2:
                return {"current": recent_tes[0] if recent_tes else None, "trend": "insufficient_data"}
            
            # Calculate trend
            trend_slope = recent_tes[-1] - recent_tes[0]
            
            if trend_slope > 1:
                trend = "improving"
            elif trend_slope < -1:
                trend = "declining"
            else:
                trend = "stable"
            
            return {
                "current": recent_tes[-1],
                "mean": sum(recent_tes) / len(recent_tes),
                "min": min(recent_tes),
                "max": max(recent_tes),
                "trend": trend,
                "variance": sum((x - sum(recent_tes)/len(recent_tes))**2 for x in recent_tes) / len(recent_tes)
            }
            
        except Exception as e:
            return {"current": None, "trend": "error", "error": str(e)}
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to JSONL file"""
        try:
            with self.metrics_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")
            
            # Keep in memory window
            self.metrics_window.append(metrics)
            
        except Exception as e:
            print(f"[ERROR] Failed to save metrics: {e}")
    
    def get_recent_metrics(self, minutes: int = 60) -> List[Dict]:
        """Get metrics from last N minutes"""
        # Read from file for persistent history
        metrics = []
        
        if not self.metrics_file.exists():
            return metrics
        
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (minutes * 60)
            
            with self.metrics_file.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                        
                        if entry_time >= cutoff_time:
                            metrics.append(entry)
                    except:
                        continue
            
            return metrics
            
        except Exception as e:
            print(f"[ERROR] Failed to read metrics: {e}")
            return metrics
    
    def run_continuous(self):
        """Run continuous metrics collection"""
        print(f"[INFO] Enhanced Metrics Collector started")
        print(f"[INFO] Collection interval: {self.collection_interval} seconds (5 minutes)")
        print(f"[INFO] Metrics file: {self.metrics_file}")
        
        # Initial collection
        print("\n[COLLECT] Collecting initial metrics...")
        metrics = self.collect_full_metrics()
        self.save_metrics(metrics)
        print(f"[COLLECT] Initial collection complete")
        
        while True:
            try:
                print(f"\n[COLLECT] Waiting {self.collection_interval} seconds until next collection...")
                time.sleep(self.collection_interval)
                
                print(f"[COLLECT] Collecting metrics at {datetime.now().isoformat()}...")
                metrics = self.collect_full_metrics()
                self.save_metrics(metrics)
                
                # Print summary
                print(f"[COLLECT] Collection complete:")
                print(f"  CPU: {metrics.get('cpu', {}).get('percent', 0):.1f}%")
                print(f"  Memory: {metrics.get('memory', {}).get('percent', 0):.1f}%")
                print(f"  TES: {metrics.get('tes', {}).get('current', 0):.1f}")
                print(f"  Python Processes: {metrics.get('processes', {}).get('python', 0)}")
                
            except KeyboardInterrupt:
                print("\n[INFO] Collector stopped by user")
                break
            except Exception as e:
                print(f"[ERROR] Collection failed: {e}")
                time.sleep(60)  # Wait 1 minute before retry


def main():
    """Run metrics collector"""
    collector = EnhancedMetricsCollector()
    collector.run_continuous()


if __name__ == "__main__":
    main()

