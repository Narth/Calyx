#!/usr/bin/env python3
"""
AI-for-All Production Integration - Permanent integration with Calyx Terminal agents
"""

import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import teaching system components
from teaching.framework import TeachingFramework
from teaching.agent_interface import AgentTeachingInterface


class ProductionTeachingIntegration:
    """
    Production-ready integration of the AI-for-All teaching system with Calyx Terminal.
    Provides seamless integration with existing agents and continuous learning capabilities.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize production teaching integration.

        Args:
            config_path: Path to teaching configuration
        """
        self.config_path = config_path or "Projects/AI_for_All/config/teaching_config.json"
        self.logger = logging.getLogger("ai4all.production_integration")

        # Initialize core components
        self.framework = TeachingFramework(self.config_path)
        self.agent_interface = AgentTeachingInterface(self.framework)

        # Production state
        self.running = False
        self.monitoring_thread = None
        self.heartbeat_thread = None
        self.last_heartbeat = time.time()

        # Agent performance monitoring
        self.agent_metrics = {}
        self.integration_enabled = {}

        # Setup logging
        self._setup_production_logging()

        self.logger.info("Production teaching integration initialized")

    def _setup_production_logging(self):
        """Setup production-grade logging"""
        # Create log directory
        log_dir = Path("outgoing/ai4all/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Setup rotating file handler for production logs
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            log_dir / "production_integration.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        self.logger.info("Production logging configured")

    def start_production_integration(self):
        """Start the production teaching integration"""
        if self.running:
            self.logger.warning("Production integration already running")
            return

        self.running = True
        self.logger.info("Starting production teaching integration")

        # Start monitoring threads
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()

        # Enable teaching for all configured agents
        self._enable_all_configured_agents()

        self.logger.info("Production teaching integration started successfully")

    def stop_production_integration(self):
        """Stop the production teaching integration"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping production teaching integration")

        # Wait for threads to finish
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)

        self.logger.info("Production teaching integration stopped")

    def _enable_all_configured_agents(self):
        """Enable teaching for all agents configured in the system"""
        configured_agents = list(self.agent_interface.agent_configs.keys())

        for agent_id in configured_agents:
            try:
                success = self.agent_interface.enable_teaching(agent_id)
                if success:
                    self.integration_enabled[agent_id] = True
                    self.logger.info(f"Enabled teaching for {agent_id}")
                else:
                    self.logger.warning(f"Failed to enable teaching for {agent_id}")
            except Exception as e:
                self.logger.error(f"Error enabling teaching for {agent_id}: {e}")

    def _monitoring_loop(self):
        """Main monitoring loop for agent performance"""
        self.logger.info("Monitoring loop started")

        while self.running:
            try:
                # Monitor agent heartbeats and update teaching system
                self._monitor_agent_heartbeats()

                # Update system status
                self._update_system_status()

                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait before retrying

    def _heartbeat_loop(self):
        """Heartbeat emission loop"""
        self.logger.info("Heartbeat loop started")

        while self.running:
            try:
                # Emit teaching system heartbeat
                self.agent_interface.emit_teaching_heartbeat()

                # Emit framework heartbeat
                self.framework.emit_heartbeat()

                # Sleep for heartbeat interval
                heartbeat_interval = self.framework.config['system_integration']['heartbeat_interval']
                time.sleep(heartbeat_interval)

            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(30)  # Wait before retrying

    def _monitor_agent_heartbeats(self):
        """Monitor agent heartbeats and update teaching system"""
        # Check for new agent heartbeats
        heartbeat_files = Path("outgoing").glob("*.lock")

        for heartbeat_file in heartbeat_files:
            agent_id = heartbeat_file.stem

            # Skip system files and known non-agent files
            if agent_id in ['agent1', 'agent2', 'agent3', 'agent4', 'triage', 'cp6', 'cp7', 'cp8', 'cp9', 'cp10', 'cp12', 'bridge', 'cbo', 'svf']:
                try:
                    # Read heartbeat data
                    with open(heartbeat_file, 'r') as f:
                        heartbeat_data = json.load(f)

                    # Extract performance metrics if available
                    metrics = self._extract_metrics_from_heartbeat(heartbeat_data)

                    if metrics:
                        # Update teaching system with agent performance
                        response = self.agent_interface.update_agent_performance(
                            agent_id=agent_id,
                            metrics=metrics,
                            context={'source': 'heartbeat_monitoring'}
                        )

                        if response.get('teaching_enabled'):
                            self.logger.debug(f"Updated teaching for {agent_id}: {len(response.get('adaptations_applied', []))} adaptations")

                except Exception as e:
                    self.logger.debug(f"Error processing heartbeat for {agent_id}: {e}")

    def _extract_metrics_from_heartbeat(self, heartbeat_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract performance metrics from agent heartbeat data"""
        metrics = {}

        try:
            # Extract common metrics from heartbeat
            if 'status' in heartbeat_data:
                metrics['stability'] = 1.0 if heartbeat_data['status'] == 'running' else 0.5

            if 'tes' in heartbeat_data:
                metrics['tes'] = float(heartbeat_data['tes'])

            if 'latency' in heartbeat_data:
                # Convert latency to velocity (higher velocity = lower latency)
                latency = float(heartbeat_data['latency'])
                metrics['velocity'] = max(0, 1.0 - (latency / 1000.0))  # Normalize to 0-1 range

            if 'error_rate' in heartbeat_data:
                metrics['error_rate'] = float(heartbeat_data['error_rate'])

            # Calculate efficiency based on available metrics
            if metrics:
                # Simple efficiency calculation based on available metrics
                efficiency_factors = []
                for metric in ['tes', 'stability', 'velocity']:
                    if metric in metrics:
                        efficiency_factors.append(metrics[metric])

                if efficiency_factors:
                    metrics['efficiency'] = sum(efficiency_factors) / len(efficiency_factors)

            return metrics if metrics else None

        except (ValueError, KeyError, TypeError) as e:
            self.logger.debug(f"Error extracting metrics from heartbeat: {e}")
            return None

    def _update_system_status(self):
        """Update overall system status and generate reports"""
        try:
            # Get system overview
            overview = self.agent_interface.get_system_overview()

            # Log key metrics
            agents_enabled = overview['agent_interface']['agents_with_teaching_enabled']
            active_sessions = overview['agent_interface']['active_sessions']

            self.logger.info(f"System status: {agents_enabled} agents enabled, {active_sessions} active sessions")

            # Generate periodic reports
            if time.time() - self.last_heartbeat > 3600:  # Every hour
                self._generate_hourly_report()
                self.last_heartbeat = time.time()

        except Exception as e:
            self.logger.error(f"Error updating system status: {e}")

    def _generate_hourly_report(self):
        """Generate hourly teaching system report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Get comprehensive system status
            system_status = self.agent_interface.get_system_overview()
            framework_status = self.framework.get_system_status()

            report = {
                'timestamp': datetime.now().isoformat(),
                'report_type': 'hourly',
                'system_status': system_status,
                'framework_status': framework_status,
                'agent_performance': {},
                'recommendations': {}
            }

            # Get status for each agent
            for agent_id in self.integration_enabled:
                if self.integration_enabled[agent_id]:
                    try:
                        agent_status = self.agent_interface.get_agent_teaching_status(agent_id)
                        report['agent_performance'][agent_id] = agent_status

                        recommendations = self.agent_interface.get_teaching_recommendations(agent_id)
                        report['recommendations'][agent_id] = recommendations
                    except Exception as e:
                        self.logger.debug(f"Error getting status for {agent_id}: {e}")

            # Save report
            report_dir = Path("outgoing/ai4all/reports")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"hourly_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated hourly report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating hourly report: {e}")

    def update_agent_performance(self, agent_id: str, metrics: Dict[str, float],
                               context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update performance metrics for an agent.

        Args:
            agent_id: Agent identifier
            metrics: Current performance metrics
            context: Additional context

        Returns:
            Teaching system response
        """
        try:
            response = self.agent_interface.update_agent_performance(
                agent_id=agent_id,
                metrics=metrics,
                context=context
            )

            # Store metrics for monitoring
            self.agent_metrics[agent_id] = {
                'timestamp': datetime.now(),
                'metrics': metrics.copy(),
                'context': context or {}
            }

            return response

        except Exception as e:
            self.logger.error(f"Error updating performance for {agent_id}: {e}")
            return {'error': str(e)}

    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        status = {
            'production_integration': {
                'running': self.running,
                'agents_enabled': len(self.integration_enabled),
                'monitoring_active': self.monitoring_thread.is_alive() if self.monitoring_thread else False,
                'heartbeat_active': self.heartbeat_thread.is_alive() if self.heartbeat_thread else False
            },
            'teaching_system': self.agent_interface.get_system_overview(),
            'agent_metrics': self.agent_metrics,
            'timestamp': datetime.now().isoformat()
        }

        return status

    def enable_agent_teaching(self, agent_id: str, learning_objectives: list = None) -> bool:
        """Enable teaching for a specific agent"""
        try:
            success = self.agent_interface.enable_teaching(agent_id, learning_objectives)
            if success:
                self.integration_enabled[agent_id] = True
                self.logger.info(f"Enabled teaching for {agent_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error enabling teaching for {agent_id}: {e}")
            return False

    def disable_agent_teaching(self, agent_id: str) -> bool:
        """Disable teaching for a specific agent"""
        try:
            success = self.agent_interface.disable_teaching(agent_id)
            if success:
                self.integration_enabled[agent_id] = False
                self.logger.info(f"Disabled teaching for {agent_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error disabling teaching for {agent_id}: {e}")
            return False

    def get_teaching_recommendations(self, agent_id: str = None) -> Dict[str, Any]:
        """Get teaching recommendations for agents"""
        if agent_id:
            return self.agent_interface.get_teaching_recommendations(agent_id)
        else:
            # Get recommendations for all enabled agents
            all_recommendations = {}
            for agent in self.integration_enabled:
                if self.integration_enabled[agent]:
                    recommendations = self.agent_interface.get_teaching_recommendations(agent)
                    if recommendations:
                        all_recommendations[agent] = recommendations

            return {'all_agents': all_recommendations}


def create_production_integration(config_path: str = None) -> ProductionTeachingIntegration:
    """
    Factory function to create production teaching integration.

    Args:
        config_path: Path to teaching configuration

    Returns:
        ProductionTeachingIntegration instance
    """
    return ProductionTeachingIntegration(config_path)


# Convenience functions for common integrations

def integrate_with_agent1():
    """Production integration for Agent1"""
    integration = create_production_integration()
    integration.enable_agent_teaching('agent1', ['task_efficiency', 'stability'])
    return integration


def integrate_with_triage():
    """Production integration for Triage"""
    integration = create_production_integration()
    integration.enable_agent_teaching('triage', ['latency_optimization', 'stability'])
    return integration


def integrate_with_copilot(copilot_id: str):
    """Production integration for copilots"""
    integration = create_production_integration()

    # Define learning objectives based on copilot type
    objectives_map = {
        'cp6': ['interaction_efficiency', 'harmony'],
        'cp7': ['diagnostic_accuracy', 'reporting_efficiency'],
        'cp8': ['system_optimization', 'resource_management'],
        'cp9': ['performance_tuning', 'efficiency_analysis'],
        'cp10': ['pattern_analysis', 'recommendation_accuracy']
    }

    objectives = objectives_map.get(copilot_id, ['general_efficiency'])
    integration.enable_agent_teaching(copilot_id, objectives)
    return integration


def main():
    """Main production integration entry point"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Production Integration")
    print("=" * 40)

    # Create production integration
    integration = create_production_integration()

    try:
        # Start production integration
        integration.start_production_integration()

        print("✅ Production teaching integration started")
        print("📊 Monitoring agents and providing continuous learning")
        print("🔄 Press Ctrl+C to stop")

        # Keep running until interrupted
        while integration.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping production integration...")
        integration.stop_production_integration()
        print("✅ Production integration stopped")

    except Exception as e:
        print(f"❌ Error in production integration: {e}")
        integration.stop_production_integration()


if __name__ == "__main__":
    main()
