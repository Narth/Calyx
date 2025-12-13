"""
Agent Teaching Integration - Hooks for integrating teaching methods into existing Calyx Terminal agents
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Import the teaching system (with error handling for missing dependencies)
try:
    from ..teaching.framework import TeachingFramework
    from ..teaching.agent_interface import AgentTeachingInterface
    TEACHING_AVAILABLE = True
except ImportError:
    TEACHING_AVAILABLE = False
    TeachingFramework = None
    AgentTeachingInterface = None


class AgentTeachingIntegration:
    """
    Integration layer for adding teaching capabilities to existing Calyx Terminal agents.
    This class provides hooks that agents can call to participate in the teaching system.
    """

    def __init__(self, agent_id: str, config_path: str = None):
        """
        Initialize teaching integration for an agent.

        Args:
            agent_id: Unique identifier for the agent
            config_path: Path to teaching configuration
        """
        self.agent_id = agent_id
        self.config_path = config_path or "config/teaching_config.json"
        self.logger = logging.getLogger(f"agent_teaching.{agent_id}")

        # Teaching system state
        self.teaching_enabled = False
        self.framework = None
        self.agent_interface = None

        # Performance tracking
        self.performance_history: list = []
        self.last_metrics_update = None

        # Initialize teaching system if available
        if TEACHING_AVAILABLE:
            self._initialize_teaching_system()
        else:
            self.logger.warning("Teaching system not available - running in standalone mode")

    def _initialize_teaching_system(self):
        """Initialize the teaching system components"""
        try:
            self.framework = TeachingFramework(self.config_path)
            self.agent_interface = AgentTeachingInterface(self.framework)

            # Enable teaching for this agent
            success = self.agent_interface.enable_teaching(self.agent_id)
            if success:
                self.teaching_enabled = True
                self.logger.info(f"Teaching integration enabled for {self.agent_id}")
            else:
                self.logger.warning(f"Failed to enable teaching for {self.agent_id}")

        except Exception as e:
            self.logger.error(f"Failed to initialize teaching system: {e}")
            self.logger.debug(traceback.format_exc())

    def update_performance(self, metrics: Dict[str, float], context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update agent performance metrics and receive teaching feedback.

        Args:
            metrics: Current performance metrics (tes, stability, velocity, error_rate, etc.)
            context: Additional context about the agent's current state

        Returns:
            Teaching system response with adaptations and suggestions
        """
        if not self.teaching_enabled or not self.agent_interface:
            # Store metrics locally for when teaching becomes available
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics.copy(),
                'context': context or {}
            })

            return {'teaching_enabled': False, 'stored_locally': True}

        try:
            response = self.agent_interface.update_agent_performance(
                agent_id=self.agent_id,
                metrics=metrics,
                context=context
            )

            self.last_metrics_update = datetime.now()

            # Log significant events
            if response.get('adaptations_applied'):
                self.logger.info(f"Teaching adaptations applied: {len(response['adaptations_applied'])} adaptations")

            return response

        except Exception as e:
            self.logger.error(f"Error updating teaching performance: {e}")
            return {'error': str(e)}

    def get_teaching_status(self) -> Dict[str, Any]:
        """Get current teaching status for this agent"""
        if not self.teaching_enabled or not self.agent_interface:
            return {
                'teaching_enabled': False,
                'reason': 'Teaching system not available or not enabled',
                'performance_history_count': len(self.performance_history)
            }

        try:
            return self.agent_interface.get_agent_teaching_status(self.agent_id)
        except Exception as e:
            self.logger.error(f"Error getting teaching status: {e}")
            return {'error': str(e)}

    def get_recommendations(self) -> list:
        """Get teaching recommendations for this agent"""
        if not self.teaching_enabled or not self.agent_interface:
            return ["Enable teaching system for personalized recommendations"]

        try:
            recommendations = self.agent_interface.get_teaching_recommendations(self.agent_id)
            return recommendations
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return [f"Error retrieving recommendations: {str(e)}"]

    def apply_teaching_adaptation(self, adaptation: Dict[str, Any]) -> bool:
        """
        Apply a teaching adaptation to the agent's behavior.

        Args:
            adaptation: Adaptation parameters from the teaching system

        Returns:
            True if adaptation was applied successfully
        """
        try:
            # This is where agent-specific adaptation logic would go
            # For now, just log the adaptation request

            self.logger.info(f"Applying teaching adaptation: {adaptation}")

            # In a real implementation, this would modify agent parameters like:
            # - Learning rates
            # - Thresholds
            # - Behavior patterns
            # - Resource allocation

            return True

        except Exception as e:
            self.logger.error(f"Error applying adaptation: {e}")
            return False

    def export_performance_data(self, output_path: str = None) -> Optional[str]:
        """Export performance data for analysis"""
        if not output_path:
            timestamp = int(datetime.now().timestamp())
            output_path = f"outgoing/ai4all/exports/{self.agent_id}_performance_{timestamp}.json"

        try:
            export_data = {
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat(),
                'teaching_enabled': self.teaching_enabled,
                'performance_history': self.performance_history,
                'last_metrics_update': self.last_metrics_update.isoformat() if self.last_metrics_update else None
            }

            if self.teaching_enabled and self.agent_interface:
                export_data['teaching_status'] = self.get_teaching_status()

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Performance data exported to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting performance data: {e}")
            return None

    def sync_with_teaching_system(self) -> bool:
        """Sync local performance data with teaching system"""
        if not TEACHING_AVAILABLE or not self.agent_interface:
            return False

        try:
            # Send any locally stored performance data to teaching system
            for performance_entry in self.performance_history:
                if self.teaching_enabled:
                    self.agent_interface.update_agent_performance(
                        agent_id=self.agent_id,
                        metrics=performance_entry['metrics'],
                        context=performance_entry['context']
                    )

            # Clear local history since it's now in the teaching system
            self.performance_history.clear()

            self.logger.info("Synchronized with teaching system")
            return True

        except Exception as e:
            self.logger.error(f"Error syncing with teaching system: {e}")
            return False

    def disable_teaching(self):
        """Disable teaching for this agent"""
        if self.teaching_enabled and self.agent_interface:
            success = self.agent_interface.disable_teaching(self.agent_id)
            if success:
                self.teaching_enabled = False
                self.logger.info(f"Teaching disabled for {self.agent_id}")

    def enable_teaching(self, learning_objectives: list = None) -> bool:
        """Enable teaching for this agent"""
        if not TEACHING_AVAILABLE:
            self.logger.warning("Teaching system not available")
            return False

        if not self.agent_interface:
            self._initialize_teaching_system()

        if self.agent_interface:
            success = self.agent_interface.enable_teaching(self.agent_id, learning_objectives)
            if success:
                self.teaching_enabled = True
                self.logger.info(f"Teaching enabled for {self.agent_id}")
                return True

        return False

    def get_heartbeat_data(self) -> Dict[str, Any]:
        """Get heartbeat data for system monitoring"""
        heartbeat = {
            'agent_id': self.agent_id,
            'teaching_enabled': self.teaching_enabled,
            'teaching_available': TEACHING_AVAILABLE,
            'performance_history_count': len(self.performance_history),
            'last_metrics_update': self.last_metrics_update.isoformat() if self.last_metrics_update else None,
            'timestamp': datetime.now().isoformat()
        }

        if self.teaching_enabled and self.agent_interface:
            # Get additional teaching system data
            try:
                status = self.get_teaching_status()
                heartbeat['active_sessions'] = len(status.get('active_sessions', []))
                heartbeat['progress_summary'] = status.get('progress_summary', {})
            except Exception as e:
                self.logger.debug(f"Error getting teaching status for heartbeat: {e}")

        return heartbeat


def create_teaching_integration(agent_id: str, config_path: str = None) -> AgentTeachingIntegration:
    """
    Factory function to create teaching integration for an agent.

    Args:
        agent_id: Agent identifier
        config_path: Path to teaching configuration

    Returns:
        AgentTeachingIntegration instance
    """
    return AgentTeachingIntegration(agent_id, config_path)


# Convenience functions for common agent integrations

def integrate_with_agent1():
    """Integration hook for Agent1"""
    integration = create_teaching_integration('agent1')

    # Agent1-specific setup could go here
    integration.logger.info("Agent1 teaching integration created")

    return integration


def integrate_with_triage():
    """Integration hook for Triage system"""
    integration = create_teaching_integration('triage')

    # Triage-specific setup could go here
    integration.logger.info("Triage teaching integration created")

    return integration


def integrate_with_copilot(copilot_id: str):
    """Integration hook for copilots (CP6, CP7, etc.)"""
    integration = create_teaching_integration(copilot_id)

    # Copilot-specific setup could go here
    integration.logger.info(f"{copilot_id} teaching integration created")

    return integration
