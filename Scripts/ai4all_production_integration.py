#!/usr/bin/env python3
"""
AI-for-All Production Integration - Direct integration with Calyx Terminal
This script provides a production-ready integration without complex import dependencies.
"""

import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Direct imports to avoid package issues
import sys
current_dir = Path(__file__).parent
ai4all_dir = current_dir.parent / "Projects" / "AI_for_All"
sys.path.insert(0, str(ai4all_dir))

# Import teaching components directly
try:
    # Add the AI_for_All directory to path
    sys.path.insert(0, str(ai4all_dir))

    # Import with direct path references
    from teaching.framework import TeachingFramework
    from teaching.agent_interface import AgentTeachingInterface
    from teaching.enhanced_learner import EnhancedAdaptiveLearner
    from monitoring.production_monitor import ProductionMonitor
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some components not available: {e}")
    COMPONENTS_AVAILABLE = False


class CalyxTeachingIntegration:
    """
    Production-ready teaching integration for Calyx Terminal.
    Provides seamless integration with existing agents.
    """

    def __init__(self):
        """Initialize the Calyx teaching integration"""
        self.logger = logging.getLogger("ai4all.calyx_integration")

        # Integration state
        self.running = False
        self.integration_thread = None
        self.last_heartbeat = time.time()

        # Agent configurations
        self.agent_configs = self._load_agent_configurations()

        # Initialize components if available
        if COMPONENTS_AVAILABLE:
            try:
                self.framework = TeachingFramework("config/teaching_config.json")
                self.agent_interface = AgentTeachingInterface(self.framework)
                self.enhanced_learner = EnhancedAdaptiveLearner(self.framework.config.get('enhanced_learning', {}))
                self.monitor = ProductionMonitor({
                    'monitoring_interval': 60,
                    'alerting_interval': 30,
                    'performance_decline_threshold': -0.1,
                    'stability_threshold': 0.7
                })
                self.logger.info("All teaching components initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing components: {e}")
                self.framework = None
                self.agent_interface = None
                self.enhanced_learner = None
                self.monitor = None
        else:
            self.logger.warning("Teaching components not available - running in basic mode")
            self.framework = None
            self.agent_interface = None
            self.enhanced_learner = None
            self.monitor = None

        # Setup logging
        self._setup_logging()

    def _load_agent_configurations(self) -> Dict[str, Any]:
        """Load agent configurations from Calyx config"""
        try:
            # Load from main Calyx config
            with open("config.yaml", 'r') as f:
                import yaml
                calyx_config = yaml.safe_load(f)
                return calyx_config.get('settings', {}).get('ai4all_teaching', {}).get('agents', {})
        except Exception as e:
            self.logger.warning(f"Failed to load agent configurations: {e}")
            return {
                'agent1': {'enabled': True, 'objectives': ['task_efficiency', 'stability']},
                'triage': {'enabled': True, 'objectives': ['latency_optimization', 'stability']},
                'cp6': {'enabled': True, 'objectives': ['interaction_efficiency', 'harmony']},
                'cp7': {'enabled': True, 'objectives': ['diagnostic_accuracy', 'reporting_efficiency']}
            }

    def _setup_logging(self):
        """Setup integration logging"""
        log_dir = Path("outgoing/ai4all/production")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "calyx_integration.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_integration(self):
        """Start the teaching integration"""
        if self.running:
            self.logger.warning("Integration already running")
            return

        self.running = True
        self.logger.info("Starting Calyx teaching integration")

        # Start integration thread
        self.integration_thread = threading.Thread(
            target=self._integration_loop,
            daemon=True
        )
        self.integration_thread.start()

        # Start monitoring if available
        if self.monitor:
            self.monitor.start_monitoring()

        # Auto-enable configured agents
        self._enable_configured_agents()

        self.logger.info("Calyx teaching integration started successfully")

    def stop_integration(self):
        """Stop the teaching integration"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping Calyx teaching integration")

        # Stop monitoring
        if self.monitor:
            self.monitor.stop_monitoring()

        # Wait for integration thread
        if self.integration_thread and self.integration_thread.is_alive():
            self.integration_thread.join(timeout=5)

        self.logger.info("Calyx teaching integration stopped")

    def _enable_configured_agents(self):
        """Enable teaching for all configured agents"""
        if not self.agent_interface:
            return

        for agent_id, config in self.agent_configs.items():
            if config.get('enabled', False):
                try:
                    objectives = config.get('objectives', ['task_efficiency'])
                    success = self.agent_interface.enable_teaching(agent_id, objectives)
                    if success:
                        self.logger.info(f"Enabled teaching for {agent_id}: {objectives}")
                    else:
                        self.logger.warning(f"Failed to enable teaching for {agent_id}")
                except Exception as e:
                    self.logger.error(f"Error enabling teaching for {agent_id}: {e}")

    def _integration_loop(self):
        """Main integration loop"""
        self.logger.info("Integration loop started")

        while self.running:
            try:
                # Monitor agent heartbeats
                self._monitor_agent_heartbeats()

                # Update integration status
                self._update_integration_status()

                # Generate periodic reports
                if time.time() - self.last_heartbeat > 3600:  # Every hour
                    self._generate_hourly_report()
                    self.last_heartbeat = time.time()

                # Sleep for integration interval
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in integration loop: {e}")
                time.sleep(60)

    def _monitor_agent_heartbeats(self):
        """Monitor agent heartbeat files and update teaching"""
        if not self.agent_interface:
            return

        heartbeat_dir = Path("outgoing")
        heartbeat_files = list(heartbeat_dir.glob("*.lock"))

        for heartbeat_file in heartbeat_files:
            agent_id = heartbeat_file.stem

            # Process configured agents
            if agent_id in self.agent_configs and self.agent_configs[agent_id].get('enabled', False):
                try:
                    # Read heartbeat data
                    with open(heartbeat_file, 'r') as f:
                        heartbeat_data = json.load(f)

                    # Extract metrics
                    metrics = self._extract_metrics_from_heartbeat(heartbeat_data)

                    if metrics:
                        # Update teaching system
                        response = self.agent_interface.update_agent_performance(
                            agent_id=agent_id,
                            metrics=metrics,
                            context={'source': 'heartbeat_integration', 'agent_type': agent_id}
                        )

                        if response.get('adaptations_applied'):
                            self.logger.debug(f"Applied adaptations for {agent_id}")

                except Exception as e:
                    self.logger.debug(f"Error processing heartbeat for {agent_id}: {e}")

    def _extract_metrics_from_heartbeat(self, heartbeat_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract performance metrics from heartbeat data"""
        metrics = {}

        try:
            # Extract standard metrics
            if 'tes' in heartbeat_data:
                metrics['tes'] = float(heartbeat_data['tes'])

            if 'status' in heartbeat_data:
                metrics['stability'] = 1.0 if heartbeat_data['status'] == 'running' else 0.5

            if 'latency' in heartbeat_data:
                latency = float(heartbeat_data['latency'])
                metrics['velocity'] = max(0, 1.0 - (latency / 1000.0))

            if 'error_rate' in heartbeat_data:
                metrics['error_rate'] = float(heartbeat_data['error_rate'])

            # Calculate efficiency
            if metrics:
                efficiency_factors = []
                for metric in ['tes', 'stability', 'velocity']:
                    if metric in metrics:
                        efficiency_factors.append(metrics[metric])

                if efficiency_factors:
                    metrics['efficiency'] = sum(efficiency_factors) / len(efficiency_factors)

            return metrics if metrics else None

        except (ValueError, KeyError, TypeError) as e:
            self.logger.debug(f"Error extracting metrics: {e}")
            return None

    def _update_integration_status(self):
        """Update integration status and log key metrics"""
        try:
            if self.agent_interface:
                overview = self.agent_interface.get_system_overview()
                agents_enabled = overview.get('agent_interface', {}).get('agents_with_teaching_enabled', 0)
                active_sessions = overview.get('agent_interface', {}).get('active_sessions', 0)

                self.logger.info(f"Integration status: {agents_enabled} agents enabled, {active_sessions} active sessions")

        except Exception as e:
            self.logger.debug(f"Error updating integration status: {e}")

    def _generate_hourly_report(self):
        """Generate hourly integration report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            report = {
                'timestamp': datetime.now().isoformat(),
                'integration_status': self.get_integration_status(),
                'agent_configurations': self.agent_configs,
                'components_available': COMPONENTS_AVAILABLE,
                'teaching_system_active': self.agent_interface is not None
            }

            # Save report
            report_dir = Path("outgoing/ai4all/reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"hourly_integration_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated hourly integration report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating hourly report: {e}")

    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        status = {
            'calyx_integration': {
                'running': self.running,
                'components_available': COMPONENTS_AVAILABLE,
                'teaching_system_active': self.agent_interface is not None,
                'enhanced_learning_available': self.enhanced_learner is not None,
                'monitoring_active': self.monitor is not None and self.monitor.running
            },
            'agent_configurations': self.agent_configs,
            'timestamp': datetime.now().isoformat()
        }

        if self.agent_interface:
            status['teaching_system'] = self.agent_interface.get_system_overview()

        if self.monitor:
            status['monitoring'] = self.monitor.get_monitoring_status()

        return status

    def update_agent_performance(self, agent_id: str, metrics: Dict[str, float],
                               context: Dict[str, str] = None) -> Dict[str, Any]:
        """Update performance for a specific agent"""
        if not self.agent_interface:
            return {'error': 'Teaching system not available'}

        try:
            return self.agent_interface.update_agent_performance(
                agent_id=agent_id,
                metrics=metrics,
                context=context
            )
        except Exception as e:
            self.logger.error(f"Error updating performance for {agent_id}: {e}")
            return {'error': str(e)}

    def get_agent_recommendations(self, agent_id: str = None) -> Dict[str, Any]:
        """Get recommendations for agents"""
        if not self.agent_interface:
            return {'error': 'Teaching system not available'}

        if agent_id:
            try:
                return self.agent_interface.get_teaching_recommendations(agent_id)
            except Exception as e:
                return {'error': str(e)}
        else:
            # Get recommendations for all agents
            all_recommendations = {}
            for agent in self.agent_configs:
                try:
                    recommendations = self.agent_interface.get_teaching_recommendations(agent)
                    if recommendations:
                        all_recommendations[agent] = recommendations
                except Exception as e:
                    self.logger.debug(f"Error getting recommendations for {agent}: {e}")

            return {'all_agents': all_recommendations}

    def export_integration_data(self, output_path: str = None) -> str:
        """Export comprehensive integration data"""
        if not output_path:
            timestamp = int(time.time())
            output_path = f"outgoing/ai4all/exports/calyx_integration_{timestamp}.json"

        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'calyx_integration': self.get_integration_status(),
                'agent_configurations': self.agent_configs,
                'components_status': {
                    'framework': self.framework is not None,
                    'agent_interface': self.agent_interface is not None,
                    'enhanced_learner': self.enhanced_learner is not None,
                    'monitor': self.monitor is not None
                }
            }

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Integration data exported to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting integration data: {e}")
            return ""


def main():
    """Main production integration entry point"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Calyx Terminal Integration")
    print("=" * 45)
    print("Integrating teaching system with existing agents...\n")

    # Create integration
    integration = CalyxTeachingIntegration()

    try:
        # Start integration
        integration.start_integration()

        print("[SUCCESS] Production integration started successfully")
        print("[MONITOR] Monitoring agents and providing continuous learning")
        print("[LOOP] System will run until interrupted")
        print("\nCommands:")
        print("  --status       Show integration status")
        print("  --recommendations  Show teaching recommendations")
        print("  --export <path> Export integration data")
        print("  --help         Show this help\n")

        # Keep running until interrupted
        while integration.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[STOP] Stopping production integration...")
        integration.stop_integration()

        # Export final data
        export_path = integration.export_integration_data()
        if export_path:
            print(f"[EXPORT] Exported integration data to: {export_path}")

        print("[SUCCESS] Production integration stopped gracefully")

    except Exception as e:
        print(f"[ERROR] Error in production integration: {e}")
        integration.stop_integration()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
