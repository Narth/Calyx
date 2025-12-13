#!/usr/bin/env python3
"""
AI-for-All Teaching System - Main integration script for Calyx Terminal
"""

import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

from teaching.framework import TeachingFramework
from teaching.agent_interface import AgentTeachingInterface


class AI4AllTeachingSystem:
    """
    Main system for AI-for-All teaching methods in Calyx Terminal.
    Integrates with existing agents and provides comprehensive learning capabilities.
    """

    def __init__(self, config_path: str = None, *, auto_enable: bool = True, load_existing: bool = True):
        """
        Initialize the AI-for-All teaching system.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path or "config/teaching_config.yaml"

        # Initialize core components
        self.framework = TeachingFramework(self.config_path)
        self.agent_interface = AgentTeachingInterface(
            self.framework,
            auto_enable_configured_agents=auto_enable,
            load_existing_sessions=load_existing,
        )

        # System state
        self.running = False
        self.last_heartbeat = time.time()

        # Setup logging
        self.logger = logging.getLogger("ai4all_teaching")
        self.logger.info("AI-for-All Teaching System initialized")

    def start(self):
        """Start the teaching system"""
        self.running = True
        self.logger.info("AI-for-All Teaching System started")

        # Enable teaching for configured agents
        self._initialize_agent_teaching()

        # Start heartbeat emission
        self._start_heartbeat_loop()

    def stop(self):
        """Stop the teaching system"""
        self.running = False
        self.logger.info("AI-for-All Teaching System stopped")

    def _initialize_agent_teaching(self):
        """Initialize teaching for all configured agents"""
        # Get agents that should have teaching enabled
        agents_to_enable = [
            'agent1', 'triage', 'cp6', 'cp7'
        ]

        for agent_id in agents_to_enable:
            success = self.agent_interface.enable_teaching(agent_id)
            if success:
                self.logger.info(f"Teaching enabled for {agent_id}")
            else:
                self.logger.warning(f"Failed to enable teaching for {agent_id}")

    def _start_heartbeat_loop(self):
        """Start the heartbeat emission loop"""
        heartbeat_interval = self.framework.config['system_integration']['heartbeat_interval']

        while self.running:
            try:
                # Emit heartbeat
                self.agent_interface.emit_teaching_heartbeat()
                self.last_heartbeat = time.time()

                # Sleep for interval
                time.sleep(heartbeat_interval)

            except KeyboardInterrupt:
                self.logger.info("Heartbeat loop interrupted")
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(10)  # Wait before retrying

    def update_agent(self, agent_id: str, metrics: Dict[str, float],
                    context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update an agent's performance and trigger teaching responses.

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

            # Log significant updates
            if response.get('adaptations_applied'):
                self.logger.info(f"Applied adaptations for {agent_id}: {len(response['adaptations_applied'])} adaptations")

            return response

        except Exception as e:
            self.logger.error(f"Error updating agent {agent_id}: {e}")
            return {'error': str(e)}

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive status for an agent"""
        try:
            return self.agent_interface.get_agent_teaching_status(agent_id)
        except Exception as e:
            self.logger.error(f"Error getting status for {agent_id}: {e}")
            return {'error': str(e)}

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            return self.agent_interface.get_system_overview()
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}

    def get_recommendations(self, agent_id: str = None) -> Dict[str, Any]:
        """Get teaching recommendations"""
        try:
            if agent_id:
                recommendations = self.agent_interface.get_teaching_recommendations(agent_id)
                return {'agent_id': agent_id, 'recommendations': recommendations}
            else:
                # Get recommendations for all agents
                all_recommendations = {}
                agents = ['agent1', 'triage', 'cp6', 'cp7']

                for agent in agents:
                    if self.agent_interface.teaching_enabled.get(agent, False):
                        recs = self.agent_interface.get_teaching_recommendations(agent)
                        if recs:
                            all_recommendations[agent] = recs

                return {'all_agents': all_recommendations}

        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return {'error': str(e)}

    def export_learning_data(self, output_path: str = None) -> str:
        """Export learning data for analysis"""
        if not output_path:
            timestamp = int(time.time())
            output_path = f"outgoing/ai4all/export/learning_data_{timestamp}.json"

        try:
            export_data = {
                'timestamp': time.time(),
                'framework_status': self.framework.get_system_status(),
                'agent_interface_overview': self.agent_interface.get_system_overview(),
                'patterns': list(self.framework.pattern_recognition.patterns.values()),
                'transfers': [t.to_dict() for t in self.framework.knowledge_integrator.transfers],
                'active_sessions': [s.to_dict() for s in self.framework.active_sessions.values()]
            }

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            self.logger.info(f"Exported learning data to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting learning data: {e}")
            return None


def main():
    """Main entry point for the AI-for-All teaching system"""
    parser = argparse.ArgumentParser(description="AI-for-All Teaching System for Calyx Terminal")
    parser.add_argument('--config', '-c', default="config/teaching_config.yaml",
                       help='Path to configuration file')
    parser.add_argument('--start', action='store_true', help='Start the teaching system')
    parser.add_argument('--stop', action='store_true', help='Stop the teaching system')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--agent-status', help='Show status for specific agent')
    parser.add_argument('--recommendations', action='store_true', help='Show teaching recommendations')
    parser.add_argument('--agent-recommendations', help='Show recommendations for specific agent')
    parser.add_argument('--export', help='Export learning data to specified path')
    parser.add_argument('--heartbeat', action='store_true', help='Emit heartbeat and exit')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize system
    def _is_runtime_active(grace: float = 120.0) -> bool:
        hb_path = Path("outgoing/ai4all/teaching_heartbeat.json")
        try:
            return hb_path.exists() and (time.time() - hb_path.stat().st_mtime) <= grace
        except Exception:
            return False

    runtime_active = _is_runtime_active()
    read_only_mode = any([
        args.status,
        args.agent_status,
        args.recommendations,
        args.agent_recommendations,
        args.export,
        args.heartbeat
    ])

    auto_enable = bool(args.start) or (not runtime_active and not read_only_mode)

    system = AI4AllTeachingSystem(
        args.config,
        auto_enable=auto_enable,
        load_existing=True
    )

    try:
        if args.heartbeat:
            # Just emit heartbeat and exit
            system.agent_interface.emit_teaching_heartbeat()
            print("Heartbeat emitted successfully")

        elif args.start:
            # Start the system
            system.start()
            print("AI-for-All Teaching System started")
            print("Press Ctrl+C to stop")

            try:
                # Keep running until interrupted
                while system.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping AI-for-All Teaching System...")
                system.stop()

        elif args.status:
            # Show system status
            status = system.get_system_status()
            print(json.dumps(status, indent=2, default=str))

        elif args.agent_status:
            # Show agent status
            status = system.get_agent_status(args.agent_status)
            print(json.dumps(status, indent=2, default=str))

        elif args.recommendations:
            # Show all recommendations
            recommendations = system.get_recommendations()
            print(json.dumps(recommendations, indent=2, default=str))

        elif args.agent_recommendations:
            # Show agent-specific recommendations
            recommendations = system.get_recommendations(args.agent_recommendations)
            print(json.dumps(recommendations, indent=2, default=str))

        elif args.export:
            # Export learning data
            export_path = system.export_learning_data(args.export)
            if export_path:
                print(f"Learning data exported to: {export_path}")
            else:
                print("Failed to export learning data")

        else:
            # Default: show help
            parser.print_help()

    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            raise


if __name__ == "__main__":
    main()

