#!/usr/bin/env python3
"""
Hardware Performance Comparative Analyzer
Generates reports comparing performance across different hardware profiles

Use Cases:
- Compare laptop (MX150) vs desktop (RTX 2070S) performance
- Identify bottlenecks and optimization opportunities
- Generate hardware requirement recommendations for BloomOS
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import statistics

ROOT = Path(__file__).resolve().parent.parent


class HardwareComparator:
    """Compare performance metrics across hardware profiles"""
    
    def __init__(self):
        self.config_file = ROOT / "config" / "hardware_profiles.json"
        self.reports_dir = ROOT / "Codex" / "Reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def load_profile_config(self) -> Dict:
        """Load hardware profile configuration"""
        if not self.config_file.exists():
            return {"profiles": {}}
        
        with self.config_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_metrics_for_profile(self, profile_name: str, hours: int = 24) -> List[Dict]:
        """Load metrics for a specific profile from last N hours"""
        metrics_file = ROOT / "logs" / f"hardware_profile_{profile_name}.jsonl"
        
        if not metrics_file.exists():
            return []
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        metrics = []
        
        with metrics_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    
                    if entry_time >= cutoff:
                        metrics.append(entry)
                except:
                    continue
        
        return metrics
    
    def calculate_statistics(self, values: List[float]) -> Dict:
        """Calculate statistical summary"""
        if not values:
            return {"count": 0}
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
        }
    
    def analyze_profile_metrics(self, profile_name: str, hours: int = 24) -> Dict:
        """Analyze metrics for a single profile"""
        metrics = self.load_metrics_for_profile(profile_name, hours)
        
        if not metrics:
            return {"profile_name": profile_name, "error": "No metrics found"}
        
        # Extract metric series
        cpu_util = [m['cpu'].get('percent_total', 0) for m in metrics if 'cpu' in m]
        memory_util = [m['memory'].get('percent', 0) for m in metrics if 'memory' in m]
        
        gpu_util = [m['gpu'].get('utilization_percent', 0) for m in metrics 
                    if 'gpu' in m and m['gpu'].get('available')]
        vram_used = [m['gpu'].get('memory_used_mb', 0) for m in metrics 
                     if 'gpu' in m and m['gpu'].get('available')]
        gpu_temp = [m['gpu'].get('temperature_celsius', 0) for m in metrics 
                    if 'gpu' in m and m['gpu'].get('available')]
        gpu_power = [m['gpu'].get('power_draw_watts', 0) for m in metrics 
                     if 'gpu' in m and m['gpu'].get('available')]
        
        # Wake-word latency if available
        wake_word_latency = []
        for m in metrics:
            if 'inference_timing' in m and m['inference_timing'].get('available'):
                latency = m['inference_timing'].get('wake_word_latency_ms', {}).get('mean')
                if latency:
                    wake_word_latency.append(latency)
        
        analysis = {
            "profile_name": profile_name,
            "period_hours": hours,
            "sample_count": len(metrics),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu": self.calculate_statistics(cpu_util),
            "memory": self.calculate_statistics(memory_util),
            "gpu": {
                "utilization": self.calculate_statistics(gpu_util),
                "vram_mb": self.calculate_statistics(vram_used),
                "temperature_celsius": self.calculate_statistics(gpu_temp),
                "power_watts": self.calculate_statistics(gpu_power),
            },
            "wake_word_latency_ms": self.calculate_statistics(wake_word_latency),
        }
        
        # Add assessment
        analysis["assessment"] = self._generate_assessment(analysis)
        
        return analysis
    
    def _generate_assessment(self, analysis: Dict) -> Dict:
        """Generate performance assessment"""
        assessment = {
            "bottlenecks": [],
            "strengths": [],
            "recommendations": [],
        }
        
        # CPU assessment
        cpu_mean = analysis['cpu'].get('mean', 0)
        if cpu_mean > 80:
            assessment["bottlenecks"].append(f"High CPU utilization ({cpu_mean:.1f}%)")
            assessment["recommendations"].append("Consider offloading more work to GPU")
        elif cpu_mean < 30:
            assessment["strengths"].append(f"Low CPU utilization ({cpu_mean:.1f}%)")
        
        # GPU assessment
        gpu_util_mean = analysis['gpu']['utilization'].get('mean', 0)
        vram_mean = analysis['gpu']['vram_mb'].get('mean', 0)
        vram_max = analysis['gpu']['vram_mb'].get('max', 0)
        
        if gpu_util_mean > 90:
            assessment["bottlenecks"].append(f"GPU saturated ({gpu_util_mean:.1f}%)")
        elif gpu_util_mean < 20:
            assessment["strengths"].append(f"GPU underutilized ({gpu_util_mean:.1f}%) - headroom available")
            assessment["recommendations"].append("Consider moving more workload to GPU")
        
        if vram_max > 3500:  # Approaching 4GB limit on MX150
            assessment["bottlenecks"].append(f"VRAM near capacity ({vram_max:.0f}MB)")
            assessment["recommendations"].append("Risk of OOM - consider smaller models or CPU fallback")
        
        # Temperature assessment
        temp_max = analysis['gpu']['temperature_celsius'].get('max', 0)
        if temp_max > 80:
            assessment["bottlenecks"].append(f"High GPU temperature ({temp_max:.0f}°C)")
            assessment["recommendations"].append("Thermal throttling risk - improve cooling or reduce load")
        
        # Wake-word latency
        latency_mean = analysis['wake_word_latency_ms'].get('mean', 0)
        if latency_mean > 2000:
            assessment["bottlenecks"].append(f"High wake-word latency ({latency_mean:.0f}ms)")
            assessment["recommendations"].append("Consider optimizing ASR pipeline or model size")
        elif latency_mean < 1000 and latency_mean > 0:
            assessment["strengths"].append(f"Good wake-word latency ({latency_mean:.0f}ms)")
        
        return assessment
    
    def compare_profiles(self, profile1: str, profile2: str, hours: int = 24) -> Dict:
        """Compare two hardware profiles"""
        analysis1 = self.analyze_profile_metrics(profile1, hours)
        analysis2 = self.analyze_profile_metrics(profile2, hours)
        
        if "error" in analysis1 or "error" in analysis2:
            return {
                "error": "Cannot compare - one or both profiles have no data",
                "profile1": analysis1,
                "profile2": analysis2,
            }
        
        comparison = {
            "profile1": profile1,
            "profile2": profile2,
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {},
        }
        
        # Compare CPU
        cpu1 = analysis1['cpu'].get('mean', 0)
        cpu2 = analysis2['cpu'].get('mean', 0)
        comparison["metrics"]["cpu_utilization"] = {
            f"{profile1}_mean": cpu1,
            f"{profile2}_mean": cpu2,
            "difference_pct": cpu2 - cpu1,
            "winner": profile1 if cpu1 < cpu2 else profile2,
        }
        
        # Compare GPU
        gpu1 = analysis1['gpu']['utilization'].get('mean', 0)
        gpu2 = analysis2['gpu']['utilization'].get('mean', 0)
        comparison["metrics"]["gpu_utilization"] = {
            f"{profile1}_mean": gpu1,
            f"{profile2}_mean": gpu2,
            "difference_pct": gpu2 - gpu1,
            "winner": profile1 if gpu1 < gpu2 else profile2,
        }
        
        # Compare VRAM
        vram1 = analysis1['gpu']['vram_mb'].get('mean', 0)
        vram2 = analysis2['gpu']['vram_mb'].get('mean', 0)
        comparison["metrics"]["vram_usage_mb"] = {
            f"{profile1}_mean": vram1,
            f"{profile2}_mean": vram2,
            "difference_mb": vram2 - vram1,
        }
        
        # Compare latency
        latency1 = analysis1['wake_word_latency_ms'].get('mean', 0)
        latency2 = analysis2['wake_word_latency_ms'].get('mean', 0)
        if latency1 > 0 and latency2 > 0:
            comparison["metrics"]["wake_word_latency_ms"] = {
                f"{profile1}_mean": latency1,
                f"{profile2}_mean": latency2,
                "difference_ms": latency2 - latency1,
                "speedup_factor": latency1 / latency2 if latency2 > 0 else 0,
            }
        
        # Generate comparison summary
        comparison["summary"] = self._generate_comparison_summary(comparison, analysis1, analysis2)
        
        return comparison
    
    def _generate_comparison_summary(self, comparison: Dict, analysis1: Dict, analysis2: Dict) -> str:
        """Generate human-readable comparison summary"""
        p1 = comparison["profile1"]
        p2 = comparison["profile2"]
        
        lines = [
            f"Comparison: {p1} vs {p2}",
            "",
            "Performance Metrics:",
        ]
        
        # CPU comparison
        cpu_diff = comparison["metrics"]["cpu_utilization"]["difference_pct"]
        if abs(cpu_diff) > 10:
            lines.append(f"  CPU: {p2} uses {abs(cpu_diff):.1f}% {'more' if cpu_diff > 0 else 'less'} CPU")
        else:
            lines.append(f"  CPU: Similar utilization (~{cpu_diff:.1f}% difference)")
        
        # GPU comparison
        gpu_diff = comparison["metrics"]["gpu_utilization"]["difference_pct"]
        if abs(gpu_diff) > 10:
            lines.append(f"  GPU: {p2} uses {abs(gpu_diff):.1f}% {'more' if gpu_diff > 0 else 'less'} GPU")
        
        # Latency comparison
        if "wake_word_latency_ms" in comparison["metrics"]:
            speedup = comparison["metrics"]["wake_word_latency_ms"].get("speedup_factor", 0)
            if speedup > 1.2:
                lines.append(f"  Latency: {p1} is {speedup:.1f}x faster than {p2}")
            elif speedup < 0.8:
                lines.append(f"  Latency: {p2} is {1/speedup:.1f}x faster than {p1}")
        
        # Bottlenecks
        bottlenecks1 = analysis1.get('assessment', {}).get('bottlenecks', [])
        bottlenecks2 = analysis2.get('assessment', {}).get('bottlenecks', [])
        
        if bottlenecks1 or bottlenecks2:
            lines.append("")
            lines.append("Bottlenecks:")
            if bottlenecks1:
                lines.append(f"  {p1}: {', '.join(bottlenecks1)}")
            if bottlenecks2:
                lines.append(f"  {p2}: {', '.join(bottlenecks2)}")
        
        return "\n".join(lines)
    
    def generate_bloomos_optimization_report(self) -> Dict:
        """Generate BloomOS hardware optimization recommendations"""
        config = self.load_profile_config()
        
        report = {
            "title": "BloomOS Hardware Optimization Report",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "profiles_analyzed": [],
            "recommendations": {
                "entry_level": [],
                "mid_range": [],
                "high_end": [],
            },
            "minimum_requirements": {},
            "optimal_requirements": {},
        }
        
        # Analyze each active profile
        for profile_name, profile_config in config.get("profiles", {}).items():
            if profile_config.get("active"):
                analysis = self.analyze_profile_metrics(profile_name, hours=168)  # 1 week
                report["profiles_analyzed"].append({
                    "name": profile_name,
                    "tier": profile_config["hardware"]["gpu"]["tier"],
                    "analysis": analysis,
                })
        
        # Generate tier-specific recommendations
        comparison_matrix = config.get("comparison_matrix", {}).get("tiers", {})
        
        for tier, specs in comparison_matrix.items():
            tier_key = tier.replace("_", " ").title()
            report["recommendations"][tier.replace("_level", "_range")] = [
                f"Whisper: {specs['whisper_model']} on {specs['whisper_device']}",
                f"LLM: Max {specs['llm_max_params_b']}B params on {specs['llm_device']}",
                f"Concurrent agents: {specs['concurrent_agents']}",
            ]
        
        # Minimum requirements (based on entry level that works)
        report["minimum_requirements"] = {
            "gpu_memory_gb": 4,
            "system_memory_gb": 16,
            "gpu_compute_capability": "6.0+",
            "whisper_model": "small",
            "llm_max_params": "3B Q4",
            "concurrent_agents": 1,
            "description": "Minimum viable configuration for basic BloomOS operations",
        }
        
        # Optimal requirements
        report["optimal_requirements"] = {
            "gpu_memory_gb": 16,
            "system_memory_gb": 32,
            "gpu_compute_capability": "8.0+",
            "whisper_model": "medium or large",
            "llm_max_params": "13B Q5 or 7B Q8",
            "concurrent_agents": 8,
            "description": "Recommended configuration for full BloomOS multi-agent capabilities",
        }
        
        return report


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hardware Performance Comparator")
    parser.add_argument("--analyze", type=str, help="Analyze single profile")
    parser.add_argument("--compare", nargs=2, help="Compare two profiles: PROFILE1 PROFILE2")
    parser.add_argument("--bloomos-report", action="store_true", help="Generate BloomOS optimization report")
    parser.add_argument("--hours", type=int, default=24, help="Hours of data to analyze (default: 24)")
    parser.add_argument("--output", type=str, help="Save report to file (Markdown)")
    
    args = parser.parse_args()
    
    comparator = HardwareComparator()
    
    if args.analyze:
        analysis = comparator.analyze_profile_metrics(args.analyze, hours=args.hours)
        print(json.dumps(analysis, indent=2))
        
    elif args.compare:
        comparison = comparator.compare_profiles(args.compare[0], args.compare[1], hours=args.hours)
        print(json.dumps(comparison, indent=2))
        print("\n" + "="*80)
        print(comparison.get("summary", ""))
        
    elif args.bloomos_report:
        report = comparator.generate_bloomos_optimization_report()
        
        if args.output:
            # Generate Markdown report
            md_lines = [
                f"# {report['title']}",
                f"**Generated:** {report['timestamp']}",
                "",
                "## Minimum Requirements",
                "",
                f"- GPU Memory: {report['minimum_requirements']['gpu_memory_gb']}GB",
                f"- System Memory: {report['minimum_requirements']['system_memory_gb']}GB",
                f"- GPU Compute: {report['minimum_requirements']['gpu_compute_capability']}",
                f"- Whisper Model: {report['minimum_requirements']['whisper_model']}",
                f"- LLM Max: {report['minimum_requirements']['llm_max_params']}",
                f"- Concurrent Agents: {report['minimum_requirements']['concurrent_agents']}",
                "",
                "## Optimal Requirements",
                "",
                f"- GPU Memory: {report['optimal_requirements']['gpu_memory_gb']}GB",
                f"- System Memory: {report['optimal_requirements']['system_memory_gb']}GB",
                f"- GPU Compute: {report['optimal_requirements']['gpu_compute_capability']}",
                f"- Whisper Model: {report['optimal_requirements']['whisper_model']}",
                f"- LLM Max: {report['optimal_requirements']['llm_max_params']}",
                f"- Concurrent Agents: {report['optimal_requirements']['concurrent_agents']}",
                "",
            ]
            
            output_path = Path(args.output)
            with output_path.open("w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))
            
            print(f"Report saved to: {output_path}")
        else:
            print(json.dumps(report, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
