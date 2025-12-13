#!/usr/bin/env python3
"""
Production Monitor - Comprehensive monitoring and alerting for AI-for-All teaching system
"""

import argparse
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

import sys
import os

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

from teaching.framework import TeachingFramework
from teaching.agent_interface import AgentTeachingInterface


class ProductionMonitor:
    """
    Production monitoring and alerting system for AI-for-All teaching system.
    Provides comprehensive monitoring, alerting, and reporting capabilities.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize production monitor.

        Args:
            config: Monitoring configuration
        """
        self.config = config
        self.logger = logging.getLogger("ai4all.monitor")

        # Initialize teaching system components
        self.framework = TeachingFramework("config/teaching_config.json")
        self.agent_interface = AgentTeachingInterface(self.framework)

        # Monitoring state
        self.running = False
        self.monitoring_thread = None
        self.alerting_thread = None

        # Alert thresholds
        self.alert_thresholds = {
            'performance_decline': config.get('performance_decline_threshold', -0.1),
            'adaptation_failure_rate': config.get('adaptation_failure_threshold', 0.5),
            'system_stability': config.get('stability_threshold', 0.7),
            'resource_usage': config.get('resource_threshold', 0.8),
            'knowledge_retention': config.get('knowledge_threshold', 0.6)
        }

        # Alert history
        self.alerts: List[Dict[str, Any]] = []
        self.metrics_history: List[Dict[str, Any]] = []

        # Setup monitoring
        self._setup_monitoring()

        self.logger.info("Production monitor initialized")

    def _setup_monitoring(self):
        """Setup monitoring components"""
        # Create monitoring directories
        monitoring_dir = Path("outgoing/ai4all/monitoring")
        monitoring_dir.mkdir(parents=True, exist_ok=True)

        # Setup monitoring logging
        monitor_log = monitoring_dir / "monitor.log"
        handler = logging.FileHandler(monitor_log)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_monitoring(self):
        """Start production monitoring"""
        if self.running:
            self.logger.warning("Monitoring already running")
            return

        self.running = True
        self.logger.info("Starting production monitoring")

        # Start monitoring threads
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

        self.alerting_thread = threading.Thread(
            target=self._alerting_loop,
            daemon=True
        )
        self.alerting_thread.start()

        self.logger.info("Production monitoring started")

    def stop_monitoring(self):
        """Stop production monitoring"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping production monitoring")

        # Generate final report
        self._generate_final_report()

        # Wait for threads to finish
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        if self.alerting_thread and self.alerting_thread.is_alive():
            self.alerting_thread.join(timeout=5)

        self.logger.info("Production monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        self.logger.info("Monitoring loop started")

        while self.running:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Check agent health
                self._check_agent_health()

                # Analyze performance trends
                self._analyze_performance_trends()

                # Check resource usage
                self._check_resource_usage()

                # Sleep for monitoring interval
                time.sleep(self.config.get('monitoring_interval', 60))

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)

    def _alerting_loop(self):
        """Alert monitoring loop"""
        self.logger.info("Alerting loop started")

        while self.running:
            try:
                # Check for alerts
                self._check_alert_conditions()

                # Process existing alerts
                self._process_alerts()

                # Sleep for alerting interval
                time.sleep(self.config.get('alerting_interval', 30))

            except Exception as e:
                self.logger.error(f"Error in alerting loop: {e}")
                time.sleep(30)

    def _collect_system_metrics(self):
        """Collect comprehensive system metrics"""
        try:
            timestamp = datetime.now()

            # Get system overview
            system_overview = self.agent_interface.get_system_overview()
            framework_status = self.framework.get_system_status()

            # Collect detailed metrics
            metrics = {
                'timestamp': timestamp.isoformat(),
                'system_overview': system_overview,
                'framework_status': framework_status,
                'agent_details': {},
                'performance_summary': {},
                'alert_status': {
                    'active_alerts': len([a for a in self.alerts if a['status'] == 'active']),
                    'alerts_last_hour': len([a for a in self.alerts if (datetime.now() - a['timestamp']).total_seconds() < 3600])
                }
            }

            # Get detailed metrics for each agent
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                try:
                    agent_status = self.agent_interface.get_agent_teaching_status(agent_id)
                    metrics['agent_details'][agent_id] = agent_status

                    # Calculate performance summary for this agent
                    if 'progress_summary' in agent_status:
                        metrics['performance_summary'][agent_id] = agent_status['progress_summary']
                except Exception as e:
                    self.logger.debug(f"Error collecting metrics for {agent_id}: {e}")

            # Store metrics
            self.metrics_history.append(metrics)

            # Keep only recent history
            max_history = self.config.get('metrics_history_size', 1000)
            if len(self.metrics_history) > max_history:
                self.metrics_history = self.metrics_history[-max_history:]

            # Save metrics periodically
            if len(self.metrics_history) % 10 == 0:  # Every 10 cycles
                self._save_metrics()

        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

    def _save_metrics(self):
        """Save metrics to persistent storage"""
        try:
            monitoring_dir = Path("outgoing/ai4all/monitoring")
            monitoring_dir.mkdir(parents=True, exist_ok=True)

            # Save recent metrics
            recent_metrics = self.metrics_history[-100:]  # Last 100 entries

            with open(monitoring_dir / "recent_metrics.json", 'w') as f:
                json.dump(recent_metrics, f, indent=2, default=str)

            self.logger.debug(f"Saved {len(recent_metrics)} metric entries")

        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")

    def _check_agent_health(self):
        """Check health of individual agents"""
        try:
            # Check each agent's teaching status
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                try:
                    status = self.agent_interface.get_agent_teaching_status(agent_id)

                    # Check for issues
                    if not status.get('teaching_enabled', False):
                        self._create_alert(
                            'agent_teaching_disabled',
                            f"Teaching disabled for {agent_id}",
                            'warning',
                            {'agent_id': agent_id}
                        )

                    # Check progress
                    progress = status.get('progress_summary', {}).get('average_progress', 0)
                    if progress < 0:
                        self._create_alert(
                            'negative_progress',
                            f"Negative progress detected for {agent_id}: {progress:.3f}",
                            'warning',
                            {'agent_id': agent_id, 'progress': progress}
                        )

                    # Check adaptation effectiveness
                    adaptations = status.get('adaptations', [])
                    if adaptations:
                        success_rate = len([a for a in adaptations if a.get('success', False)]) / len(adaptations)
                        if success_rate < 0.3:
                            self._create_alert(
                                'low_adaptation_success',
                                f"Low adaptation success rate for {agent_id}: {success_rate:.1%}",
                                'warning',
                                {'agent_id': agent_id, 'success_rate': success_rate}
                            )

                except Exception as e:
                    self.logger.debug(f"Error checking health for {agent_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error in agent health check: {e}")

    def _analyze_performance_trends(self):
        """Analyze performance trends across agents"""
        try:
            if len(self.metrics_history) < 5:
                return  # Need at least 5 data points for trend analysis

            recent_metrics = self.metrics_history[-5:]
            older_metrics = self.metrics_history[-10:-5] if len(self.metrics_history) >= 10 else recent_metrics

            # Analyze trends for each agent
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                recent_progress = []
                older_progress = []

                # Extract progress data
                for metrics in recent_metrics:
                    if (agent_id in metrics.get('performance_summary', {}) and
                        'average_progress' in metrics['performance_summary'][agent_id]):
                        recent_progress.append(metrics['performance_summary'][agent_id]['average_progress'])

                for metrics in older_metrics:
                    if (agent_id in metrics.get('performance_summary', {}) and
                        'average_progress' in metrics['performance_summary'][agent_id]):
                        older_progress.append(metrics['performance_summary'][agent_id]['average_progress'])

                # Calculate trend
                if recent_progress and older_progress:
                    recent_avg = sum(recent_progress) / len(recent_progress)
                    older_avg = sum(older_progress) / len(older_progress)

                    trend = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

                    # Alert on significant trends
                    if trend < self.alert_thresholds['performance_decline']:
                        self._create_alert(
                            'performance_decline',
                            f"Performance declining for {agent_id}: {trend:.1%} trend",
                            'warning',
                            {'agent_id': agent_id, 'trend': trend}
                        )
                    elif trend > 0.1:  # Significant improvement
                        self._create_alert(
                            'performance_improvement',
                            f"Significant performance improvement for {agent_id}: {trend:.1%} trend",
                            'info',
                            {'agent_id': agent_id, 'trend': trend}
                        )

        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")

    def _check_resource_usage(self):
        """Check system resource usage"""
        try:
            import psutil

            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.alert_thresholds['resource_usage'] * 100:
                self._create_alert(
                    'high_cpu_usage',
                    f"High CPU usage detected: {cpu_percent:.1f}%",
                    'warning',
                    {'cpu_percent': cpu_percent}
                )

            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            if memory_percent > self.alert_thresholds['resource_usage'] * 100:
                self._create_alert(
                    'high_memory_usage',
                    f"High memory usage detected: {memory_percent:.1f}%",
                    'warning',
                    {'memory_percent': memory_percent}
                )

            # Check disk usage for teaching system directories
            disk_usage = psutil.disk_usage('/')
            disk_percent = disk_usage.percent
            if disk_percent > self.alert_thresholds['resource_usage'] * 100:
                self._create_alert(
                    'high_disk_usage',
                    f"High disk usage detected: {disk_percent:.1f}%",
                    'warning',
                    {'disk_percent': disk_percent}
                )

        except ImportError:
            self.logger.debug("psutil not available for resource monitoring")
        except Exception as e:
            self.logger.error(f"Error checking resource usage: {e}")

    def _check_alert_conditions(self):
        """Check for alert conditions"""
        try:
            # Check system stability
            system_overview = self.agent_interface.get_system_overview()
            stability_score = self._calculate_system_stability(system_overview)

            if stability_score < self.alert_thresholds['system_stability']:
                self._create_alert(
                    'low_system_stability',
                    f"Low system stability detected: {stability_score:.3f}",
                    'warning',
                    {'stability_score': stability_score}
                )

            # Check knowledge retention
            framework_status = self.framework.get_system_status()
            knowledge_maturity = self._calculate_knowledge_maturity()

            if knowledge_maturity < self.alert_thresholds['knowledge_retention']:
                self._create_alert(
                    'low_knowledge_retention',
                    f"Low knowledge retention detected: {knowledge_maturity:.3f}",
                    'info',
                    {'knowledge_maturity': knowledge_maturity}
                )

        except Exception as e:
            self.logger.error(f"Error checking alert conditions: {e}")

    def _calculate_system_stability(self, system_overview: Dict[str, Any]) -> float:
        """Calculate overall system stability score"""
        try:
            # Weighted stability calculation
            agents_enabled = system_overview['agent_interface']['agents_with_teaching_enabled']
            total_agents = system_overview['agent_interface']['agents_configured']
            active_sessions = system_overview['agent_interface']['active_sessions']

            # Stability factors
            agent_coverage = agents_enabled / max(1, total_agents)
            session_stability = min(1.0, active_sessions / 8.0)  # 8 is optimal number of sessions

            # Check for recent errors or issues
            recent_alerts = len([a for a in self.alerts
                               if (datetime.now() - a['timestamp']).total_seconds() < 3600
                               and a['severity'] in ['error', 'warning']])

            error_penalty = min(0.3, recent_alerts * 0.05)  # Max 30% penalty

            stability = (agent_coverage * 0.4 + session_stability * 0.4 + (1 - error_penalty) * 0.2)

            return max(0.0, min(1.0, stability))

        except Exception as e:
            self.logger.debug(f"Error calculating system stability: {e}")
            return 0.5  # Default neutral stability

    def _calculate_knowledge_maturity(self) -> float:
        """Calculate overall knowledge maturity"""
        try:
            # Get knowledge status from all agents
            total_maturity = 0.0
            agent_count = 0

            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                try:
                    knowledge_status = self.agent_interface.framework.knowledge_integrator.get_integration_status(agent_id)
                    maturity = knowledge_status.get('knowledge_maturity', 0.0)
                    total_maturity += maturity
                    agent_count += 1
                except Exception as e:
                    self.logger.debug(f"Error getting knowledge status for {agent_id}: {e}")

            return total_maturity / agent_count if agent_count > 0 else 0.0

        except Exception as e:
            self.logger.debug(f"Error calculating knowledge maturity: {e}")
            return 0.0

    def _create_alert(self, alert_type: str, message: str, severity: str, details: Dict[str, Any]):
        """Create a new alert with deduplication"""
        # Check if a similar alert was created recently (within last 10 minutes)
        now = datetime.now()
        recent_threshold = 600  # 10 minutes
        
        for existing_alert in reversed(self.alerts[-50:]):  # Check last 50 alerts
            if (existing_alert['type'] == alert_type and 
                existing_alert['status'] == 'active' and
                (now - existing_alert['timestamp']).total_seconds() < recent_threshold):
                # Similar alert already exists, don't create duplicate
                return
        
        alert = {
            'id': f"alert_{int(time.time())}_{alert_type}",
            'type': alert_type,
            'message': message,
            'severity': severity,  # 'info', 'warning', 'error', 'critical'
            'timestamp': datetime.now(),
            'details': details,
            'status': 'active',
            'acknowledged': False
        }

        self.alerts.append(alert)

        # Log alert
        log_level = {'info': logging.INFO, 'warning': logging.WARNING,
                    'error': logging.ERROR, 'critical': logging.CRITICAL}[severity]
        self.logger.log(log_level, f"ALERT [{alert_type}] {message}")

        # Save alert to file
        self._save_alerts()

    def _save_alerts(self):
        """Save alerts to persistent storage"""
        try:
            monitoring_dir = Path("outgoing/ai4all/monitoring")
            monitoring_dir.mkdir(parents=True, exist_ok=True)

            # Keep only recent alerts (last 1000)
            recent_alerts = self.alerts[-1000:]

            with open(monitoring_dir / "alerts.json", 'w') as f:
                json.dump(recent_alerts, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving alerts: {e}")

    def _process_alerts(self):
        """Process and update alert status"""
        try:
            current_time = datetime.now()

            # Update alert status based on time and conditions
            for alert in self.alerts:
                if alert['status'] == 'active':
                    # Auto-resolve alerts after 1 hour if no new similar alerts
                    alert_age = (current_time - alert['timestamp']).total_seconds()

                    if alert_age > 3600:  # 1 hour
                        alert['status'] = 'resolved'
                        alert['resolved_at'] = current_time
                        self.logger.info(f"Auto-resolved alert: {alert['type']}")

                    # Escalate warning alerts to error if they persist
                    elif (alert['severity'] == 'warning' and alert_age > 1800):  # 30 minutes
                        alert['severity'] = 'error'
                        alert['escalated_at'] = current_time
                        self.logger.warning(f"Escalated alert to error: {alert['type']}")

        except Exception as e:
            self.logger.error(f"Error processing alerts: {e}")

    def _generate_final_report(self):
        """Generate final monitoring report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Compile comprehensive report
            report = {
                'timestamp': datetime.now().isoformat(),
                'report_type': 'final',
                'monitoring_summary': {
                    'total_alerts': len(self.alerts),
                    'active_alerts': len([a for a in self.alerts if a['status'] == 'active']),
                    'metrics_collected': len(self.metrics_history),
                    'monitoring_duration_hours': (datetime.now() - self.metrics_history[0]['timestamp']).total_seconds() / 3600 if self.metrics_history else 0
                },
                'system_performance': self._calculate_system_performance_summary(),
                'agent_performance': self._calculate_agent_performance_summary(),
                'alert_summary': self._summarize_alerts(),
                'recommendations': self._generate_monitoring_recommendations()
            }

            # Save final report
            monitoring_dir = Path("outgoing/ai4all/monitoring")
            monitoring_dir.mkdir(parents=True, exist_ok=True)

            report_file = monitoring_dir / f"final_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated final monitoring report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")

    def _calculate_system_performance_summary(self) -> Dict[str, Any]:
        """Calculate system performance summary"""
        try:
            if not self.metrics_history:
                return {'error': 'No metrics data available'}

            # Calculate averages over monitoring period
            total_agents = []
            total_sessions = []
            total_progress = []

            for metrics in self.metrics_history:
                system = metrics.get('system_overview', {})
                total_agents.append(system.get('agent_interface', {}).get('agents_with_teaching_enabled', 0))
                total_sessions.append(system.get('agent_interface', {}).get('active_sessions', 0))

                # Average progress across all agents
                for agent_progress in metrics.get('performance_summary', {}).values():
                    if isinstance(agent_progress, dict) and 'average_progress' in agent_progress:
                        total_progress.append(agent_progress['average_progress'])

            return {
                'avg_agents_enabled': sum(total_agents) / len(total_agents) if total_agents else 0,
                'avg_active_sessions': sum(total_sessions) / len(total_sessions) if total_sessions else 0,
                'avg_learning_progress': sum(total_progress) / len(total_progress) if total_progress else 0,
                'max_learning_progress': max(total_progress) if total_progress else 0,
                'min_learning_progress': min(total_progress) if total_progress else 0,
                'monitoring_samples': len(self.metrics_history)
            }

        except Exception as e:
            self.logger.error(f"Error calculating system performance summary: {e}")
            return {'error': str(e)}

    def _calculate_agent_performance_summary(self) -> Dict[str, Any]:
        """Calculate agent performance summary"""
        agent_summary = {}

        for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
            try:
                status = self.agent_interface.get_agent_teaching_status(agent_id)
                agent_summary[agent_id] = {
                    'teaching_enabled': status.get('teaching_enabled', False),
                    'active_sessions': len(status.get('active_sessions', [])),
                    'average_progress': status.get('progress_summary', {}).get('average_progress', 0),
                    'total_adaptations': len(status.get('adaptations', [])),
                    'knowledge_patterns': status.get('knowledge_patterns', [])
                }
            except Exception as e:
                agent_summary[agent_id] = {'error': str(e)}

        return agent_summary

    def _summarize_alerts(self) -> Dict[str, Any]:
        """Summarize alert history"""
        if not self.alerts:
            return {'total_alerts': 0, 'alert_types': [], 'severity_distribution': {}}

        # Count by type and severity
        alert_types = {}
        severity_counts = {'info': 0, 'warning': 0, 'error': 0, 'critical': 0}

        for alert in self.alerts:
            alert_type = alert['type']
            severity = alert['severity']

            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            'total_alerts': len(self.alerts),
            'active_alerts': len([a for a in self.alerts if a['status'] == 'active']),
            'alert_types': dict(sorted(alert_types.items(), key=lambda x: x[1], reverse=True)),
            'severity_distribution': severity_counts,
            'most_common_alert': max(alert_types.items(), key=lambda x: x[1]) if alert_types else None
        }

    def _generate_monitoring_recommendations(self) -> List[str]:
        """Generate monitoring-based recommendations"""
        recommendations = []

        # Analyze alert patterns
        alert_summary = self._summarize_alerts()

        if alert_summary['active_alerts'] > 0:
            recommendations.append(f"Address {alert_summary['active_alerts']} active alerts before production deployment")

        if alert_summary['severity_distribution'].get('error', 0) > 0:
            recommendations.append("Resolve error-level alerts before continuing")

        # Analyze performance
        system_perf = self._calculate_system_performance_summary()

        if system_perf.get('avg_learning_progress', 0) < 0.1:
            recommendations.append("Review learning objectives - progress below expected threshold")

        if system_perf.get('avg_agents_enabled', 0) < 3:
            recommendations.append("Enable teaching for more agents to improve system coverage")

        # Check for common issues
        if alert_summary.get('most_common_alert'):
            most_common = alert_summary['most_common_alert']
            if most_common[1] > 5:  # More than 5 occurrences
                recommendations.append(f"Investigate recurring {most_common[0]} alerts")

        return recommendations

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            'monitoring': {
                'running': self.running,
                'metrics_collected': len(self.metrics_history),
                'alerts_total': len(self.alerts),
                'alerts_active': len([a for a in self.alerts if a['status'] == 'active']),
                'last_update': datetime.now().isoformat()
            },
            'system_health': self._calculate_system_stability({}),
            'agent_health': self._calculate_agent_performance_summary(),
            'recent_alerts': [a for a in self.alerts[-10:] if a['status'] == 'active'],
            'performance_summary': self._calculate_system_performance_summary()
        }

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now()
                self.logger.info(f"Alert acknowledged: {alert_id}")
                return True

        return False

    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Resolve an alert"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['status'] = 'resolved'
                alert['resolved_at'] = datetime.now()
                alert['resolution_notes'] = resolution_notes
                self.logger.info(f"Alert resolved: {alert_id} - {resolution_notes}")
                return True

        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="AI-for-All Production Monitor")
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--alert-interval', type=int, default=30, help='Alert evaluation cadence in seconds')
    parser.add_argument('--performance-decline-threshold', type=float, default=-0.1,
                        help='Minimum acceptable performance delta before alert')
    parser.add_argument('--stability-threshold', type=float, default=0.7,
                        help='Minimum acceptable system stability score')
    parser.add_argument('--resource-threshold', type=float, default=0.8,
                        help='Resource usage threshold for alerts')
    parser.add_argument('--knowledge-threshold', type=float, default=0.6,
                        help='Knowledge retention threshold')
    args = parser.parse_args()

    config = {
        'monitoring_interval': args.interval,
        'alerting_interval': args.alert_interval,
        'performance_decline_threshold': args.performance_decline_threshold,
        'stability_threshold': args.stability_threshold,
        'resource_threshold': args.resource_threshold,
        'knowledge_threshold': args.knowledge_threshold,
    }

    monitor = ProductionMonitor(config)
    monitor.start_monitoring()

    try:
        sleep_interval = max(5, args.interval // 2)
        while True:
            time.sleep(sleep_interval)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
