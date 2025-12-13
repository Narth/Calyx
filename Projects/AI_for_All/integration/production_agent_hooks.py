"""
Production Agent Hooks - Seamless integration with existing Calyx Terminal agents
"""

import json
import logging
import threading
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Import teaching system
import sys
import os

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from teaching.framework import TeachingFramework
    from teaching.agent_interface import AgentTeachingInterface
    from teaching.enhanced_learner import EnhancedAdaptiveLearner
    from monitoring.production_monitor import ProductionMonitor
except ImportError as e:
    print(f"Import error in production hooks: {e}")
    # Emergency fallback with absolute paths
    sys.path.insert(0, os.path.join(parent_dir, 'teaching'))
    sys.path.insert(0, os.path.join(parent_dir, 'monitoring'))

    from framework import TeachingFramework
    from agent_interface import AgentTeachingInterface
    from enhanced_learner import EnhancedAdaptiveLearner
    from production_monitor import ProductionMonitor


class AgentTeachingHook:
    """
    Production-ready hook for integrating teaching capabilities into existing agents.
    Provides a simple interface that agents can use to participate in the teaching system.
    """

    def __init__(self, agent_id: str, config_path: str = None):
        """
        Initialize teaching hook for an agent.

        Args:
            agent_id: Agent identifier
            config_path: Path to teaching configuration
        """
        self.agent_id = agent_id
        self.config_path = config_path or "Projects/AI_for_All/config/teaching_config.json"
        self.logger = logging.getLogger(f"agent_hook.{agent_id}")

        # Initialize teaching components
        self.framework = TeachingFramework(self.config_path)
        self.agent_interface = AgentTeachingInterface(self.framework)

        # Enhanced learning (optional)
        try:
            self.enhanced_learner = EnhancedAdaptiveLearner(self.framework.config.get('enhanced_learning', {}))
            self.enhanced_available = True
        except Exception as e:
            self.logger.debug(f"Enhanced learner not available: {e}")
            self.enhanced_learner = None
            self.enhanced_available = False

        # Hook state
        self.enabled = False
        self.performance_history = []
        self.last_update = None

        # Auto-enable if configured
        self._auto_enable_if_configured()

    def _auto_enable_if_configured(self):
        """Auto-enable teaching if the agent is configured for it"""
        try:
            # Check if agent is configured for teaching
            if hasattr(self.agent_interface, 'agent_configs') and self.agent_id in self.agent_interface.agent_configs:
                config = self.agent_interface.agent_configs[self.agent_id]
                if config.get('teaching_enabled', False):
                    success = self.agent_interface.enable_teaching(self.agent_id)
                    if success:
                        self.enabled = True
                        self.logger.info(f"Auto-enabled teaching for {self.agent_id}")
                    else:
                        self.logger.warning(f"Failed to auto-enable teaching for {self.agent_id}")
        except Exception as e:
            self.logger.debug(f"Error in auto-enable check: {e}")

    def enable_teaching(self, learning_objectives: list = None) -> bool:
        """Enable teaching for this agent"""
        try:
            success = self.agent_interface.enable_teaching(self.agent_id, learning_objectives)
            if success:
                self.enabled = True
                self.logger.info(f"Teaching enabled for {self.agent_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error enabling teaching: {e}")
            return False

    def disable_teaching(self) -> bool:
        """Disable teaching for this agent"""
        try:
            success = self.agent_interface.disable_teaching(self.agent_id)
            if success:
                self.enabled = False
                self.logger.info(f"Teaching disabled for {self.agent_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error disabling teaching: {e}")
            return False

    def update_performance(self, metrics: Dict[str, float], context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update agent performance and receive teaching feedback.

        Args:
            metrics: Current performance metrics (tes, stability, velocity, error_rate, etc.)
            context: Additional context about the agent's current state

        Returns:
            Teaching system response with adaptations and suggestions
        """
        if not self.enabled:
            return {'teaching_enabled': False}

        try:
            # Update teaching system
            response = self.agent_interface.update_agent_performance(
                agent_id=self.agent_id,
                metrics=metrics,
                context=context
            )

            # Store performance for monitoring
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics.copy(),
                'context': context or {},
                'teaching_response': response.copy()
            })

            # Keep only recent history
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]

            self.last_update = datetime.now()

            # Log significant events
            adaptations = response.get('adaptations_applied', [])
            if adaptations:
                self.logger.info(f"Applied {len(adaptations)} adaptations for {self.agent_id}")

            return response

        except Exception as e:
            self.logger.error(f"Error updating performance: {e}")
            return {'error': str(e)}

    def get_teaching_status(self) -> Dict[str, Any]:
        """Get current teaching status for this agent"""
        if not self.enabled:
            return {'teaching_enabled': False}

        try:
            return self.agent_interface.get_agent_teaching_status(self.agent_id)
        except Exception as e:
            self.logger.error(f"Error getting teaching status: {e}")
            return {'error': str(e)}

    def get_recommendations(self) -> list:
        """Get teaching recommendations for this agent"""
        if not self.enabled:
            return ["Enable teaching system for personalized recommendations"]

        try:
            return self.agent_interface.get_teaching_recommendations(self.agent_id)
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return [f"Error retrieving recommendations: {str(e)}"]

    def apply_adaptation(self, adaptation: Dict[str, Any]) -> bool:
        """
        Apply a teaching adaptation to the agent's behavior.

        Args:
            adaptation: Adaptation parameters from the teaching system

        Returns:
            True if adaptation was applied successfully
        """
        try:
            # This is where agent-specific adaptation logic would go
            adaptation_desc = adaptation.get('adaptation', 'Unknown adaptation')

            self.logger.info(f"Applying teaching adaptation for {self.agent_id}: {adaptation_desc}")

            # Example adaptations that agents might implement:
            if 'learning_rate' in adaptation_desc.lower():
                # Adjust learning rate (example implementation)
                self._adjust_learning_rate(adaptation)

            elif 'stability' in adaptation_desc.lower():
                # Adjust stability parameters
                self._adjust_stability_parameters(adaptation)

            elif 'exploration' in adaptation_desc.lower():
                # Adjust exploration behavior
                self._adjust_exploration_behavior(adaptation)

            else:
                self.logger.info(f"Applied general adaptation: {adaptation_desc}")

            return True

        except Exception as e:
            self.logger.error(f"Error applying adaptation: {e}")
            return False

    def _adjust_learning_rate(self, adaptation: Dict[str, Any]):
        """Adjust agent's learning rate based on teaching feedback"""
        # This would be implemented by the specific agent
        # Example: modify learning rate in agent configuration
        current_rate = adaptation.get('current_value', 0.1)
        suggested_rate = adaptation.get('suggested_value', 0.1)

        self.logger.info(f"Adjusting learning rate: {current_rate:.3f} -> {suggested_rate:.3f}")

        # Agent-specific implementation would go here
        # For example:
        # self.agent_config['learning_rate'] = suggested_rate
        # self.reinitialize_learning_model()

    def _adjust_stability_parameters(self, adaptation: Dict[str, Any]):
        """Adjust agent's stability parameters"""
        # Agent-specific stability adjustments
        self.logger.info(f"Adjusting stability parameters: {adaptation.get('reasoning', 'Stability optimization')}")

        # Example implementation:
        # self.agent_config['stability_threshold'] = adaptation.get('suggested_value', 0.9)
        # self.agent_config['error_tolerance'] = self._calculate_error_tolerance(adaptation)

    def _adjust_exploration_behavior(self, adaptation: Dict[str, Any]):
        """Adjust agent's exploration behavior"""
        self.logger.info(f"Adjusting exploration: {adaptation.get('reasoning', 'Exploration optimization')}")

        # Example implementation:
        # self.agent_config['exploration_rate'] = adaptation.get('suggested_value', 0.1)
        # self.reset_exploration_strategy()

    def get_learning_insights(self) -> Dict[str, Any]:
        """Get enhanced learning insights for this agent"""
        if not self.enabled or not self.enhanced_available:
            return {'enhanced_learning': False}

        try:
            return self.enhanced_learner.get_learning_insights(self.agent_id)
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return {'error': str(e)}

    def export_performance_data(self, output_path: str = None) -> Optional[str]:
        """Export performance data for analysis"""
        if not output_path:
            timestamp = int(datetime.now().timestamp())
            output_path = f"outgoing/ai4all/exports/{self.agent_id}_performance_{timestamp}.json"

        try:
            export_data = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat(),
                'teaching_enabled': self.enabled,
                'performance_history': self.performance_history,
                'last_update': self.last_update.isoformat() if self.last_update else None
            }

            if self.enabled:
                export_data['teaching_status'] = self.get_teaching_status()

            if self.enhanced_available:
                export_data['learning_insights'] = self.get_learning_insights()

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Performance data exported to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting performance data: {e}")
            return None

    def get_hook_status(self) -> Dict[str, Any]:
        """Get comprehensive hook status"""
        return {
            'agent_id': self.agent_id,
            'teaching_enabled': self.enabled,
            'enhanced_learning_available': self.enhanced_available,
            'performance_history_count': len(self.performance_history),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'framework_status': self.framework.get_system_status(),
            'timestamp': datetime.now().isoformat()
        }


class ProductionIntegrationManager:
    """
    Manages production integration of teaching system across all agents.
    Provides centralized control and monitoring of teaching integration.
    """

    def __init__(self):
        """Initialize production integration manager"""
        self.logger = logging.getLogger("ai4all.integration_manager")

        # Agent hooks
        self.agent_hooks: Dict[str, AgentTeachingHook] = {}

        # Production monitor
        self.monitor = ProductionMonitor({
            'monitoring_interval': 60,
            'alerting_interval': 30,
            'performance_decline_threshold': -0.1,
            'adaptation_failure_threshold': 0.5,
            'stability_threshold': 0.7,
            'resource_threshold': 0.8,
            'knowledge_threshold': 0.6,
            'metrics_history_size': 1000
        })

        # Integration state
        self.running = False
        self.integration_thread = None

        self.logger.info("Production integration manager initialized")

    def start_integration(self):
        """Start production integration for all agents"""
        if self.running:
            self.logger.warning("Integration already running")
            return

        self.running = True
        self.logger.info("Starting production integration")

        # Start monitoring
        self.monitor.start_monitoring()

        # Start integration thread
        self.integration_thread = threading.Thread(
            target=self._integration_loop,
            daemon=True
        )
        self.integration_thread.start()

        # Initialize agent hooks
        self._initialize_agent_hooks()

        self.logger.info("Production integration started")

    def stop_integration(self):
        """Stop production integration"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping production integration")

        # Stop monitoring
        self.monitor.stop_monitoring()

        # Wait for integration thread
        if self.integration_thread and self.integration_thread.is_alive():
            self.integration_thread.join(timeout=5)

        # Export final data for all agents
        for agent_id, hook in self.agent_hooks.items():
            try:
                hook.export_performance_data()
            except Exception as e:
                self.logger.debug(f"Error exporting data for {agent_id}: {e}")

        self.logger.info("Production integration stopped")

    def _initialize_agent_hooks(self):
        """Initialize hooks for all configured agents"""
        # Get list of agents from configuration
        try:
            config_path = Path("Projects/AI_for_All/config/agent_teaching_configs.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    agent_configs = json.load(f)

                for agent_id in agent_configs.keys():
                    try:
                        hook = AgentTeachingHook(agent_id)
                        self.agent_hooks[agent_id] = hook
                        self.logger.info(f"Initialized hook for {agent_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to initialize hook for {agent_id}: {e}")
            else:
                self.logger.warning("Agent configuration file not found, using default agents")

                # Initialize default agents
                default_agents = ['agent1', 'triage', 'cp6', 'cp7']
                for agent_id in default_agents:
                    try:
                        hook = AgentTeachingHook(agent_id)
                        self.agent_hooks[agent_id] = hook
                        self.logger.info(f"Initialized default hook for {agent_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to initialize default hook for {agent_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error initializing agent hooks: {e}")

    def _integration_loop(self):
        """Main integration loop"""
        self.logger.info("Integration loop started")

        while self.running:
            try:
                # Check agent heartbeat files and update teaching system
                self._monitor_agent_heartbeats()

                # Update integration status
                self._update_integration_status()

                # Sleep for integration interval
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in integration loop: {e}")
                time.sleep(60)

    def _monitor_agent_heartbeats(self):
        """Monitor agent heartbeat files and update teaching"""
        heartbeat_dir = Path("outgoing")
        heartbeat_files = list(heartbeat_dir.glob("*.lock"))

        for heartbeat_file in heartbeat_files:
            agent_id = heartbeat_file.stem

            # Process known agents
            if agent_id in self.agent_hooks:
                try:
                    # Read heartbeat data
                    with open(heartbeat_file, 'r') as f:
                        heartbeat_data = json.load(f)

                    # Extract metrics and update teaching
                    metrics = self._extract_metrics_from_heartbeat(heartbeat_data)

                    if metrics:
                        hook = self.agent_hooks[agent_id]
                        response = hook.update_performance(metrics, {'source': 'heartbeat_integration'})

                        if response.get('adaptations_applied'):
                            self.logger.debug(f"Applied adaptations for {agent_id} via heartbeat")

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

            # Calculate composite metrics
            if metrics:
                # Simple efficiency calculation
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

    def _update_integration_status(self):
        """Update overall integration status"""
        # This could emit status updates, generate reports, etc.
        pass

    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        status = {
            'integration_manager': {
                'running': self.running,
                'agents_configured': len(self.agent_hooks),
                'monitoring_active': self.monitor.running if self.monitor else False
            },
            'agents': {},
            'monitoring': self.monitor.get_monitoring_status() if self.monitor else {},
            'timestamp': datetime.now().isoformat()
        }

        # Get status for each agent
        for agent_id, hook in self.agent_hooks.items():
            status['agents'][agent_id] = hook.get_hook_status()

        return status

    def enable_agent(self, agent_id: str, learning_objectives: list = None) -> bool:
        """Enable teaching for a specific agent"""
        if agent_id not in self.agent_hooks:
            # Create hook for new agent
            try:
                hook = AgentTeachingHook(agent_id)
                self.agent_hooks[agent_id] = hook
            except Exception as e:
                self.logger.error(f"Failed to create hook for {agent_id}: {e}")
                return False

        return self.agent_hooks[agent_id].enable_teaching(learning_objectives)

    def disable_agent(self, agent_id: str) -> bool:
        """Disable teaching for a specific agent"""
        if agent_id in self.agent_hooks:
            return self.agent_hooks[agent_id].disable_teaching()
        return True

    def update_agent_performance(self, agent_id: str, metrics: Dict[str, float],
                               context: Dict[str, str] = None) -> Dict[str, Any]:
        """Update performance for a specific agent"""
        if agent_id in self.agent_hooks:
            return self.agent_hooks[agent_id].update_performance(metrics, context)
        else:
            self.logger.warning(f"No hook found for agent {agent_id}")
            return {'error': 'Agent not found'}

    def get_agent_recommendations(self, agent_id: str = None) -> Dict[str, Any]:
        """Get recommendations for agents"""
        if agent_id:
            if agent_id in self.agent_hooks:
                return {'agent_id': agent_id, 'recommendations': self.agent_hooks[agent_id].get_recommendations()}
            else:
                return {'error': f'Agent {agent_id} not found'}
        else:
            # Get recommendations for all agents
            all_recommendations = {}
            for agent_id, hook in self.agent_hooks.items():
                if hook.enabled:
                    recommendations = hook.get_recommendations()
                    if recommendations:
                        all_recommendations[agent_id] = recommendations

            return {'all_agents': all_recommendations}

    def export_all_data(self, output_dir: str = None) -> Dict[str, str]:
        """Export data for all agents"""
        if not output_dir:
            timestamp = int(datetime.now().timestamp())
            output_dir = f"outgoing/ai4all/exports/integration_{timestamp}"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        exported_files = {}

        # Export data for each agent
        for agent_id, hook in self.agent_hooks.items():
            try:
                export_path = hook.export_performance_data(str(output_dir / f"{agent_id}_data.json"))
                if export_path:
                    exported_files[agent_id] = export_path
            except Exception as e:
                self.logger.error(f"Error exporting data for {agent_id}: {e}")

        # Export system data
        try:
            system_status = self.get_integration_status()
            system_file = output_dir / "system_status.json"
            with open(system_file, 'w') as f:
                json.dump(system_status, f, indent=2, default=str)
            exported_files['system'] = str(system_file)

            self.logger.info(f"Exported integration data to {output_dir}")
            return exported_files

        except Exception as e:
            self.logger.error(f"Error exporting system data: {e}")
            return exported_files


# Factory functions for easy integration

def create_agent_hook(agent_id: str, config_path: str = None) -> AgentTeachingHook:
    """Create a teaching hook for an agent"""
    return AgentTeachingHook(agent_id, config_path)


def create_integration_manager() -> ProductionIntegrationManager:
    """Create the production integration manager"""
    return ProductionIntegrationManager()


def create_production_integration(config_path: str = None) -> ProductionIntegrationManager:
    """Create the production integration manager (alias for create_integration_manager)"""
    return create_integration_manager()


def integrate_with_agent1():
    """Easy integration for Agent1"""
    hook = create_agent_hook('agent1')
    hook.enable_teaching(['task_efficiency', 'stability'])
    return hook


def integrate_with_triage():
    """Easy integration for Triage"""
    hook = create_agent_hook('triage')
    hook.enable_teaching(['latency_optimization', 'stability'])
    return hook


def integrate_with_copilot(copilot_id: str):
    """Easy integration for copilots"""
    # Define objectives based on copilot type
    objectives_map = {
        'cp6': ['interaction_efficiency', 'harmony'],
        'cp7': ['diagnostic_accuracy', 'reporting_efficiency'],
        'cp8': ['system_optimization', 'resource_management'],
        'cp9': ['performance_tuning', 'efficiency_analysis'],
        'cp10': ['pattern_analysis', 'recommendation_accuracy']
    }

    hook = create_agent_hook(copilot_id)
    objectives = objectives_map.get(copilot_id, ['general_efficiency'])
    hook.enable_teaching(objectives)
    return hook


# Aliases for backward compatibility
integrate_agent1 = integrate_with_agent1
integrate_triage = integrate_with_triage


def main():
    """Main integration entry point"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Production Integration")
    print("=" * 40)
    print("Integrating teaching system with Calyx Terminal agents...")

    # Create integration manager
    manager = create_integration_manager()

    try:
        # Start integration
        manager.start_integration()

        print("✅ Production integration started")
        print("📊 Monitoring agents and providing continuous learning")
        print("🔄 System will run until interrupted")

        # Keep running until interrupted
        while manager.running:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping production integration...")
        manager.stop_integration()

        # Export final data
        exported = manager.export_all_data()
        print(f"✅ Exported data for {len(exported)} components")

        print("✅ Production integration stopped gracefully")

    except Exception as e:
        print(f"❌ Error in production integration: {e}")
        manager.stop_integration()


if __name__ == "__main__":
    import time
    main()
