#!/usr/bin/env python3
"""
AI-for-All Teaching System - Resource-Aware Learning Module
Adaptive learning that respects system resource constraints and optimizes performance
"""

import json
import time
import psutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml

@dataclass
class ResourceThresholds:
    """Resource thresholds for teaching system decisions"""
    cpu_soft: float = 70.0
    cpu_hard: float = 85.0
    memory_soft: float = 75.0
    memory_hard: float = 90.0
    disk_io_soft: float = 60.0
    disk_io_hard: float = 80.0

@dataclass
class TeachingResourceProfile:
    """Resource consumption profile for different teaching activities"""
    activity_type: str
    cpu_usage: float
    memory_usage: float
    duration_minutes: int
    priority: str  # critical, high, normal, low

@dataclass
class LearningAdaptation:
    """Adaptation decision for teaching system"""
    timestamp: datetime
    resource_status: str  # normal, constrained, critical
    adaptation_type: str  # scale_back, pause, optimize, resume
    original_settings: Dict
    adapted_settings: Dict
    reason: str
    estimated_impact: str

class ResourceAwareLearner:
    """Resource-aware teaching system that adapts to system constraints"""

    def __init__(self, config_path: str = "../../../config.yaml"):
        # Setup logging first
        self.logger = self._setup_logging()

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.thresholds = self._load_resource_thresholds()

        # Teaching activity profiles
        self.resource_profiles = self._initialize_resource_profiles()

        # Adaptation history
        self.adaptation_history = []
        self.max_adaptations = 100

        # Current system state
        self.current_resource_status = "normal"
        self.last_resource_check = None

    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            return {}

    def _load_resource_thresholds(self) -> ResourceThresholds:
        """Load resource thresholds from configuration"""
        thresholds = ResourceThresholds()

        if 'ai4all_optimization' in self.config:
            opt_config = self.config['ai4all_optimization']
            if 'performance_protection' in opt_config:
                prot_config = opt_config['performance_protection']
                if 'emergency_resource_thresholds' in prot_config:
                    thresh_config = prot_config['emergency_resource_thresholds']

                    thresholds.cpu_soft = thresh_config.get('cpu_usage', 70)
                    thresholds.memory_soft = thresh_config.get('memory_usage', 75)
                    thresholds.disk_io_soft = thresh_config.get('disk_io', 60)

        return thresholds

    def _initialize_resource_profiles(self) -> Dict[str, TeachingResourceProfile]:
        """Initialize resource consumption profiles for teaching activities"""
        return {
            'baseline_establishment': TeachingResourceProfile(
                activity_type='baseline_establishment',
                cpu_usage=40.0,
                memory_usage=200.0,  # MB
                duration_minutes=15,
                priority='high'
            ),
            'pattern_analysis': TeachingResourceProfile(
                activity_type='pattern_analysis',
                cpu_usage=60.0,
                memory_usage=300.0,
                duration_minutes=20,
                priority='high'
            ),
            'knowledge_integration': TeachingResourceProfile(
                activity_type='knowledge_integration',
                cpu_usage=35.0,
                memory_usage=150.0,
                duration_minutes=10,
                priority='normal'
            ),
            'performance_tracking': TeachingResourceProfile(
                activity_type='performance_tracking',
                cpu_usage=20.0,
                memory_usage=100.0,
                duration_minutes=5,
                priority='low'
            ),
            'cross_agent_sharing': TeachingResourceProfile(
                activity_type='cross_agent_sharing',
                cpu_usage=45.0,
                memory_usage=250.0,
                duration_minutes=12,
                priority='normal'
            ),
            'predictive_optimization': TeachingResourceProfile(
                activity_type='predictive_optimization',
                cpu_usage=50.0,
                memory_usage=180.0,
                duration_minutes=8,
                priority='high'
            )
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for resource-aware learner"""
        logger = logging.getLogger('resource_aware_learner')
        logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = Path("../../logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        log_file = log_dir / "ai4all_resource_aware.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def get_current_resource_usage(self) -> Dict[str, float]:
        """Get current system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_mb': memory.used / (1024 * 1024),
                'disk_io_read_mb': disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                'disk_io_write_mb': disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {e}")
            return {}

    def evaluate_resource_status(self, resource_usage: Dict[str, float]) -> str:
        """Evaluate current resource status against thresholds"""
        cpu = resource_usage.get('cpu_percent', 0)
        memory = resource_usage.get('memory_percent', 0)

        if cpu >= self.thresholds.cpu_hard or memory >= self.thresholds.memory_hard:
            return 'critical'
        elif cpu >= self.thresholds.cpu_soft or memory >= self.thresholds.memory_soft:
            return 'constrained'
        else:
            return 'normal'

    def estimate_teaching_impact(self, activity_type: str, concurrent_activities: int = 1) -> Dict[str, float]:
        """Estimate resource impact of teaching activities"""
        if activity_type not in self.resource_profiles:
            return {'cpu_impact': 0, 'memory_impact': 0}

        profile = self.resource_profiles[activity_type]

        # Scale impact based on concurrent activities
        cpu_impact = profile.cpu_usage * concurrent_activities
        memory_impact = profile.memory_usage * concurrent_activities

        return {
            'cpu_impact': cpu_impact,
            'memory_impact': memory_impact,
            'estimated_duration': profile.duration_minutes * concurrent_activities,
            'priority': profile.priority
        }

    def should_scale_back_teaching(self, planned_activities: List[str], current_resources: Dict[str, float]) -> bool:
        """Determine if teaching activities should be scaled back"""
        if not planned_activities:
            return False

        # Calculate total estimated impact
        total_cpu_impact = 0
        total_memory_impact = 0

        for activity in planned_activities:
            impact = self.estimate_teaching_impact(activity)
            total_cpu_impact += impact['cpu_impact']
            total_memory_impact += impact['memory_impact']

        current_cpu = current_resources.get('cpu_percent', 0)
        current_memory = current_resources.get('memory_percent', 0)

        # Scale back if estimated impact would exceed safe thresholds
        safe_cpu_threshold = self.thresholds.cpu_soft * 0.8  # Use 80% of soft limit as safety margin
        safe_memory_threshold = self.thresholds.memory_soft * 0.8

        return (current_cpu + total_cpu_impact > safe_cpu_threshold or
                current_memory + total_memory_impact > safe_memory_threshold)

    def create_teaching_adaptation(self, activity_type: str, adaptation_type: str,
                                   reason: str, original_settings: Dict, adapted_settings: Dict) -> LearningAdaptation:
        """Create a learning adaptation record"""
        adaptation = LearningAdaptation(
            timestamp=datetime.now(),
            resource_status=self.current_resource_status,
            adaptation_type=adaptation_type,
            original_settings=original_settings,
            adapted_settings=adapted_settings,
            reason=reason,
            estimated_impact=self._calculate_adaptation_impact(original_settings, adapted_settings)
        )

        # Add to history
        self.adaptation_history.append(adaptation)
        if len(self.adaptation_history) > self.max_adaptations:
            self.adaptation_history.pop(0)

        return adaptation

    def _calculate_adaptation_impact(self, original: Dict, adapted: Dict) -> str:
        """Calculate the estimated impact of an adaptation"""
        # Simple impact calculation based on key parameters
        if 'batch_size' in original and 'batch_size' in adapted:
            original_size = original['batch_size']
            adapted_size = adapted['batch_size']

            if adapted_size < original_size:
                reduction_percent = ((original_size - adapted_size) / original_size) * 100
                return f"Reduced batch size by {reduction_percent:.1f}% to conserve resources"

        if 'concurrent_learners' in original and 'concurrent_learners' in adapted:
            original_learners = original['concurrent_learners']
            adapted_learners = adapted['concurrent_learners']

            if adapted_learners < original_learners:
                reduction_percent = ((original_learners - adapted_learners) / original_learners) * 100
                return f"Reduced concurrent learners by {reduction_percent:.1f}% to manage system load"

        return "Resource optimization applied based on current system constraints"

    def suggest_teaching_optimizations(self, planned_activities: List[str],
                                      current_resources: Dict[str, float]) -> Dict[str, Any]:
        """Suggest optimizations for teaching activities based on resource constraints"""
        suggestions = {
            'should_proceed': True,
            'adaptations': [],
            'estimated_resource_usage': {},
            'recommendations': []
        }

        # Check if we should scale back
        if self.should_scale_back_teaching(planned_activities, current_resources):
            suggestions['should_proceed'] = False

            # Suggest specific adaptations
            for activity in planned_activities:
                profile = self.resource_profiles.get(activity, TeachingResourceProfile(activity, 25, 100, 5, 'normal'))
                impact = self.estimate_teaching_impact(activity)

                # Create adaptation suggestions
                if impact['cpu_impact'] > 30:  # High CPU activities
                    adaptation = {
                        'activity': activity,
                        'type': 'batch_size_reduction',
                        'original_batch_size': 100,
                        'suggested_batch_size': 50,
                        'reason': 'High CPU usage detected'
                    }
                    suggestions['adaptations'].append(adaptation)

                if impact['memory_impact'] > 200:  # High memory activities
                    adaptation = {
                        'activity': activity,
                        'type': 'memory_optimization',
                        'original_cache_size': 1000,
                        'suggested_cache_size': 500,
                        'reason': 'High memory usage detected'
                    }
                    suggestions['adaptations'].append(adaptation)

            suggestions['recommendations'].append(
                "Consider deferring intensive learning activities until resource usage normalizes"
            )

        # Calculate estimated resource usage
        for activity in planned_activities:
            impact = self.estimate_teaching_impact(activity)
            suggestions['estimated_resource_usage'][activity] = impact

        return suggestions

    def optimize_knowledge_sharing(self, data_size_mb: float, current_resources: Dict[str, float]) -> Dict[str, Any]:
        """Optimize knowledge sharing based on resource constraints"""
        optimizations = {
            'compression_applied': False,
            'batch_size_reduced': False,
            'priority_adjusted': False,
            'settings': {}
        }

        # Check if compression would be beneficial
        if data_size_mb > 10 and current_resources.get('disk_io_write_mb', 0) > 50:
            optimizations['compression_applied'] = True
            optimizations['settings']['compression_enabled'] = True
            optimizations['settings']['compression_threshold'] = 5  # MB

        # Reduce batch size if memory is constrained
        memory_percent = current_resources.get('memory_percent', 0)
        if memory_percent > self.thresholds.memory_soft:
            optimizations['batch_size_reduced'] = True
            reduction_factor = max(0.3, 1.0 - ((memory_percent - self.thresholds.memory_soft) / 100))
            original_batch = 100
            optimizations['settings']['batch_size'] = int(original_batch * reduction_factor)

        # Adjust priority based on resource availability
        if self.current_resource_status == 'constrained':
            optimizations['priority_adjusted'] = True
            optimizations['settings']['priority'] = 'low'

        return optimizations

    def generate_resource_report(self) -> str:
        """Generate a resource-aware teaching report"""
        report_lines = [
            "# AI-for-All Resource-Aware Learning Report",
            f"**Generated:** {datetime.now().isoformat()}",
            f"**Agent:** Systems Resources Agent",
            "",
            "## Current System Status",
            f"- Resource Status: {self.current_resource_status}",
            f"- Adaptations Applied: {len(self.adaptation_history)}",
            "",
            "## Resource Profiles"
        ]

        for activity, profile in self.resource_profiles.items():
            report_lines.extend([
                f"### {activity}",
                f"- CPU Usage: {profile.cpu_usage}%",
                f"- Memory Usage: {profile.memory_usage} MB",
                f"- Duration: {profile.duration_minutes} minutes",
                f"- Priority: {profile.priority}",
                ""
            ])

        if self.adaptation_history:
            report_lines.extend([
                "## Recent Adaptations",
                ""
            ])

            for adaptation in self.adaptation_history[-5:]:  # Last 5 adaptations
                report_lines.extend([
                    f"### {adaptation.adaptation_type} - {adaptation.timestamp}",
                    f"- Resource Status: {adaptation.resource_status}",
                    f"- Reason: {adaptation.reason}",
                    f"- Impact: {adaptation.estimated_impact}",
                    ""
                ])

        return "\n".join(report_lines)

    def get_resource_aware_recommendations(self, planned_activities: List[str]) -> List[str]:
        """Get resource-aware recommendations for teaching activities"""
        recommendations = []

        # Check current resource status
        current_resources = self.get_current_resource_usage()
        self.current_resource_status = self.evaluate_resource_status(current_resources)

        if self.current_resource_status == 'critical':
            recommendations.append("CRITICAL: System resources severely constrained. Consider pausing all teaching activities.")
            recommendations.append("Emergency mode: Only essential system operations should continue.")

        elif self.current_resource_status == 'constrained':
            recommendations.append("WARNING: System resources approaching limits. Consider reducing teaching intensity.")
            recommendations.append("Suggestion: Focus on high-priority learning objectives only.")

            # Activity-specific recommendations
            for activity in planned_activities:
                if activity in self.resource_profiles:
                    profile = self.resource_profiles[activity]
                    if profile.priority == 'low':
                        recommendations.append(f"Consider deferring {activity} until resource usage normalizes")

        else:
            recommendations.append("System resources normal. Full teaching activities can proceed.")
            recommendations.append("Monitor resource usage during intensive learning cycles.")

        return recommendations

def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description='AI-for-All Resource-Aware Learning System')
    parser.add_argument('--check-resources', action='store_true', help='Check current resource status')
    parser.add_argument('--evaluate-activities', nargs='+', help='Evaluate resource impact of specific activities')
    parser.add_argument('--optimize-sharing', type=float, help='Optimize knowledge sharing for data size (MB)')
    parser.add_argument('--recommendations', nargs='+', default=['pattern_analysis', 'knowledge_integration'], help='Get recommendations for activities')
    parser.add_argument('--report', action='store_true', help='Generate resource-aware teaching report')

    args = parser.parse_args()

    learner = ResourceAwareLearner()

    if args.check_resources:
        resources = learner.get_current_resource_usage()
        status = learner.evaluate_resource_status(resources)

        print(f"[C:REPORT] — Systems Resources Agent: Current Resource Status")
        print(f"[Agent • Systems Resources]: CPU: {resources.get('cpu_percent', 0):.1f}")
        print(f"[Agent • Systems Resources]: Memory: {resources.get('memory_percent', 0):.1f}")
        print(f"[Agent • Systems Resources]: Status: {status}")

    elif args.evaluate_activities:
        print(f"[C:REPORT] — Systems Resources Agent: Activity Resource Impact Analysis")

        for activity in args.evaluate_activities:
            impact = learner.estimate_teaching_impact(activity)
            if impact['cpu_impact'] > 0:
                print(f"[Agent • Systems Resources]: {activity}:")
                print(f"[Agent • Systems Resources]:   CPU Impact: {impact['cpu_impact']:.1f}")
                print(f"[Agent • Systems Resources]:   Memory Impact: {impact['memory_impact']:.1f}")
                print(f"[Agent • Systems Resources]:   Duration: {impact['estimated_duration']} minutes")
            else:
                print(f"[Agent • Systems Resources]: Unknown activity: {activity}")

    elif args.optimize_sharing:
        resources = learner.get_current_resource_usage()
        optimizations = learner.optimize_knowledge_sharing(args.optimize_sharing, resources)

        print(f"[C:REPORT] — Systems Resources Agent: Knowledge Sharing Optimization")
        print(f"[Agent • Systems Resources]: Data Size: {args.optimize_sharing} MB")
        print(f"[Agent • Systems Resources]: Optimizations Applied:")

        if optimizations['compression_applied']:
            print(f"[Agent • Systems Resources]:   - Compression enabled")
        if optimizations['batch_size_reduced']:
            batch_size = optimizations['settings'].get('batch_size', 'N/A')
            print(f"[Agent • Systems Resources]:   - Batch size reduced to {batch_size}")
        if optimizations['priority_adjusted']:
            print(f"[Agent • Systems Resources]:   - Priority adjusted to low")

    elif args.recommendations:
        recommendations = learner.get_resource_aware_recommendations(args.recommendations)

        print(f"[C:REPORT] — Systems Resources Agent: Teaching Recommendations")
        print(f"[Agent • Systems Resources]: Planned Activities: {', '.join(args.recommendations)}")

        for rec in recommendations:
            print(f"[Agent • Systems Resources]: - {rec}")

    elif args.report:
        report = learner.generate_resource_report()
        print(report)

    else:
        # Default: show current status and recommendations
        print(f"[C:REPORT] — Systems Resources Agent: AI-for-All Resource-Aware Learning System")
        print(f"[Agent • Systems Resources]: Use --help for available commands")

        resources = learner.get_current_resource_usage()
        status = learner.evaluate_resource_status(resources)

        print(f"[Agent • Systems Resources]: Current Status: {status}")
        print(f"[Agent • Systems Resources]: CPU: {resources.get('cpu_percent', 0):.1f}")
        print(f"[Agent • Systems Resources]: Memory: {resources.get('memory_percent', 0):.1f}")

        recommendations = learner.get_resource_aware_recommendations(['pattern_analysis'])
        for rec in recommendations:
            print(f"[Agent • Systems Resources]: - {rec}")

if __name__ == "__main__":
    main()
