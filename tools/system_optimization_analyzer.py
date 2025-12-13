#!/usr/bin/env python3
"""Comprehensive system optimization analysis."""
import json
import psutil
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def analyze_system_resources():
    """Analyze current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_available_gb": memory.available / (1024**3),
        "disk_free_percent": disk.free / disk.total * 100,
        "disk_free_gb": disk.free / (1024**3),
    }

def analyze_config_optimization():
    """Analyze config.yaml for optimization opportunities."""
    import yaml
    
    with open(ROOT / "config.yaml") as f:
        config = yaml.safe_load(f)
    
    issues = []
    recommendations = []
    
    # Check model configuration
    if config.get("settings", {}).get("faster_whisper_device") == "cpu":
        recommendations.append({
            "category": "GPU Utilization",
            "issue": "ASR using CPU instead of GPU",
            "recommendation": "Enable GPU for faster-whisper",
            "impact": "HIGH - Significantly faster ASR processing",
            "config_key": "settings.faster_whisper_device"
        })
    
    # Check KWS settings
    kws = config.get("settings", {}).get("kws", {})
    if not kws.get("enabled", False):
        recommendations.append({
            "category": "Wake Word Detection",
            "issue": "KWS disabled",
            "recommendation": "Enable KWS for efficient wake word detection",
            "impact": "MEDIUM - Reduced CPU load for audio processing",
            "config_key": "settings.kws.enabled"
        })
    
    # Check scheduler interval
    scheduler_interval = config.get("settings", {}).get("scheduler", {}).get("interval_sec", 240)
    if scheduler_interval < 180:
        recommendations.append({
            "category": "Scheduler Optimization",
            "issue": f"Scheduler interval very short ({scheduler_interval}s)",
            "recommendation": "Consider increasing to 300s for better resource management",
            "impact": "LOW - Better capacity management",
            "config_key": "settings.scheduler.interval_sec"
        })
    
    # Check VAD settings
    vad = config.get("settings", {}).get("vad", {})
    if not vad.get("webrtcvad_enabled", False):
        recommendations.append({
            "category": "Voice Activity Detection",
            "issue": "WebRTC VAD disabled",
            "recommendation": "Enable WebRTC VAD for efficient voice detection",
            "impact": "MEDIUM - Reduced audio processing load",
            "config_key": "settings.vad.webrtcvad_enabled"
        })
    
    return recommendations

def analyze_workflow_patterns():
    """Analyze workflow patterns from metrics."""
    import csv
    
    issues = []
    
    try:
        with open(ROOT / "logs" / "agent_metrics.csv") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            if len(rows) < 10:
                return issues
            
            # Analyze duration patterns
            durations = [float(r.get("duration_s", 0)) for r in rows[-50:] if r.get("duration_s")]
            if durations:
                avg_duration = sum(durations) / len(durations)
                max_duration = max(durations)
                
                if avg_duration > 200:
                    issues.append({
                        "category": "Performance",
                        "issue": f"Average task duration high ({avg_duration:.1f}s)",
                        "recommendation": "Review task complexity and LLM efficiency",
                        "impact": "MEDIUM - Slower workflow completion"
                    })
                
                if max_duration > 400:
                    issues.append({
                        "category": "Performance",
                        "issue": f"Some tasks exceed 400s (max: {max_duration:.1f}s)",
                        "recommendation": "Investigate long-running tasks",
                        "impact": "HIGH - User experience degradation"
                    })
            
            # Analyze TES patterns
            tes_scores = [float(r.get("tes", 0)) for r in rows[-50:] if r.get("tes")]
            if tes_scores:
                avg_tes = sum(tes_scores) / len(tes_scores)
                if avg_tes < 90:
                    issues.append({
                        "category": "Quality",
                        "issue": f"Average TES below 90 ({avg_tes:.1f})",
                        "recommendation": "Review test failures and stability",
                        "impact": "MEDIUM - Quality concerns"
                    })
    
    except Exception as e:
        pass
    
    return issues

def main():
    print("[SSA] Comprehensive System Optimization Analysis")
    print("=" * 60)
    
    # System resources
    print("\n[Current System Resources]")
    resources = analyze_system_resources()
    print(f"  CPU: {resources['cpu_percent']:.1f}%")
    print(f"  Memory: {resources['memory_percent']:.1f}% ({resources['memory_available_gb']:.2f} GB available)")
    print(f"  Disk: {resources['disk_free_percent']:.1f}% free ({resources['disk_free_gb']:.2f} GB)")
    
    # Config optimization
    print("\n[Configuration Optimization Opportunities]")
    config_recs = analyze_config_optimization()
    if config_recs:
        for rec in config_recs:
            print(f"\n  [{rec['category']}] {rec['issue']}")
            print(f"    Recommendation: {rec['recommendation']}")
            print(f"    Impact: {rec['impact']}")
    else:
        print("  No immediate configuration optimizations identified")
    
    # Workflow patterns
    print("\n[Workflow Pattern Analysis]")
    workflow_issues = analyze_workflow_patterns()
    if workflow_issues:
        for issue in workflow_issues:
            print(f"\n  [{issue['category']}] {issue['issue']}")
            print(f"    Recommendation: {issue['recommendation']}")
            print(f"    Impact: {issue['impact']}")
    else:
        print("  Workflow patterns appear healthy")
    
    # Summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "resources": resources,
        "config_recommendations": config_recs,
        "workflow_issues": workflow_issues,
        "total_opportunities": len(config_recs) + len(workflow_issues)
    }
    
    report_file = ROOT / "outgoing" / "overseer_reports" / f"optimization_analysis_{int(time.time())}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n[Analysis Complete] Report saved: {report_file.relative_to(ROOT)}")
    print(f"\n[Summary] {len(config_recs)} config recommendations, {len(workflow_issues)} workflow issues")
    
    return report

if __name__ == "__main__":
    main()

