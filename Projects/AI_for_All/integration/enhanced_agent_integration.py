#!/usr/bin/env python3
"""
Enhanced Agent Integration - Automatic performance data feeding for AI-for-All teaching system
"""

import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

# Import teaching system
import sys
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir))

from teaching.framework import TeachingFramework
from teaching.agent_interface import AgentTeachingInterface


class EnhancedAgentIntegration:
    """
    Enhanced integration that automatically extracts and feeds performance data
    from active Calyx Terminal agents to the AI-for-All teaching system.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize enhanced agent integration.

        Args:
            config: Integration configuration
        """
        self.config = config
        self.logger = logging.getLogger("ai4all.enhanced_integration")

        # Initialize teaching system
        self.framework = TeachingFramework("config/teaching_config.json")
        self.agent_interface = AgentTeachingInterface(self.framework)

        # Integration settings
        self.monitoring_interval = config.get('monitoring_interval', 30)
        self.performance_extraction_enabled = config.get('performance_extraction', True)
        self.auto_enable_agents = config.get('auto_enable_agents', True)

        # Agent tracking
        self.active_agents: Dict[str, Dict] = {}
        self.agent_baselines: Dict[str, Dict] = {}
        self.performance_cache: Dict[str, List] = {}

        # Integration state
        self.running = False
        self.integration_thread = None
        self.last_scan = None

        # Setup logging
        self._setup_integration_logging()

        self.logger.info("Enhanced agent integration initialized")

    def _setup_integration_logging(self):
        """Setup integration logging"""
        log_dir = Path("outgoing/ai4all/integration")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "enhanced_integration.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_integration(self):
        """Start enhanced agent integration"""
        if self.running:
            self.logger.warning("Integration already running")
            return

        self.running = True
        self.logger.info("Starting enhanced agent integration")

        # Auto-enable configured agents
        if self.auto_enable_agents:
            self._enable_configured_agents()

        # Start integration thread
        self.integration_thread = threading.Thread(
            target=self._integration_loop,
            daemon=True
        )
        self.integration_thread.start()

        self.logger.info("Enhanced agent integration started successfully")

    def stop_integration(self):
        """Stop enhanced agent integration"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping enhanced agent integration")

        # Wait for integration thread
        if self.integration_thread and self.integration_thread.is_alive():
            self.integration_thread.join(timeout=5)

        # Export final performance data
        self._export_final_data()

        self.logger.info("Enhanced agent integration stopped")

    def _enable_configured_agents(self):
        """Enable teaching for all agents configured in the system"""
        # Get agent configurations from main Calyx config
        try:
            with open("config.yaml", 'r') as f:
                import yaml
                calyx_config = yaml.safe_load(f)
                ai4all_config = calyx_config.get('settings', {}).get('ai4all_teaching', {}).get('agents', {})

                for agent_id, agent_config in ai4all_config.items():
                    if agent_config.get('enabled', False):
                        objectives = agent_config.get('learning_objectives', ['task_efficiency'])
                        baseline_metrics = agent_config.get('baseline_metrics', {})

                        success = self.agent_interface.enable_teaching(agent_id, objectives)
                        if success:
                            self.agent_baselines[agent_id] = baseline_metrics
                            self.logger.info(f"Auto-enabled teaching for {agent_id}: {objectives}")
                        else:
                            self.logger.warning(f"Failed to enable teaching for {agent_id}")

        except Exception as e:
            self.logger.error(f"Error enabling configured agents: {e}")

    def _integration_loop(self):
        """Main integration loop"""
        self.logger.info("Enhanced integration loop started")

        while self.running:
            try:
                # Scan for active agents
                self._scan_active_agents()

                # Extract and update performance data
                self._extract_and_update_performance()

                # Check for agent state changes
                self._check_agent_state_changes()

                # Update integration status
                self._update_integration_status()

                # Sleep for monitoring interval
                time.sleep(self.monitoring_interval)

            except Exception as e:
                self.logger.error(f"Error in integration loop: {e}")
                time.sleep(60)  # Wait longer on errors

    def _scan_active_agents(self):
        """Scan for active agents and update tracking"""
        try:
            heartbeat_dir = Path("outgoing")
            heartbeat_files = list(heartbeat_dir.glob("*.lock"))

            current_agents = set()
            for heartbeat_file in heartbeat_files:
                agent_id = heartbeat_file.stem

                # Track configured agents
                if agent_id in ['agent1', 'triage', 'cp6', 'cp7', 'cp8', 'cp9', 'cp10', 'cp12']:
                    current_agents.add(agent_id)

                    # Update agent tracking
                    if agent_id not in self.active_agents:
                        self.active_agents[agent_id] = {
                            'first_seen': datetime.now(),
                            'last_seen': datetime.now(),
                            'heartbeat_count': 0,
                            'status': 'unknown'
                        }
                    else:
                        self.active_agents[agent_id]['last_seen'] = datetime.now()
                        self.active_agents[agent_id]['heartbeat_count'] += 1

            # Mark agents as inactive if not seen recently
            current_time = datetime.now()
            for agent_id in list(self.active_agents.keys()):
                if agent_id not in current_agents:
                    # Check if agent has been inactive for more than 5 minutes
                    last_seen = self.active_agents[agent_id]['last_seen']
                    if (current_time - last_seen).total_seconds() > 300:
                        self.active_agents[agent_id]['status'] = 'inactive'
                        self.logger.debug(f"Agent {agent_id} marked as inactive")

            self.last_scan = current_time

        except Exception as e:
            self.logger.error(f"Error scanning active agents: {e}")

    def _extract_and_update_performance(self):
        """Extract performance data from agents and update teaching system"""
        if not self.performance_extraction_enabled:
            return

        for agent_id in self.active_agents:
            if self.active_agents[agent_id].get('status') != 'inactive':
                try:
                    # Extract performance metrics
                    metrics = self._extract_agent_performance_metrics(agent_id)

                    if metrics:
                        # Update teaching system
                        response = self.agent_interface.update_agent_performance(
                            agent_id=agent_id,
                            metrics=metrics,
                            context={
                                'source': 'enhanced_integration',
                                'agent_type': agent_id,
                                'extraction_method': 'heartbeat_analysis',
                                'timestamp': datetime.now().isoformat()
                            }
                        )

                        # Cache performance data
                        if agent_id not in self.performance_cache:
                            self.performance_cache[agent_id] = []

                        self.performance_cache[agent_id].append({
                            'timestamp': datetime.now(),
                            'metrics': metrics.copy(),
                            'teaching_response': response
                        })

                        # Keep only recent cache
                        if len(self.performance_cache[agent_id]) > 100:
                            self.performance_cache[agent_id] = self.performance_cache[agent_id][-100:]

                        if response.get('adaptations_applied'):
                            self.logger.debug(f"Applied adaptations for {agent_id}: {len(response['adaptations_applied'])} adaptations")

                except Exception as e:
                    self.logger.debug(f"Error extracting performance for {agent_id}: {e}")

    def _extract_agent_performance_metrics(self, agent_id: str) -> Optional[Dict[str, float]]:
        """Extract comprehensive performance metrics for an agent"""
        metrics = {}

        try:
            # Read agent heartbeat
            heartbeat_file = Path(f"outgoing/{agent_id}.lock")
            if not heartbeat_file.exists():
                return None

            with open(heartbeat_file, 'r') as f:
                heartbeat_data = json.load(f)

            # Extract basic metrics
            metrics['agent_uptime'] = self._calculate_agent_uptime(agent_id, heartbeat_data)
            metrics['status_efficiency'] = self._calculate_status_efficiency(heartbeat_data)
            metrics['activity_level'] = self._calculate_activity_level(agent_id, heartbeat_data)

            # Extract goal-based metrics
            goal_metrics = self._extract_goal_metrics(agent_id, heartbeat_data)
            metrics.update(goal_metrics)

            # Extract process metrics if PID available
            process_metrics = self._extract_process_metrics(heartbeat_data)
            metrics.update(process_metrics)

            # Calculate derived metrics
            derived_metrics = self._calculate_derived_metrics(agent_id, metrics)
            metrics.update(derived_metrics)

            # Store agent status
            self.active_agents[agent_id]['status'] = heartbeat_data.get('status', 'unknown')
            self.active_agents[agent_id]['current_phase'] = heartbeat_data.get('phase', 'unknown')

            return metrics if metrics else None

        except Exception as e:
            self.logger.debug(f"Error extracting performance metrics for {agent_id}: {e}")
            return None

    def _calculate_agent_uptime(self, agent_id: str, heartbeat_data: Dict) -> float:
        """Calculate agent uptime based on heartbeat data"""
        try:
            if 'ts' in heartbeat_data:
                current_time = time.time()
                last_activity = current_time - heartbeat_data['ts']
                # Convert to efficiency score (more recent activity = higher efficiency)
                return max(0, 1.0 - (last_activity / 3600.0))  # 1 hour window
            return 0.5
        except Exception:
            return 0.5

    def _calculate_status_efficiency(self, heartbeat_data: Dict) -> float:
        """Calculate efficiency based on agent status"""
        status_scores = {
            'running': 1.0,
            'executing': 1.0,
            'testing': 0.9,
            'planning': 0.8,
            'idle': 0.3,
            'completed': 1.0,
            'error': 0.1,
            'unknown': 0.5
        }

        status = heartbeat_data.get('status', 'unknown')
        return status_scores.get(status, 0.5)

    def _calculate_activity_level(self, agent_id: str, heartbeat_data: Dict) -> float:
        """Calculate activity level based on agent behavior"""
        activity_score = 0.0

        try:
            # Status-based activity
            status = heartbeat_data.get('status', 'unknown')
            if status == 'running':
                activity_score += 0.5
            elif status == 'executing':
                activity_score += 0.7
            elif status == 'testing':
                activity_score += 0.6

            # Phase-based activity
            phase = heartbeat_data.get('phase', 'unknown')
            phase_scores = {
                'planning': 0.3,
                'executing': 0.8,
                'testing': 0.7,
                'completed': 0.9
            }
            activity_score += phase_scores.get(phase, 0.2)

            # Goal complexity activity
            goal_preview = heartbeat_data.get('goal_preview', '')
            if goal_preview:
                complexity = min(0.3, len(goal_preview) / 200.0)  # Normalize goal length
                activity_score += complexity

            return min(1.0, activity_score)

        except Exception:
            return 0.5

    def _extract_goal_metrics(self, agent_id: str, heartbeat_data: Dict) -> Dict[str, float]:
        """Extract metrics based on goal analysis"""
        metrics = {}

        try:
            goal_preview = heartbeat_data.get('goal_preview', '')

            if goal_preview:
                # Goal type classification
                goal_lower = goal_preview.lower()

                if any(keyword in goal_lower for keyword in ['harmony', 'cadence', 'rhythm', 'social']):
                    metrics['harmony_focus'] = 1.0
                if any(keyword in goal_lower for keyword in ['test', 'validate', 'check', 'verify']):
                    metrics['validation_focus'] = 1.0
                if any(keyword in goal_lower for keyword in ['optimize', 'improve', 'enhance']):
                    metrics['optimization_focus'] = 1.0

                # Goal complexity
                complexity_indicators = [
                    'multiple' in goal_lower,
                    'complex' in goal_lower,
                    len(goal_preview) > 100,
                    goal_preview.count(' ') > 20
                ]

                metrics['goal_complexity'] = sum(complexity_indicators) / 4.0

                # Urgency indicators
                urgency_indicators = [
                    'urgent' in goal_lower,
                    'immediate' in goal_lower,
                    'critical' in goal_lower,
                    'emergency' in goal_lower
                ]

                if any(urgency_indicators):
                    metrics['urgency_level'] = 1.0

        except Exception as e:
            self.logger.debug(f"Error extracting goal metrics: {e}")

        return metrics

    def _extract_process_metrics(self, heartbeat_data: Dict) -> Dict[str, float]:
        """Extract metrics from process information"""
        metrics = {}

        try:
            if 'pid' in heartbeat_data:
                pid = heartbeat_data['pid']
                import psutil

                process = psutil.Process(pid)
                metrics['process_cpu'] = process.cpu_percent()
                metrics['process_memory'] = process.memory_percent()

                # Calculate process efficiency
                cpu_usage = process.cpu_percent()
                memory_usage = process.memory_percent()

                # Process efficiency: lower resource usage for active process is better
                if cpu_usage > 0 or memory_usage > 0:
                    metrics['process_efficiency'] = 1.0 - ((cpu_usage + memory_usage) / 200.0)
                else:
                    metrics['process_efficiency'] = 0.5  # Idle process

        except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.debug(f"Process metrics unavailable: {e}")
        except Exception as e:
            self.logger.debug(f"Error extracting process metrics: {e}")

        return metrics

    def _calculate_derived_metrics(self, agent_id: str, basic_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate derived performance metrics"""
        derived_metrics = {}

        try:
            # Overall agent efficiency
            efficiency_factors = []
            for metric in ['status_efficiency', 'activity_level', 'process_efficiency']:
                if metric in basic_metrics:
                    efficiency_factors.append(basic_metrics[metric])

            if efficiency_factors:
                derived_metrics['agent_efficiency'] = sum(efficiency_factors) / len(efficiency_factors)

            # Calculate agent health score
            health_factors = []
            for metric in ['agent_uptime', 'status_efficiency', 'process_efficiency']:
                if metric in basic_metrics:
                    health_factors.append(basic_metrics[metric])

            if health_factors:
                derived_metrics['agent_health'] = sum(health_factors) / len(health_factors)

            # Calculate productivity score
            productivity_factors = []
            for metric in ['activity_level', 'goal_complexity', 'process_efficiency']:
                if metric in basic_metrics:
                    productivity_factors.append(basic_metrics[metric])

            if productivity_factors:
                derived_metrics['productivity_score'] = sum(productivity_factors) / len(productivity_factors)

        except Exception as e:
            self.logger.debug(f"Error calculating derived metrics: {e}")

        return derived_metrics

    def _check_agent_state_changes(self):
        """Check for significant agent state changes"""
        try:
            for agent_id in self.active_agents:
                if agent_id in self.performance_cache and len(self.performance_cache[agent_id]) >= 3:
                    recent_metrics = self.performance_cache[agent_id][-3:]

                    # Check for significant changes
                    for metric in ['agent_efficiency', 'agent_health', 'activity_level']:
                        values = [m['metrics'].get(metric, 0) for m in recent_metrics]
                        if len(values) >= 2:
                            change = values[-1] - values[0]
                            if abs(change) > 0.2:  # 20% change
                                self.logger.info(f"Significant {metric} change for {agent_id}: {change:.3f}")

        except Exception as e:
            self.logger.debug(f"Error checking agent state changes: {e}")

    def _update_integration_status(self):
        """Update integration status and generate reports"""
        try:
            # Generate periodic integration report
            if self.last_scan and (datetime.now() - self.last_scan).total_seconds() > 3600:  # Every hour
                self._generate_integration_report()

        except Exception as e:
            self.logger.debug(f"Error updating integration status: {e}")

    def _generate_integration_report(self):
        """Generate integration status report"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'integration_status': {
                    'running': self.running,
                    'active_agents': len([a for a in self.active_agents.values() if a.get('status') != 'inactive']),
                    'agents_with_performance_data': len([a for a in self.performance_cache if self.performance_cache[a]]),
                    'total_performance_updates': sum(len(cache) for cache in self.performance_cache.values()),
                    'integration_uptime': (datetime.now() - self.active_agents[list(self.active_agents.keys())[0]]['first_seen']).total_seconds() if self.active_agents else 0
                },
                'agent_details': {},
                'performance_summary': {},
                'recommendations': []
            }

            # Add agent details
            for agent_id in self.active_agents:
                agent_info = self.active_agents[agent_id].copy()
                agent_info['performance_cache_size'] = len(self.performance_cache.get(agent_id, []))
                agent_info['baseline_metrics'] = self.agent_baselines.get(agent_id, {})

                if agent_id in self.performance_cache and self.performance_cache[agent_id]:
                    latest_metrics = self.performance_cache[agent_id][-1]['metrics']
                    agent_info['latest_metrics'] = latest_metrics

                report['agent_details'][agent_id] = agent_info

            # Generate recommendations
            recommendations = self._generate_integration_recommendations(report)
            report['recommendations'] = recommendations

            # Save report
            report_dir = Path("outgoing/ai4all/integration")
            report_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            report_file = report_dir / f"integration_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated integration report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating integration report: {e}")

    def _generate_integration_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate integration-based recommendations"""
        recommendations = []

        try:
            # Check agent coverage
            total_configured = len(self.agent_configs)
            active_with_data = len([a for a in report['agent_details'].values() if a.get('performance_cache_size', 0) > 0])

            if active_with_data < total_configured:
                missing_agents = [agent_id for agent_id, config in self.agent_configs.items()
                                if config.get('enabled', False) and report['agent_details'].get(agent_id, {}).get('performance_cache_size', 0) == 0]
                if missing_agents:
                    recommendations.append(f"Enable performance data collection for agents: {', '.join(missing_agents)}")

            # Check performance data quality
            for agent_id, details in report['agent_details'].items():
                cache_size = details.get('performance_cache_size', 0)
                if cache_size < 5:  # Less than 5 data points
                    recommendations.append(f"Insufficient performance data for {agent_id} - check integration")

            # Check for agents with poor performance
            for agent_id, details in report['agent_details'].items():
                latest_metrics = details.get('latest_metrics', {})
                if latest_metrics:
                    efficiency = latest_metrics.get('agent_efficiency', 0)
                    if efficiency < 0.3:
                        recommendations.append(f"Low efficiency detected for {agent_id} ({efficiency:.1%}) - investigate agent performance")

        except Exception as e:
            self.logger.debug(f"Error generating integration recommendations: {e}")

        return recommendations[:5]

    def _export_final_data(self):
        """Export final integration data"""
        try:
            # Export performance cache for all agents
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'integration_summary': {
                    'total_agents_tracked': len(self.active_agents),
                    'agents_with_data': len([a for a in self.performance_cache if self.performance_cache[a]]),
                    'total_performance_updates': sum(len(cache) for cache in self.performance_cache.values()),
                    'integration_duration': (datetime.now() - self.active_agents[list(self.active_agents.keys())[0]]['first_seen']).total_seconds() if self.active_agents else 0
                },
                'agent_data': {},
                'performance_cache': self.performance_cache,
                'agent_baselines': self.agent_baselines
            }

            # Add agent-specific data
            for agent_id in self.active_agents:
                export_data['agent_data'][agent_id] = {
                    'tracking_info': self.active_agents[agent_id],
                    'baseline_metrics': self.agent_baselines.get(agent_id, {}),
                    'performance_samples': len(self.performance_cache.get(agent_id, []))
                }

            # Save export data
            export_dir = Path("outgoing/ai4all/integration")
            export_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            export_file = export_dir / f"final_integration_data_{timestamp}.json"
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Final integration data exported: {export_file}")

        except Exception as e:
            self.logger.error(f"Error exporting final data: {e}")

    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        return {
            'enhanced_integration': {
                'running': self.running,
                'active_agents': len([a for a in self.active_agents.values() if a.get('status') != 'inactive']),
                'agents_with_performance_data': len([a for a in self.performance_cache if self.performance_cache[a]]),
                'total_performance_updates': sum(len(cache) for cache in self.performance_cache.values()),
                'last_scan': self.last_scan.isoformat() if self.last_scan else None
            },
            'agent_details': self.active_agents,
            'performance_cache_summary': {agent: len(cache) for agent, cache in self.performance_cache.items()},
            'agent_baselines': self.agent_baselines,
            'timestamp': datetime.now().isoformat()
        }


def create_enhanced_integration(config: Dict[str, Any] = None) -> EnhancedAgentIntegration:
    """Create enhanced agent integration"""
    if config is None:
        config = {
            'monitoring_interval': 30,
            'performance_extraction': True,
            'auto_enable_agents': True
        }

    return EnhancedAgentIntegration(config)


def main():
    """Main enhanced integration entry point"""
    logging.basicConfig(level=logging.INFO)

    print("Enhanced AI-for-All Agent Integration")
    print("=" * 40)
    print("Automatically extracting performance data from active agents...\n")

    # Create enhanced integration
    integration = create_enhanced_integration()

    try:
        # Start integration
        integration.start_integration()

        print("✅ Enhanced integration started successfully")
        print("📊 Automatically monitoring agent performance")
        print("🔄 Feeding data to teaching system")
        print("📈 Enabling continuous learning\n")

        # Keep running until interrupted
        while integration.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping enhanced integration...")
        integration.stop_integration()

        # Export final data
        status = integration.get_integration_status()
        print(f"✅ Integration completed: {status['enhanced_integration']['total_performance_updates']} performance updates processed")

        print("✅ Enhanced integration stopped gracefully")

    except Exception as e:
        print(f"❌ Error in enhanced integration: {e}")
        integration.stop_integration()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
