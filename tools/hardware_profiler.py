#!/usr/bin/env python3
"""
Hardware Performance Profiler - Specialized metrics for hardware capability assessment
Collects GPU, CPU, thermal, and inference timing metrics for cross-hardware optimization

Primary Use Cases:
- Baseline performance on lower-spec hardware (Razer Blade Stealth / MX150)
- Comparative analysis with high-spec hardware (Desktop / RTX 2070 Super)
- BloomOS hardware requirement optimization
- Real-world latency and throughput benchmarking
"""
from __future__ import annotations
import json
import psutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

ROOT = Path(__file__).resolve().parent.parent


class HardwareProfiler:
    """Collect hardware-specific performance metrics"""
    
    def __init__(self, profile_name: Optional[str] = None):
        self.profile_name = profile_name or self._detect_profile_name()
        self.metrics_file = ROOT / "logs" / f"hardware_profile_{self.profile_name}.jsonl"
        self.config_file = ROOT / "config" / "hardware_profiles.json"
        self.collection_interval = 60  # 1 minute for granular hardware metrics
        
        # Ensure logs directory exists
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load hardware profile
        self.hardware_profile = self._initialize_hardware_profile()
        
    def _detect_profile_name(self) -> str:
        """Auto-detect profile name from hostname or system info"""
        try:
            import platform
            hostname = platform.node().lower().replace('-', '_')
            return hostname
        except:
            return "unknown"
    
    def _initialize_hardware_profile(self) -> Dict:
        """Initialize hardware profile with static system information"""
        profile = {
            "profile_name": self.profile_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "system": self._get_system_info(),
            "gpu": self._get_gpu_info(),
            "cpu": self._get_cpu_info_static(),
            "memory": self._get_memory_info_static(),
        }
        
        # Save profile configuration
        self._save_hardware_profile(profile)
        return profile
    
    def _get_system_info(self) -> Dict:
        """Get static system information"""
        try:
            import platform
            return {
                "os": platform.system(),
                "os_version": platform.version(),
                "os_release": platform.release(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_gpu_info(self) -> Dict:
        """Get GPU information using nvidia-smi"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(',')]
                return {
                    "available": True,
                    "name": parts[0] if len(parts) > 0 else "Unknown",
                    "driver_version": parts[1] if len(parts) > 1 else "Unknown",
                    "memory_total_mb": float(parts[2]) if len(parts) > 2 else 0,
                    "compute_capability": "Unknown",  # Not queryable via nvidia-smi
                    "power_limit_watts": 0,  # May not be supported on mobile GPUs
                }
            else:
                return {"available": False, "reason": "nvidia-smi failed"}
                
        except FileNotFoundError:
            return {"available": False, "reason": "nvidia-smi not found"}
        except Exception as e:
            return {"available": False, "reason": str(e)}
    
    def _get_cpu_info_static(self) -> Dict:
        """Get static CPU information"""
        try:
            cpu_freq = psutil.cpu_freq()
            return {
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
                "max_frequency_mhz": cpu_freq.max if cpu_freq else None,
                "min_frequency_mhz": cpu_freq.min if cpu_freq else None,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_memory_info_static(self) -> Dict:
        """Get static memory information"""
        try:
            memory = psutil.virtual_memory()
            return {
                "total_gb": round(memory.total / (1024**3), 2),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _save_hardware_profile(self, profile: Dict):
        """Save hardware profile to config file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing profiles
            profiles = {}
            if self.config_file.exists():
                with self.config_file.open("r", encoding="utf-8") as f:
                    profiles = json.load(f)
            
            # Update with current profile
            profiles[self.profile_name] = profile
            
            # Save back
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2)
                
            print(f"[PROFILE] Saved hardware profile: {self.profile_name}")
            
        except Exception as e:
            print(f"[ERROR] Failed to save hardware profile: {e}")
    
    def collect_runtime_metrics(self) -> Dict:
        """Collect runtime performance metrics"""
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "profile_name": self.profile_name,
            "cpu": self._get_cpu_runtime(),
            "memory": self._get_memory_runtime(),
            "gpu": self._get_gpu_runtime(),
            "thermal": self._get_thermal_info(),
            "processes": self._get_process_metrics(),
            "inference_timing": self._estimate_inference_timing(),
        }
        
        return metrics
    
    def _get_cpu_runtime(self) -> Dict:
        """Get runtime CPU metrics"""
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_percent_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
            
            return {
                "percent_total": psutil.cpu_percent(interval=0.1),
                "percent_per_core": cpu_percent_per_core,
                "frequency_current_mhz": cpu_freq.current if cpu_freq else None,
                "load_average_1min": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_memory_runtime(self) -> Dict:
        """Get runtime memory metrics"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percent": swap.percent,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_gpu_runtime(self) -> Dict:
        """Get runtime GPU metrics using nvidia-smi"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.free,temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(',')]
                
                # Parse values, handling "N/A" and "[Not Supported]" gracefully
                def parse_float(val: str, default: float = 0.0) -> float:
                    try:
                        if val.lower() in ['n/a', '[not supported]', 'not supported']:
                            return default
                        return float(val)
                    except:
                        return default
                
                return {
                    "available": True,
                    "utilization_percent": parse_float(parts[0]) if len(parts) > 0 else 0,
                    "memory_utilization_percent": parse_float(parts[1]) if len(parts) > 1 else 0,
                    "memory_used_mb": parse_float(parts[2]) if len(parts) > 2 else 0,
                    "memory_free_mb": parse_float(parts[3]) if len(parts) > 3 else 0,
                    "temperature_celsius": parse_float(parts[4]) if len(parts) > 4 else 0,
                    "power_draw_watts": parse_float(parts[5]) if len(parts) > 5 else 0,
                }
            else:
                return {"available": False, "reason": "nvidia-smi query failed"}
                
        except Exception as e:
            return {"available": False, "reason": str(e)}
    
    def _get_thermal_info(self) -> Dict:
        """Get thermal/temperature information"""
        try:
            temps = psutil.sensors_temperatures()
            
            if not temps:
                return {"available": False, "reason": "No temperature sensors found"}
            
            # Aggregate temperatures
            all_temps = []
            for name, entries in temps.items():
                for entry in entries:
                    all_temps.append({
                        "sensor": name,
                        "label": entry.label,
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                    })
            
            return {
                "available": True,
                "sensors": all_temps,
                "max_temp": max(t["current"] for t in all_temps) if all_temps else None,
            }
            
        except AttributeError:
            # psutil.sensors_temperatures not available on Windows
            return {"available": False, "reason": "sensors_temperatures not supported on this OS"}
        except Exception as e:
            return {"available": False, "reason": str(e)}
    
    def _get_process_metrics(self) -> Dict:
        """Get process-specific metrics"""
        try:
            processes = list(psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'num_threads']))
            
            # Filter for relevant processes
            python_procs = [p for p in processes if 'python' in p.info['name'].lower()]
            whisper_procs = [p for p in processes if any(kw in str(p.info.get('cmdline', '')).lower() 
                                                          for kw in ['whisper', 'listener', 'asr'])]
            
            return {
                "total_processes": len(processes),
                "python_processes": len(python_procs),
                "whisper_processes": len(whisper_procs),
                "python_memory_total_percent": sum(p.info['memory_percent'] or 0 for p in python_procs),
                "python_cpu_total_percent": sum(p.info['cpu_percent'] or 0 for p in python_procs),
                "python_threads_total": sum(p.info['num_threads'] or 0 for p in python_procs),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _estimate_inference_timing(self) -> Dict:
        """Estimate inference timing by checking recent operation logs"""
        # This is a placeholder - can be enhanced to parse actual timing logs
        # from wake_word_audit.csv, agent metrics, etc.
        
        try:
            audit_file = ROOT / "logs" / "wake_word_audit.csv"
            
            if not audit_file.exists():
                return {"available": False, "reason": "No wake_word_audit.csv found"}
            
            # Read last 10 entries for recent timing
            import csv
            timings = []
            
            with audit_file.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Get last 10 rows with timing data
                for row in rows[-10:]:
                    if "latency_ms" in row:
                        try:
                            timings.append(float(row["latency_ms"]))
                        except:
                            continue
            
            if not timings:
                return {"available": False, "reason": "No timing data in recent logs"}
            
            return {
                "available": True,
                "wake_word_latency_ms": {
                    "mean": sum(timings) / len(timings),
                    "min": min(timings),
                    "max": max(timings),
                    "count": len(timings),
                }
            }
            
        except Exception as e:
            return {"available": False, "reason": str(e)}
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to JSONL file"""
        try:
            with self.metrics_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to save metrics: {e}")
    
    def generate_profile_summary(self) -> Dict:
        """Generate a summary of hardware capabilities and limitations"""
        gpu_info = self.hardware_profile.get("gpu", {})
        cpu_info = self.hardware_profile.get("cpu", {})
        memory_info = self.hardware_profile.get("memory", {})
        
        # Assess hardware tier
        gpu_available = gpu_info.get("available", False)
        gpu_memory = gpu_info.get("memory_total_mb", 0)
        system_memory = memory_info.get("total_gb", 0)
        
        # Determine tier
        if gpu_memory >= 8000 and system_memory >= 24:
            tier = "high_end"
            capability = "Can run large models, full multi-agent parallelism"
        elif gpu_memory >= 4000 and system_memory >= 16:
            tier = "mid_range"
            capability = "Can run medium models, limited parallelism, some throttling"
        elif gpu_available and system_memory >= 8:
            tier = "entry_level"
            capability = "Can run small models, heavy throttling, serial operations"
        else:
            tier = "cpu_only"
            capability = "CPU-only inference, minimal capabilities"
        
        # Identify limitations
        limitations = []
        if gpu_memory < 6000:
            limitations.append("GPU VRAM insufficient for medium/large models")
        if system_memory < 16:
            limitations.append("RAM may limit multi-agent operations")
        if cpu_info.get("physical_cores", 0) < 4:
            limitations.append("CPU cores insufficient for heavy parallelism")
        
        # Recommended optimizations
        optimizations = []
        if tier == "entry_level" or tier == "mid_range":
            optimizations.append("Use model serialization (ASR on CPU, LLM on GPU or vice versa)")
            optimizations.append("Increase scheduler intervals to reduce load")
            optimizations.append("Limit concurrent agent operations")
        if gpu_memory < 6000:
            optimizations.append("Prefer quantized models (Q4 over Q5/Q8)")
            optimizations.append("Use small/tiny model variants")
        
        return {
            "profile_name": self.profile_name,
            "tier": tier,
            "capability_summary": capability,
            "hardware": {
                "gpu": gpu_info.get("name", "Unknown"),
                "gpu_memory_gb": round(gpu_memory / 1024, 2) if gpu_memory else 0,
                "cpu_cores": cpu_info.get("physical_cores", 0),
                "system_memory_gb": system_memory,
            },
            "limitations": limitations,
            "recommended_optimizations": optimizations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def run_benchmark(self, duration_seconds: int = 60) -> Dict:
        """Run a quick benchmark to assess performance"""
        print(f"\n[BENCHMARK] Starting {duration_seconds}s hardware benchmark...")
        
        start_time = time.time()
        samples = []
        
        while time.time() - start_time < duration_seconds:
            metrics = self.collect_runtime_metrics()
            samples.append(metrics)
            self.save_metrics(metrics)
            
            # Print progress
            elapsed = int(time.time() - start_time)
            print(f"[BENCHMARK] {elapsed}/{duration_seconds}s - "
                  f"CPU: {metrics['cpu'].get('percent_total', 0):.1f}% | "
                  f"GPU: {metrics['gpu'].get('utilization_percent', 0):.1f}% | "
                  f"VRAM: {metrics['gpu'].get('memory_used_mb', 0):.0f}MB")
            
            time.sleep(5)  # Sample every 5 seconds during benchmark
        
        # Calculate statistics
        cpu_percentages = [s['cpu'].get('percent_total', 0) for s in samples if 'cpu' in s]
        gpu_utils = [s['gpu'].get('utilization_percent', 0) for s in samples if 'gpu' in s and s['gpu'].get('available')]
        vram_usage = [s['gpu'].get('memory_used_mb', 0) for s in samples if 'gpu' in s and s['gpu'].get('available')]
        
        benchmark_results = {
            "duration_seconds": duration_seconds,
            "samples_collected": len(samples),
            "cpu_stats": {
                "mean": sum(cpu_percentages) / len(cpu_percentages) if cpu_percentages else 0,
                "max": max(cpu_percentages) if cpu_percentages else 0,
                "min": min(cpu_percentages) if cpu_percentages else 0,
            },
            "gpu_stats": {
                "mean_utilization": sum(gpu_utils) / len(gpu_utils) if gpu_utils else 0,
                "max_utilization": max(gpu_utils) if gpu_utils else 0,
                "mean_vram_mb": sum(vram_usage) / len(vram_usage) if vram_usage else 0,
                "max_vram_mb": max(vram_usage) if vram_usage else 0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        print(f"\n[BENCHMARK] Complete!")
        print(f"  CPU Average: {benchmark_results['cpu_stats']['mean']:.1f}%")
        print(f"  GPU Average: {benchmark_results['gpu_stats']['mean_utilization']:.1f}%")
        print(f"  VRAM Average: {benchmark_results['gpu_stats']['mean_vram_mb']:.0f}MB")
        
        return benchmark_results
    
    def run_continuous(self, interval_seconds: Optional[int] = None):
        """Run continuous metrics collection"""
        interval = interval_seconds or self.collection_interval
        
        print(f"\n[HARDWARE PROFILER] Started for profile: {self.profile_name}")
        print(f"[HARDWARE PROFILER] Collection interval: {interval} seconds")
        print(f"[HARDWARE PROFILER] Metrics file: {self.metrics_file}")
        
        # Print profile summary
        summary = self.generate_profile_summary()
        print(f"\n[PROFILE] Hardware Tier: {summary['tier']}")
        print(f"[PROFILE] GPU: {summary['hardware']['gpu']} ({summary['hardware']['gpu_memory_gb']}GB)")
        print(f"[PROFILE] RAM: {summary['hardware']['system_memory_gb']}GB")
        
        if summary['limitations']:
            print(f"\n[LIMITATIONS]")
            for limitation in summary['limitations']:
                print(f"  ⚠️  {limitation}")
        
        if summary['recommended_optimizations']:
            print(f"\n[OPTIMIZATIONS]")
            for opt in summary['recommended_optimizations']:
                print(f"  💡 {opt}")
        
        # Initial collection
        print(f"\n[COLLECT] Collecting initial metrics...")
        metrics = self.collect_runtime_metrics()
        self.save_metrics(metrics)
        
        while True:
            try:
                time.sleep(interval)
                
                metrics = self.collect_runtime_metrics()
                self.save_metrics(metrics)
                
                # Print summary
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Metrics collected:")
                print(f"  CPU: {metrics['cpu'].get('percent_total', 0):.1f}%")
                print(f"  Memory: {metrics['memory'].get('percent', 0):.1f}%")
                
                if metrics['gpu'].get('available'):
                    print(f"  GPU Util: {metrics['gpu'].get('utilization_percent', 0):.1f}%")
                    print(f"  VRAM: {metrics['gpu'].get('memory_used_mb', 0):.0f}MB / "
                          f"{metrics['gpu'].get('memory_free_mb', 0):.0f}MB free")
                    print(f"  GPU Temp: {metrics['gpu'].get('temperature_celsius', 0):.0f}°C")
                
            except KeyboardInterrupt:
                print("\n[HARDWARE PROFILER] Stopped by user")
                break
            except Exception as e:
                print(f"[ERROR] Collection failed: {e}")
                time.sleep(30)


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hardware Performance Profiler")
    parser.add_argument("--profile", type=str, help="Profile name (auto-detected if not specified)")
    parser.add_argument("--interval", type=int, default=60, help="Collection interval in seconds (default: 60)")
    parser.add_argument("--benchmark", type=int, help="Run benchmark for N seconds instead of continuous collection")
    parser.add_argument("--summary", action="store_true", help="Print profile summary and exit")
    
    args = parser.parse_args()
    
    profiler = HardwareProfiler(profile_name=args.profile)
    
    if args.summary:
        summary = profiler.generate_profile_summary()
        print(json.dumps(summary, indent=2))
    elif args.benchmark:
        results = profiler.run_benchmark(duration_seconds=args.benchmark)
        print(f"\n[RESULTS]")
        print(json.dumps(results, indent=2))
    else:
        profiler.run_continuous(interval_seconds=args.interval)


if __name__ == "__main__":
    main()
