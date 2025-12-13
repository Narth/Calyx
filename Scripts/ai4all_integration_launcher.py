#!/usr/bin/env python3
"""
AI-for-All Integration Launcher - Production integration with Calyx Terminal
"""

import json
import time
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime

# Import integration components
try:
    from Projects.AI_for_All.integration.production_agent_hooks import (
        ProductionIntegrationManager,
        create_integration_manager,
        integrate_with_agent1,
        integrate_with_triage,
        integrate_with_copilot
    )
except ImportError:
    # Fallback imports
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Projects', 'AI_for_All'))

    from Projects.AI_for_All.integration.production_agent_hooks import (
        ProductionIntegrationManager,
        create_integration_manager,
        integrate_with_agent1,
        integrate_with_triage,
        integrate_with_copilot
    )

# Import enhanced learning
try:
    from Projects.AI_for_All.teaching.enhanced_learner import EnhancedAdaptiveLearner
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Projects', 'AI_for_All'))

    from teaching.enhanced_learner import EnhancedAdaptiveLearner


class CalyxTeachingIntegration:
    """
    Main integration class for AI-for-All teaching system with Calyx Terminal.
    Provides production-ready integration that respects existing system constraints.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize Calyx teaching integration.

        Args:
            config_path: Path to main Calyx configuration
        """
        self.config_path = config_path or "config.yaml"
        self.logger = logging.getLogger("ai4all.calyx_integration")

        # Load Calyx configuration
        self.calyx_config = self._load_calyx_config()

        # Initialize integration manager
        self.integration_manager = create_integration_manager()

        # Integration state
        self.running = False
        self.integration_thread = None

        # Enhanced learning features
        self.enhanced_learner = None

        # Setup logging
        self._setup_integration_logging()

        self.logger.info("Calyx teaching integration initialized")

    def _load_calyx_config(self) -> Dict:
        """Load main Calyx Terminal configuration"""
        try:
            with open(self.config_path, 'r') as f:
                import yaml
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load Calyx config: {e}")
            return {}

    def _setup_integration_logging(self):
        """Setup integration logging"""
        # Create integration log directory
        log_dir = Path("outgoing/ai4all/integration")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Setup file handler
        handler = logging.FileHandler(log_dir / "calyx_integration.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_integration(self):
        """Start the teaching integration with Calyx Terminal"""
        if self.running:
            self.logger.warning("Integration already running")
            return

        self.running = True
        self.logger.info("Starting Calyx teaching integration")

        # Validate configuration
        if not self._validate_configuration():
            self.logger.error("Configuration validation failed")
            return

        # Start integration in background thread
        self.integration_thread = threading.Thread(
            target=self._integration_main_loop,
            daemon=True
        )
        self.integration_thread.start()

        # Start integration manager
        self.integration_manager.start_integration()

        self.logger.info("Calyx teaching integration started successfully")

    def stop_integration(self):
        """Stop the teaching integration"""
        if not self.running:
            return

        self.running = False
        self.logger.info("Stopping Calyx teaching integration")

        # Stop integration manager
        self.integration_manager.stop_integration()

        # Wait for integration thread
        if self.integration_thread and self.integration_thread.is_alive():
            self.integration_thread.join(timeout=10)

        self.logger.info("Calyx teaching integration stopped")

    def _validate_configuration(self) -> bool:
        """Validate configuration before starting"""
        try:
            # Check if AI-for-All teaching is enabled in main config
            teaching_config = self.calyx_config.get('settings', {}).get('ai4all_teaching', {})

            if not teaching_config.get('enabled', False):
                self.logger.warning("AI-for-All teaching not enabled in main configuration")
                return False

            # Check if required paths exist
            config_path = teaching_config.get('config_path', 'Projects/AI_for_All/config/teaching_config.json')
            agent_config_path = teaching_config.get('agent_configs_path', 'Projects/AI_for_All/config/agent_teaching_configs.json')

            if not Path(config_path).exists():
                self.logger.error(f"Teaching config not found: {config_path}")
                return False

            if not Path(agent_config_path).exists():
                self.logger.error(f"Agent config not found: {agent_config_path}")
                return False

            self.logger.info("Configuration validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def _integration_main_loop(self):
        """Main integration loop"""
        self.logger.info("Integration main loop started")

        while self.running:
            try:
                # Monitor system health
                self._monitor_system_health()

                # Update agent integrations
                self._update_agent_integrations()

                # Check for configuration changes
                self._check_configuration_changes()

                # Sleep for integration interval
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in integration main loop: {e}")
                time.sleep(60)  # Wait longer on errors

    def _monitor_system_health(self):
        """Monitor overall system health"""
        try:
            # Get integration status
            status = self.integration_manager.get_integration_status()

            # Log key metrics
            agents_configured = status['integration_manager']['agents_configured']
            agents_enabled = len([a for a in status['agents'].values() if a.get('teaching_enabled', False)])

            self.logger.info(f"Integration status: {agents_enabled}/{agents_configured} agents enabled")

            # Check for issues
            if agents_enabled == 0:
                self.logger.warning("No agents have teaching enabled")

            # Monitor resource usage if available
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent

                if cpu_percent > 80 or memory_percent > 80:
                    self.logger.warning(f"High resource usage: CPU={cpu_percent:.1f}%, Memory={memory_percent:.1f}%")

            except ImportError:
                pass  # psutil not available

        except Exception as e:
            self.logger.error(f"Error monitoring system health: {e}")

    def _update_agent_integrations(self):
        """Update agent integrations based on current state"""
        try:
            # Check for new agents in heartbeat files
            heartbeat_dir = Path("outgoing")
            heartbeat_files = list(heartbeat_dir.glob("*.lock"))

            for heartbeat_file in heartbeat_files:
                agent_id = heartbeat_file.stem

                # Check if this agent should have teaching enabled
                teaching_config = self.calyx_config.get('settings', {}).get('ai4all_teaching', {}).get('agents', {})

                if agent_id in teaching_config and teaching_config[agent_id].get('enabled', False):
                    # Enable teaching for this agent if not already enabled
                    if agent_id not in self.integration_manager.agent_hooks:
                        self.logger.info(f"Auto-enabling teaching for {agent_id}")
                        self.integration_manager.enable_agent(agent_id, teaching_config[agent_id].get('learning_objectives'))

        except Exception as e:
            self.logger.error(f"Error updating agent integrations: {e}")

    def _check_configuration_changes(self):
        """Check for configuration changes and reload if needed"""
        try:
            # Check if config file has been modified
            config_path = Path("Projects/AI_for_All/config/teaching_config.json")
            if config_path.exists():
                # Simple modification check (in production, would use file timestamps)
                pass

        except Exception as e:
            self.logger.error(f"Error checking configuration changes: {e}")

    def get_integration_status(self) -> Dict[str, Any]:
        """Get comprehensive integration status"""
        status = {
            'calyx_integration': {
                'running': self.running,
                'config_valid': self._validate_configuration(),
                'enhanced_learning': self.enhanced_learner is not None
            },
            'integration_manager': self.integration_manager.get_integration_status(),
            'teaching_config': self.calyx_config.get('settings', {}).get('ai4all_teaching', {}),
            'timestamp': datetime.now().isoformat()
        }

        return status

    def enable_enhanced_learning(self):
        """Enable enhanced learning features"""
        try:
            if self.enhanced_learner is None:
                # Initialize enhanced learner
                teaching_config = self.calyx_config.get('settings', {}).get('ai4all_teaching', {}).get('learning', {})
                self.enhanced_learner = EnhancedAdaptiveLearner(teaching_config)

                self.logger.info("Enhanced learning features enabled")

        except Exception as e:
            self.logger.error(f"Error enabling enhanced learning: {e}")

    def get_system_recommendations(self) -> Dict[str, Any]:
        """Get system-wide recommendations"""
        try:
            # Get recommendations from integration manager
            recommendations = self.integration_manager.get_agent_recommendations()

            # Add system-level recommendations
            system_recommendations = {
                **recommendations,
                'system_level': self._get_system_level_recommendations()
            }

            return system_recommendations

        except Exception as e:
            self.logger.error(f"Error getting system recommendations: {e}")
            return {'error': str(e)}

    def _get_system_level_recommendations(self) -> List[str]:
        """Get system-level recommendations"""
        recommendations = []

        try:
            # Check system health
            status = self.integration_manager.get_integration_status()

            # Check if all configured agents are enabled
            teaching_config = self.calyx_config.get('settings', {}).get('ai4all_teaching', {}).get('agents', {})
            configured_agents = list(teaching_config.keys())
            enabled_agents = [agent for agent, hook in self.integration_manager.agent_hooks.items() if hook.enabled]

            missing_agents = set(configured_agents) - set(enabled_agents)
            if missing_agents:
                recommendations.append(f"Enable teaching for agents: {', '.join(missing_agents)}")

            # Check performance
            for agent_id in enabled_agents:
                if agent_id in status['agents']:
                    agent_status = status['agents'][agent_id]
                    progress = agent_status.get('progress_summary', {}).get('average_progress', 0)

                    if progress < 0.1:
                        recommendations.append(f"Review learning objectives for {agent_id} - low progress ({progress:.1%})")

            # Check resource usage
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent

                if cpu_percent > 70:
                    recommendations.append(f"High CPU usage ({cpu_percent:.1f}%) - consider reducing teaching frequency")

                if memory_percent > 70:
                    recommendations.append(f"High memory usage ({memory_percent:.1f}%) - monitor teaching system impact")

            except ImportError:
                pass

        except Exception as e:
            self.logger.error(f"Error generating system recommendations: {e}")

        return recommendations

    def export_integration_data(self, output_path: str = None) -> str:
        """Export comprehensive integration data"""
        if not output_path:
            timestamp = int(datetime.now().timestamp())
            output_path = f"outgoing/ai4all/exports/calyx_integration_{timestamp}.json"

        try:
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'calyx_integration': self.get_integration_status(),
                'agent_data': self.integration_manager.export_all_data(),
                'system_recommendations': self.get_system_recommendations(),
                'configuration': self.calyx_config.get('settings', {}).get('ai4all_teaching', {})
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
    """Main entry point for Calyx teaching integration"""
    parser = argparse.ArgumentParser(description="AI-for-All Integration with Calyx Terminal")
    parser.add_argument('--config', '-c', default="config.yaml", help='Path to Calyx configuration')
    parser.add_argument('--start', action='store_true', help='Start teaching integration')
    parser.add_argument('--stop', action='store_true', help='Stop teaching integration')
    parser.add_argument('--status', action='store_true', help='Show integration status')
    parser.add_argument('--recommendations', action='store_true', help='Show system recommendations')
    parser.add_argument('--export', help='Export integration data to specified path')
    parser.add_argument('--enable-enhanced', action='store_true', help='Enable enhanced learning features')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create integration
    integration = CalyxTeachingIntegration(args.config)

    try:
        if args.status:
            # Show integration status
            status = integration.get_integration_status()
            print(json.dumps(status, indent=2, default=str))

        elif args.recommendations:
            # Show recommendations
            recommendations = integration.get_system_recommendations()
            print(json.dumps(recommendations, indent=2, default=str))

        elif args.export:
            # Export data
            export_path = integration.export_integration_data(args.export)
            if export_path:
                print(f"Integration data exported to: {export_path}")
            else:
                print("Failed to export integration data")

        elif args.enable_enhanced:
            # Enable enhanced learning
            integration.enable_enhanced_learning()
            print("Enhanced learning features enabled")

        elif args.start:
            # Start integration
            integration.start_integration()
            print("AI-for-All teaching integration started")
            print("Press Ctrl+C to stop")

            # Keep running until interrupted
            while integration.running:
                time.sleep(1)

        elif args.stop:
            # Stop integration
            integration.stop_integration()
            print("AI-for-All teaching integration stopped")

        else:
            # Default: show help
            parser.print_help()

    except KeyboardInterrupt:
        print("\nStopping AI-for-All teaching integration...")
        integration.stop_integration()
        print("Integration stopped")

    except Exception as e:
        print(f"Error: {e}")
        integration.stop_integration()
        if args.verbose:
            raise


if __name__ == "__main__":
    main()
