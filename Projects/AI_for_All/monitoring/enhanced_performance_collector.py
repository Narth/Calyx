#!/usr/bin/env python3
"""
Enhanced Performance Data Collector - Advanced metrics extraction for AI-for-All teaching system
"""

import json
import logging
import psutil
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from .production_monitor import ProductionMonitor


class EnhancedPerformanceCollector:
    """
    Enhanced performance data collector that extracts comprehensive metrics
    from Calyx Terminal agents and system operations for teaching system learning.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize enhanced performance collector.

        Args:
            config: Configuration for performance collection
        """
        self.config = config
        self.logger = logging.getLogger("ai4all.enhanced_collector")

        # Collection settings
        self.collection_interval = config.get('collection_interval', 30)
        self.metric_history_size = config.get('metric_history_size', 1000)
        self.enable_resource_monitoring = config.get('enable_resource_monitoring', True)
        self.enable_agent_analysis = config.get('enable_agent_analysis', True)

        # Performance tracking
        self.agent_metrics_history: Dict[str, List[Dict]] = {}
        self.system_metrics_history: List[Dict] = []
        self.performance_patterns: Dict[str, Any] = {}

        # Resource monitoring
        self.resource_baselines = self._establish_resource_baselines()

        # Setup logging
        self._setup_collector_logging()

        self.logger.info("Enhanced performance collector initialized")

    def _setup_collector_logging(self):
        """Setup performance collector logging"""
        log_dir = Path("outgoing/ai4all/monitoring")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "performance_collector.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _establish_resource_baselines(self) -> Dict[str, float]:
        """Establish baseline resource usage for comparison"""
        try:
            baselines = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'network_io': 0,  # Will be calculated from changes
                'timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Established resource baselines: {baselines}")
            return baselines

        except Exception as e:
            self.logger.error(f"Error establishing resource baselines: {e}")
            return {}

    def collect_enhanced_agent_metrics(self, agent_id: str) -> Dict[str, float]:
        """
        Collect enhanced performance metrics for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary of performance metrics
        """
        metrics = {}

        try:
            # Read agent heartbeat if available
            heartbeat_file = Path(f"outgoing/{agent_id}.lock")
            if heartbeat_file.exists():
                with open(heartbeat_file, 'r') as f:
                    heartbeat_data = json.load(f)
                    metrics.update(self._extract_agent_metrics(heartbeat_data, agent_id))

            # Get agent run data if available
            agent_run_data = self._get_agent_run_metrics(agent_id)
            if agent_run_data:
                metrics.update(agent_run_data)

            # Calculate derived metrics
            enhanced_metrics = self._calculate_enhanced_metrics(agent_id, metrics)
            metrics.update(enhanced_metrics)

            # Store in history
            if agent_id not in self.agent_metrics_history:
                self.agent_metrics_history[agent_id] = []

            self.agent_metrics_history[agent_id].append({
                'timestamp': datetime.now(),
                'metrics': metrics.copy()
            })

            # Keep only recent history
            if len(self.agent_metrics_history[agent_id]) > self.metric_history_size:
                self.agent_metrics_history[agent_id] = self.agent_metrics_history[agent_id][-self.metric_history_size:]

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics for {agent_id}: {e}")
            return {}

    def _extract_agent_metrics(self, heartbeat_data: Dict[str, Any], agent_id: str) -> Dict[str, float]:
        """Extract metrics from agent heartbeat data"""
        metrics = {}

        try:
            # Basic agent status metrics
            status = heartbeat_data.get('status', 'unknown')
            metrics['agent_status'] = 1.0 if status == 'running' else 0.5 if status == 'idle' else 0.0

            # Phase-based metrics
            phase = heartbeat_data.get('phase', 'unknown')
            phase_scores = {
                'planning': 0.8,
                'executing': 1.0,
                'testing': 0.9,
                'completed': 1.0,
                'error': 0.2,
                'idle': 0.3
            }
            metrics['phase_efficiency'] = phase_scores.get(phase, 0.5)

            # Goal complexity estimation
            goal_preview = heartbeat_data.get('goal_preview', '')
            if goal_preview:
                # Simple complexity estimation based on goal length and keywords
                complexity = min(1.0, len(goal_preview) / 100.0)
                metrics['goal_complexity'] = complexity

                # Check for specific goal types
                if any(keyword in goal_preview.lower() for keyword in ['harmony', 'cadence', 'rhythm']):
                    metrics['harmony_focus'] = 1.0
                if any(keyword in goal_preview.lower() for keyword in ['test', 'validate', 'check']):
                    metrics['validation_focus'] = 1.0

            # Process information
            if 'pid' in heartbeat_data:
                pid = heartbeat_data['pid']
                try:
                    process = psutil.Process(pid)
                    metrics['process_cpu'] = process.cpu_percent()
                    metrics['process_memory'] = process.memory_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Timestamp-based metrics
            if 'ts' in heartbeat_data:
                current_time = time.time()
                last_activity = current_time - heartbeat_data['ts']
                metrics['time_since_activity'] = min(1.0, last_activity / 3600.0)  # Normalize to 0-1 (1 hour max)

        except Exception as e:
            self.logger.debug(f"Error extracting metrics from heartbeat: {e}")

        return metrics

    def _get_agent_run_metrics(self, agent_id: str) -> Dict[str, float]:
        """Get metrics from recent agent runs"""
        metrics = {}

        try:
            # Look for recent agent run directories
            agent_runs = list(Path("outgoing").glob(f"{agent_id}_run_*"))
            if not agent_runs:
                return metrics

            # Get most recent run
            latest_run = max(agent_runs, key=lambda x: x.stat().st_mtime)

            # Check for metrics or audit files
            audit_file = latest_run / "audit.json"
            if audit_file.exists():
                with open(audit_file, 'r') as f:
                    audit_data = json.load(f)

                    # Extract TES and other metrics
                    if 'tes' in audit_data:
                        metrics['tes'] = float(audit_data['tes'])

                    if 'stability' in audit_data:
                        metrics['stability'] = float(audit_data['stability'])

                    if 'velocity' in audit_data:
                        metrics['velocity'] = float(audit_data['velocity'])

                    if 'duration_s' in audit_data:
                        duration = float(audit_data['duration_s'])
                        # Convert duration to efficiency (shorter is better, up to a point)
                        metrics['execution_efficiency'] = max(0, 1.0 - (duration / 300.0))  # 5 minutes max

            # Check for plan file to assess complexity
            plan_file = latest_run / "plan.json"
            if plan_file.exists():
                with open(plan_file, 'r') as f:
                    plan_data = json.load(f)

                    # Count plan steps as complexity indicator
                    steps = plan_data.get('steps', [])
                    metrics['plan_complexity'] = min(1.0, len(steps) / 10.0)

                    # Check for specific plan types
                    plan_descriptions = [step.get('description', '').lower() for step in steps]
                    if any('harmony' in desc for desc in plan_descriptions):
                        metrics['plan_harmony_focus'] = 1.0
                    if any('test' in desc for desc in plan_descriptions):
                        metrics['plan_testing_focus'] = 1.0

        except Exception as e:
            self.logger.debug(f"Error getting agent run metrics: {e}")

        return metrics

    def _calculate_enhanced_metrics(self, agent_id: str, basic_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate enhanced derived metrics"""
        enhanced_metrics = {}

        try:
            # Calculate efficiency composite
            efficiency_factors = []
            for metric in ['tes', 'stability', 'velocity', 'execution_efficiency']:
                if metric in basic_metrics:
                    efficiency_factors.append(basic_metrics[metric])

            if efficiency_factors:
                enhanced_metrics['efficiency'] = sum(efficiency_factors) / len(efficiency_factors)

            # Calculate stability trend
            if agent_id in self.agent_metrics_history and len(self.agent_metrics_history[agent_id]) >= 3:
                recent_metrics = self.agent_metrics_history[agent_id][-3:]
                stability_values = [m.get('stability', 0) for m in recent_metrics if 'metrics' in m]

                if len(stability_values) >= 2:
                    # Calculate stability trend
                    stability_trend = stability_values[-1] - stability_values[0]
                    enhanced_metrics['stability_trend'] = max(-1.0, min(1.0, stability_trend))

            # Calculate activity score
            activity_factors = []
            for metric in ['agent_status', 'phase_efficiency', 'goal_complexity']:
                if metric in basic_metrics:
                    activity_factors.append(basic_metrics[metric])

            if activity_factors:
                enhanced_metrics['activity_score'] = sum(activity_factors) / len(activity_factors)

            # Calculate resource efficiency (if resource data available)
            if 'process_cpu' in basic_metrics and 'process_memory' in basic_metrics:
                cpu_usage = basic_metrics['process_cpu']
                memory_usage = basic_metrics['process_memory']

                # Resource efficiency: lower usage for same output is better
                resource_efficiency = 1.0 - ((cpu_usage + memory_usage) / 200.0)  # Normalize to 0-1
                enhanced_metrics['resource_efficiency'] = max(0, resource_efficiency)

        except Exception as e:
            self.logger.debug(f"Error calculating enhanced metrics: {e}")

        return enhanced_metrics

    def collect_system_performance_metrics(self) -> Dict[str, float]:
        """Collect comprehensive system performance metrics"""
        metrics = {}

        try:
            # Basic system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics.update({
                'system_cpu_percent': cpu_percent,
                'system_memory_percent': memory.percent,
                'system_memory_available': memory.available / (1024**3),  # GB
                'system_disk_percent': disk.percent,
                'system_disk_free': disk.free / (1024**3),  # GB
            })

            # Network I/O (if available)
            try:
                network = psutil.net_io_counters()
                if network:
                    metrics['network_bytes_sent'] = network.bytes_sent
                    metrics['network_bytes_recv'] = network.bytes_recv
            except Exception:
                pass

            # Process counts
            metrics['total_processes'] = len(psutil.pids())

            # Teaching system specific metrics
            teaching_processes = 0
            teaching_cpu = 0
            teaching_memory = 0

            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if any(keyword in proc.info['name'].lower() for keyword in ['python', 'ai4all', 'teaching']):
                        teaching_processes += 1
                        teaching_cpu += proc.info.get('cpu_percent', 0)
                        teaching_memory += proc.info.get('memory_percent', 0)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            metrics.update({
                'teaching_processes': teaching_processes,
                'teaching_cpu_usage': teaching_cpu,
                'teaching_memory_usage': teaching_memory,
                'teaching_system_overhead': (teaching_cpu + teaching_memory) / 100.0  # Percentage of total resources
            })

            # Calculate system health score
            health_factors = []
            if cpu_percent < 80: health_factors.append(1.0)
            elif cpu_percent < 90: health_factors.append(0.7)
            else: health_factors.append(0.3)

            if memory.percent < 80: health_factors.append(1.0)
            elif memory.percent < 90: health_factors.append(0.7)
            else: health_factors.append(0.3)

            if disk.percent < 80: health_factors.append(1.0)
            elif disk.percent < 90: health_factors.append(0.7)
            else: health_factors.append(0.3)

            metrics['system_health_score'] = sum(health_factors) / len(health_factors) if health_factors else 0.5

            # Store in history
            self.system_metrics_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics.copy()
            })

            # Keep only recent history
            if len(self.system_metrics_history) > self.metric_history_size:
                self.system_metrics_history = self.system_metrics_history[-self.metric_history_size:]

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {}

    def analyze_performance_patterns(self) -> Dict[str, Any]:
        """Analyze performance patterns across all agents"""
        patterns = {
            'agent_patterns': {},
            'system_patterns': {},
            'cross_agent_patterns': {},
            'recommendations': []
        }

        try:
            # Analyze each agent's performance trends
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                if agent_id in self.agent_metrics_history and len(self.agent_metrics_history[agent_id]) >= 5:
                    agent_patterns = self._analyze_agent_patterns(agent_id)
                    patterns['agent_patterns'][agent_id] = agent_patterns

            # Analyze system-level patterns
            if len(self.system_metrics_history) >= 10:
                system_patterns = self._analyze_system_patterns()
                patterns['system_patterns'] = system_patterns

            # Find cross-agent patterns
            cross_patterns = self._find_cross_agent_patterns()
            patterns['cross_agent_patterns'] = cross_patterns

            # Generate recommendations
            patterns['recommendations'] = self._generate_pattern_recommendations(patterns)

        except Exception as e:
            self.logger.error(f"Error analyzing performance patterns: {e}")

        return patterns

    def _analyze_agent_patterns(self, agent_id: str) -> Dict[str, Any]:
        """Analyze performance patterns for a specific agent"""
        history = self.agent_metrics_history[agent_id]
        if len(history) < 5:
            return {'error': 'Insufficient data'}

        # Extract metric trends
        metric_trends = {}
        for metric in ['tes', 'stability', 'velocity', 'efficiency']:
            values = [entry['metrics'].get(metric, 0) for entry in history[-10:] if metric in entry['metrics']]
            if len(values) >= 3:
                # Simple trend analysis
                if len(values) >= 5:
                    recent_avg = sum(values[-3:]) / 3
                    older_avg = sum(values[:2]) / 2
                    trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
                else:
                    trend = 0

                metric_trends[metric] = {
                    'current_value': values[-1],
                    'trend': trend,
                    'trend_direction': 'improving' if trend > 0.05 else 'declining' if trend < -0.05 else 'stable',
                    'data_points': len(values)
                }

        # Analyze activity patterns
        activity_values = [entry['metrics'].get('activity_score', 0) for entry in history[-10:]]
        if activity_values:
            avg_activity = sum(activity_values) / len(activity_values)
            activity_trend = activity_values[-1] - activity_values[0] if len(activity_values) >= 2 else 0

            return {
                'metric_trends': metric_trends,
                'activity_analysis': {
                    'average_activity': avg_activity,
                    'activity_trend': activity_trend,
                    'activity_direction': 'increasing' if activity_trend > 0.1 else 'decreasing' if activity_trend < -0.1 else 'stable'
                },
                'sample_size': len(history),
                'analysis_timestamp': datetime.now().isoformat()
            }

        return {'error': 'No activity data available'}

    def _analyze_system_patterns(self) -> Dict[str, Any]:
        """Analyze system-level performance patterns"""
        if len(self.system_metrics_history) < 10:
            return {'error': 'Insufficient system data'}

        # Analyze resource usage patterns
        resource_metrics = ['system_cpu_percent', 'system_memory_percent', 'system_disk_percent']

        resource_analysis = {}
        for metric in resource_metrics:
            values = [entry['metrics'].get(metric, 0) for entry in self.system_metrics_history[-20:]]
            if values:
                resource_analysis[metric] = {
                    'current_value': values[-1],
                    'average_value': sum(values) / len(values),
                    'max_value': max(values),
                    'min_value': min(values),
                    'trend': self._calculate_trend(values)
                }

        # Analyze teaching system overhead
        overhead_values = [entry['metrics'].get('teaching_system_overhead', 0) for entry in self.system_metrics_history[-20:]]
        if overhead_values:
            overhead_analysis = {
                'current_overhead': overhead_values[-1],
                'average_overhead': sum(overhead_values) / len(overhead_values),
                'max_overhead': max(overhead_values),
                'overhead_trend': self._calculate_trend(overhead_values)
            }
        else:
            overhead_analysis = {'error': 'No overhead data'}

        return {
            'resource_analysis': resource_analysis,
            'overhead_analysis': overhead_analysis,
            'system_health_trend': resource_analysis.get('system_health_score', {}).get('trend', 0) if 'system_health_score' in resource_analysis else 0
        }

    def _find_cross_agent_patterns(self) -> Dict[str, Any]:
        """Find patterns that occur across multiple agents"""
        cross_patterns = {}

        try:
            # Compare performance trends across agents
            agent_trends = {}
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                if agent_id in self.agent_metrics_history and len(self.agent_metrics_history[agent_id]) >= 5:
                    patterns = self._analyze_agent_patterns(agent_id)
                    if 'metric_trends' in patterns:
                        agent_trends[agent_id] = patterns['metric_trends']

            if len(agent_trends) >= 2:
                # Find common trends
                common_trends = {}
                for metric in ['tes', 'stability', 'efficiency']:
                    directions = [trends.get(metric, {}).get('trend_direction', 'unknown')
                                for trends in agent_trends.values() if metric in trends]

                    if len(set(directions)) == 1 and directions[0] != 'unknown':  # All agents showing same trend
                        common_trends[metric] = {
                            'direction': directions[0],
                            'agents_affected': list(agent_trends.keys()),
                            'significance': 'high' if len(directions) >= 3 else 'medium'
                        }

                cross_patterns['common_performance_trends'] = common_trends

                # Find correlation patterns
                correlations = self._find_metric_correlations(agent_trends)
                cross_patterns['metric_correlations'] = correlations

        except Exception as e:
            self.logger.debug(f"Error finding cross-agent patterns: {e}")

        return cross_patterns

    def _find_metric_correlations(self, agent_trends: Dict[str, Dict]) -> Dict[str, Any]:
        """Find correlations between metrics across agents"""
        correlations = {}

        try:
            # Check if certain metrics tend to move together
            for agent_id, trends in agent_trends.items():
                for metric1 in trends:
                    for metric2 in trends:
                        if metric1 != metric2:
                            trend1 = trends[metric1].get('trend', 0)
                            trend2 = trends[metric2].get('trend', 0)

                            # Calculate correlation (simple approach)
                            if abs(trend1) > 0.01 and abs(trend2) > 0.01:
                                correlation = trend1 * trend2  # Positive if both trends same direction
                                if abs(correlation) > 0.5:  # Significant correlation
                                    key = f"{metric1}_{metric2}"
                                    if key not in correlations:
                                        correlations[key] = {
                                            'correlation_strength': abs(correlation),
                                            'trend_directions': [trend1 > 0, trend2 > 0],
                                            'agents_showing_pattern': [agent_id]
                                        }
                                    else:
                                        correlations[key]['agents_showing_pattern'].append(agent_id)

        except Exception as e:
            self.logger.debug(f"Error finding metric correlations: {e}")

        return correlations

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend from a list of values"""
        if len(values) < 2:
            return 0

        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        y = values

        # Calculate slope
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator = sum((xi - mean_x) ** 2 for xi in x)

        return numerator / denominator if denominator != 0 else 0

    def _generate_pattern_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on pattern analysis"""
        recommendations = []

        try:
            # System-level recommendations
            system_patterns = patterns.get('system_patterns', {})
            if 'resource_analysis' in system_patterns:
                resource_analysis = system_patterns['resource_analysis']

                # Check for resource issues
                for metric, analysis in resource_analysis.items():
                    if 'system_cpu_percent' in metric and analysis.get('current_value', 0) > 80:
                        recommendations.append("High CPU usage detected - consider optimizing teaching frequency")
                    if 'system_memory_percent' in metric and analysis.get('current_value', 0) > 80:
                        recommendations.append("High memory usage detected - monitor teaching system resource consumption")

            # Cross-agent recommendations
            cross_patterns = patterns.get('cross_agent_patterns', {})
            if 'common_performance_trends' in cross_patterns:
                common_trends = cross_patterns['common_performance_trends']

                for metric, trend_info in common_trends.items():
                    if trend_info['direction'] == 'declining' and trend_info['significance'] == 'high':
                        recommendations.append(f"System-wide {metric} decline detected across multiple agents - investigate external factors")
                    elif trend_info['direction'] == 'improving' and trend_info['significance'] == 'high':
                        recommendations.append(f"System-wide {metric} improvement detected - reinforce successful patterns")

        except Exception as e:
            self.logger.debug(f"Error generating pattern recommendations: {e}")

        return recommendations[:5]  # Return top 5 recommendations

    def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'collection_summary': {
                'agents_monitored': len(self.agent_metrics_history),
                'total_samples': sum(len(history) for history in self.agent_metrics_history.values()),
                'system_samples': len(self.system_metrics_history),
                'collection_period': (datetime.now() - datetime.fromisoformat(self.resource_baselines.get('timestamp', datetime.now().isoformat()))).total_seconds() if self.resource_baselines else 0
            },
            'agent_performance': {},
            'system_performance': self.collect_system_performance_metrics(),
            'patterns_analysis': self.analyze_performance_patterns(),
            'recommendations': []
        }

        # Get performance for each agent
        for agent_id in self.agent_metrics_history:
            if self.agent_metrics_history[agent_id]:
                latest_metrics = self.agent_metrics_history[agent_id][-1]['metrics']
                agent_patterns = self._analyze_agent_patterns(agent_id)

                report['agent_performance'][agent_id] = {
                    'latest_metrics': latest_metrics,
                    'pattern_analysis': agent_patterns,
                    'sample_count': len(self.agent_metrics_history[agent_id])
                }

        # Generate recommendations
        all_recommendations = []
        for agent_data in report['agent_performance'].values():
            patterns = agent_data.get('pattern_analysis', {})
            if 'recommendations' in patterns:
                all_recommendations.extend(patterns['recommendations'])

        # Add system recommendations
        system_patterns = report['patterns_analysis'].get('system_patterns', {})
        if 'recommendations' in report['patterns_analysis']:
            all_recommendations.extend(report['patterns_analysis']['recommendations'])

        report['recommendations'] = list(set(all_recommendations))[:10]  # Unique top 10

        return report

    def export_performance_data(self, output_path: str = None) -> str:
        """Export comprehensive performance data"""
        if not output_path:
            timestamp = int(time.time())
            output_path = f"outgoing/ai4all/monitoring/enhanced_performance_{timestamp}.json"

        try:
            export_data = self.get_comprehensive_performance_report()

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Enhanced performance data exported to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting performance data: {e}")
            return ""


def create_enhanced_collector(config: Dict[str, Any] = None) -> EnhancedPerformanceCollector:
    """Create enhanced performance collector"""
    if config is None:
        config = {
            'collection_interval': 30,
            'metric_history_size': 1000,
            'enable_resource_monitoring': True,
            'enable_agent_analysis': True
        }

    return EnhancedPerformanceCollector(config)
