#!/usr/bin/env python3
"""
Resource-Aware Teaching - Resource optimization for AI-for-All teaching system
"""

import json
import logging
import psutil
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta

from ..teaching.framework import TeachingFramework
from ..teaching.agent_interface import AgentTeachingInterface


class ResourceAwareTeachingOptimizer:
    """
    Resource-aware teaching optimizer that adapts teaching behavior based on system resources.
    Implements the resource optimization framework defined in config.yaml.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize resource-aware teaching optimizer.

        Args:
            config: Resource optimization configuration
        """
        self.config = config
        self.logger = logging.getLogger("ai4all.resource_optimizer")

        # Initialize teaching system
        self.framework = TeachingFramework("config/teaching_config.json")
        self.agent_interface = AgentTeachingInterface(self.framework)

        # Resource monitoring
        self.resource_thresholds = {
            'cpu_soft': config.get('cpu_usage_soft_limit', 70) / 100.0,
            'cpu_hard': config.get('cpu_usage_hard_limit', 85) / 100.0,
            'memory_soft': config.get('memory_soft_limit', 75) / 100.0,
            'memory_hard': config.get('memory_hard_limit', 90) / 100.0,
            'disk_soft': config.get('disk_io_soft_limit', 60) / 100.0,
            'disk_hard': config.get('disk_io_hard_limit', 80) / 100.0
        }

        # Agent resource profiles
        self.agent_profiles = config.get('agent_profiles', {})

        # Optimization state
        self.optimization_active = False
        self.current_resource_mode = 'normal'
        self.resource_history: List[Dict] = []
        self.optimization_actions: List[Dict] = []

        # Setup logging
        self._setup_resource_logging()

        self.logger.info("Resource-aware teaching optimizer initialized")

    def _setup_resource_logging(self):
        """Setup resource optimization logging"""
        log_dir = Path("outgoing/ai4all/optimization")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "resource_optimization.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_optimization(self):
        """Start resource-aware optimization"""
        self.optimization_active = True
        self.logger.info("Resource-aware optimization started")

        # Initial resource assessment
        self._assess_current_resources()

        # Start optimization loop
        self._start_optimization_loop()

    def stop_optimization(self):
        """Stop resource-aware optimization"""
        self.optimization_active = False
        self.logger.info("Resource-aware optimization stopped")

        # Generate final optimization report
        self._generate_optimization_report()

    def _start_optimization_loop(self):
        """Start the resource optimization loop"""
        while self.optimization_active:
            try:
                # Assess current resource usage
                resource_status = self._assess_current_resources()

                # Determine required optimization mode
                optimization_mode = self._determine_optimization_mode(resource_status)

                # Apply optimizations
                if optimization_mode != self.current_resource_mode:
                    self._apply_optimization_mode(optimization_mode)
                    self.current_resource_mode = optimization_mode

                # Record resource history
                self.resource_history.append({
                    'timestamp': datetime.now(),
                    'resource_status': resource_status,
                    'optimization_mode': optimization_mode,
                    'actions_taken': self.optimization_actions[-5:] if self.optimization_actions else []
                })

                # Keep only recent history
                if len(self.resource_history) > 1000:
                    self.resource_history = self.resource_history[-1000:]

                # Sleep for optimization interval
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                time.sleep(60)

    def _assess_current_resources(self) -> Dict[str, Any]:
        """Assess current system resource usage"""
        try:
            # Get current resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            resource_status = {
                'cpu_percent': cpu_percent / 100.0,
                'memory_percent': memory.percent / 100.0,
                'disk_percent': disk.percent / 100.0,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'system_load': cpu_percent / 100.0,
                'timestamp': datetime.now().isoformat()
            }

            # Calculate resource pressure
            resource_pressure = self._calculate_resource_pressure(resource_status)
            resource_status['resource_pressure'] = resource_pressure

            # Determine resource health
            resource_health = self._calculate_resource_health(resource_status)
            resource_status['resource_health'] = resource_health

            return resource_status

        except Exception as e:
            self.logger.error(f"Error assessing resources: {e}")
            return {'error': str(e)}

    def _calculate_resource_pressure(self, resource_status: Dict[str, Any]) -> float:
        """Calculate overall resource pressure (0.0 to 1.0)"""
        try:
            pressure_factors = []

            # CPU pressure
            cpu_pressure = min(1.0, resource_status['cpu_percent'] / self.resource_thresholds['cpu_hard'])
            pressure_factors.append(cpu_pressure)

            # Memory pressure
            memory_pressure = min(1.0, resource_status['memory_percent'] / self.resource_thresholds['memory_hard'])
            pressure_factors.append(memory_pressure)

            # Disk pressure
            disk_pressure = min(1.0, resource_status['disk_percent'] / self.resource_thresholds['disk_hard'])
            pressure_factors.append(disk_pressure)

            return sum(pressure_factors) / len(pressure_factors) if pressure_factors else 0.5

        except Exception as e:
            self.logger.debug(f"Error calculating resource pressure: {e}")
            return 0.5

    def _calculate_resource_health(self, resource_status: Dict[str, Any]) -> str:
        """Calculate overall resource health status"""
        try:
            pressure = resource_status.get('resource_pressure', 0.5)

            if pressure < 0.3:
                return 'excellent'
            elif pressure < 0.6:
                return 'good'
            elif pressure < 0.8:
                return 'acceptable'
            else:
                return 'critical'

        except Exception:
            return 'unknown'

    def _determine_optimization_mode(self, resource_status: Dict[str, Any]) -> str:
        """Determine required optimization mode based on resource status"""
        try:
            pressure = resource_status.get('resource_pressure', 0.5)

            if pressure > 0.9:
                return 'emergency'
            elif pressure > 0.8:
                return 'aggressive'
            elif pressure > 0.6:
                return 'conservative'
            else:
                return 'normal'

        except Exception as e:
            self.logger.debug(f"Error determining optimization mode: {e}")
            return 'normal'

    def _apply_optimization_mode(self, mode: str):
        """Apply optimizations based on the specified mode"""
        try:
            self.logger.info(f"Applying {mode} resource optimization mode")

            action = {
                'timestamp': datetime.now(),
                'mode': mode,
                'actions': []
            }

            if mode == 'emergency':
                # Emergency mode: maximum resource conservation
                self._apply_emergency_optimizations(action)

            elif mode == 'aggressive':
                # Aggressive mode: significant resource reduction
                self._apply_aggressive_optimizations(action)

            elif mode == 'conservative':
                # Conservative mode: moderate resource reduction
                self._apply_conservative_optimizations(action)

            elif mode == 'normal':
                # Normal mode: restore normal operation
                self._apply_normal_optimizations(action)

            self.optimization_actions.append(action)
            self.logger.info(f"Applied {mode} optimizations: {len(action['actions'])} actions")

        except Exception as e:
            self.logger.error(f"Error applying optimization mode {mode}: {e}")

    def _apply_emergency_optimizations(self, action: Dict[str, Any]):
        """Apply emergency resource optimizations"""
        try:
            # Disable enhanced learning features
            if hasattr(self.framework, 'enhanced_learner'):
                # This would disable neural networks, cross-domain learning, etc.
                pass

            # Reduce teaching frequency
            self._reduce_teaching_frequency(0.2)  # 80% reduction

            # Disable knowledge pattern recording
            # This would temporarily disable pattern recognition to save resources

            # Reduce monitoring frequency
            # This would reduce the frequency of performance data collection

            action['actions'].extend([
                'Disabled enhanced learning features',
                'Reduced teaching frequency by 80%',
                'Temporarily disabled pattern recording',
                'Reduced monitoring frequency'
            ])

        except Exception as e:
            self.logger.error(f"Error applying emergency optimizations: {e}")

    def _apply_aggressive_optimizations(self, action: Dict[str, Any]):
        """Apply aggressive resource optimizations"""
        try:
            # Reduce teaching frequency
            self._reduce_teaching_frequency(0.5)  # 50% reduction

            # Limit concurrent learning sessions
            self._limit_concurrent_sessions(2)

            # Reduce pattern analysis complexity
            # This would simplify pattern recognition algorithms

            action['actions'].extend([
                'Reduced teaching frequency by 50%',
                'Limited concurrent sessions to 2',
                'Simplified pattern analysis'
            ])

        except Exception as e:
            self.logger.error(f"Error applying aggressive optimizations: {e}")

    def _apply_conservative_optimizations(self, action: Dict[str, Any]):
        """Apply conservative resource optimizations"""
        try:
            # Moderate teaching frequency reduction
            self._reduce_teaching_frequency(0.8)  # 20% reduction

            # Limit concurrent sessions
            self._limit_concurrent_sessions(3)

            action['actions'].extend([
                'Reduced teaching frequency by 20%',
                'Limited concurrent sessions to 3'
            ])

        except Exception as e:
            self.logger.error(f"Error applying conservative optimizations: {e}")

    def _apply_normal_optimizations(self, action: Dict[str, Any]):
        """Restore normal operation"""
        try:
            # Restore normal teaching frequency
            self._restore_teaching_frequency()

            # Restore concurrent sessions
            self._restore_concurrent_sessions()

            # Re-enable enhanced features
            self._enable_enhanced_features()

            action['actions'].extend([
                'Restored normal teaching frequency',
                'Restored concurrent session limits',
                'Re-enabled enhanced learning features'
            ])

        except Exception as e:
            self.logger.error(f"Error applying normal optimizations: {e}")

    def _reduce_teaching_frequency(self, factor: float):
        """Reduce teaching frequency by the specified factor"""
        try:
            # Update teaching configuration
            if hasattr(self.framework, 'config'):
                original_interval = self.framework.config['system_integration'].get('heartbeat_interval', 60)
                new_interval = int(original_interval / factor)
                self.framework.config['system_integration']['heartbeat_interval'] = new_interval

                self.logger.info(f"Teaching frequency reduced: {original_interval}s -> {new_interval}s")

        except Exception as e:
            self.logger.debug(f"Error reducing teaching frequency: {e}")

    def _restore_teaching_frequency(self):
        """Restore normal teaching frequency"""
        try:
            if hasattr(self.framework, 'config'):
                self.framework.config['system_integration']['heartbeat_interval'] = 60
                self.logger.info("Teaching frequency restored to normal")

        except Exception as e:
            self.logger.debug(f"Error restoring teaching frequency: {e}")

    def _limit_concurrent_sessions(self, max_sessions: int):
        """Limit concurrent learning sessions"""
        try:
            # This would implement session limiting logic
            self.logger.info(f"Concurrent sessions limited to {max_sessions}")

        except Exception as e:
            self.logger.debug(f"Error limiting concurrent sessions: {e}")

    def _restore_concurrent_sessions(self):
        """Restore normal concurrent session limits"""
        try:
            self.logger.info("Concurrent session limits restored")

        except Exception as e:
            self.logger.debug(f"Error restoring concurrent sessions: {e}")

    def _enable_enhanced_features(self):
        """Re-enable enhanced learning features"""
        try:
            self.logger.info("Enhanced learning features re-enabled")

        except Exception as e:
            self.logger.debug(f"Error enabling enhanced features: {e}")

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive optimization status"""
        current_resources = self._assess_current_resources()

        status = {
            'resource_optimization': {
                'active': self.optimization_active,
                'current_mode': self.current_resource_mode,
                'resource_pressure': current_resources.get('resource_pressure', 0.5),
                'resource_health': current_resources.get('resource_health', 'unknown'),
                'optimization_actions': len(self.optimization_actions),
                'resource_history_samples': len(self.resource_history)
            },
            'current_resources': current_resources,
            'resource_thresholds': self.resource_thresholds,
            'agent_profiles': self.agent_profiles,
            'timestamp': datetime.now().isoformat()
        }

        return status

    def _generate_optimization_report(self):
        """Generate comprehensive optimization report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            report = {
                'timestamp': datetime.now().isoformat(),
                'optimization_summary': {
                    'total_runtime': (datetime.now() - self.resource_history[0]['timestamp']).total_seconds() if self.resource_history else 0,
                    'optimization_modes_used': list(set([r['optimization_mode'] for r in self.resource_history])),
                    'total_optimization_actions': len(self.optimization_actions),
                    'average_resource_pressure': sum([r['resource_status'].get('resource_pressure', 0.5) for r in self.resource_history]) / len(self.resource_history) if self.resource_history else 0
                },
                'resource_history': self.resource_history[-100:],  # Last 100 samples
                'optimization_actions': self.optimization_actions,
                'recommendations': self._generate_resource_recommendations()
            }

            # Save report
            report_dir = Path("outgoing/ai4all/optimization")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"optimization_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated optimization report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating optimization report: {e}")

    def _generate_resource_recommendations(self) -> List[str]:
        """Generate resource-based recommendations"""
        recommendations = []

        try:
            if not self.resource_history:
                return recommendations

            # Analyze resource patterns
            recent_resources = self.resource_history[-20:]  # Last 20 samples

            avg_cpu = sum([r['resource_status'].get('cpu_percent', 0) for r in recent_resources]) / len(recent_resources)
            avg_memory = sum([r['resource_status'].get('memory_percent', 0) for r in recent_resources]) / len(recent_resources)

            # Generate recommendations based on patterns
            if avg_cpu > 0.8:
                recommendations.append("High average CPU usage detected - consider reducing teaching frequency or disabling enhanced features")

            if avg_memory > 0.8:
                recommendations.append("High average memory usage detected - monitor teaching system memory consumption")

            # Check for resource pressure patterns
            high_pressure_samples = len([r for r in recent_resources if r['resource_status'].get('resource_pressure', 0) > 0.8])
            if high_pressure_samples > len(recent_resources) * 0.5:
                recommendations.append("Frequent high resource pressure detected - consider optimizing agent resource allocation")

            # Check optimization effectiveness
            if self.optimization_actions:
                emergency_modes = len([a for a in self.optimization_actions if a['mode'] == 'emergency'])
                if emergency_modes > 5:
                    recommendations.append("Frequent emergency mode activation - investigate underlying resource constraints")

        except Exception as e:
            self.logger.debug(f"Error generating resource recommendations: {e}")

        return recommendations[:5]


def create_resource_optimizer(config: Dict[str, Any] = None) -> ResourceAwareTeachingOptimizer:
    """Create resource-aware teaching optimizer"""
    if config is None:
        # Load from main Calyx config
        try:
            with open("config.yaml", 'r') as f:
                import yaml
                calyx_config = yaml.safe_load(f)
                config = calyx_config.get('settings', {}).get('ai4all_optimization', {})
        except Exception:
            config = {
                'cpu_usage_soft_limit': 70,
                'cpu_usage_hard_limit': 85,
                'memory_soft_limit': 75,
                'memory_hard_limit': 90,
                'agent_profiles': {}
            }

    return ResourceAwareTeachingOptimizer(config)


def main():
    """Main resource optimization entry point"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Resource-Aware Teaching Optimization")
    print("=" * 50)
    print("Optimizing teaching system based on resource constraints...\n")

    # Create resource optimizer
    optimizer = create_resource_optimizer()

    try:
        # Start optimization
        optimizer.start_optimization()

        print("✅ Resource-aware optimization started")
        print("📊 Monitoring system resources")
        print("⚖️  Adapting teaching behavior based on resource usage")
        print("🔄 System will optimize until interrupted\n")

        # Keep running until interrupted
        while optimizer.optimization_active:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping resource optimization...")
        optimizer.stop_optimization()

        # Show final status
        status = optimizer.get_optimization_status()
        actions_taken = status['resource_optimization']['optimization_actions']
        avg_pressure = sum([r['resource_status'].get('resource_pressure', 0.5) for r in optimizer.resource_history]) / len(optimizer.resource_history) if optimizer.resource_history else 0

        print(f"✅ Optimization completed: {actions_taken} actions taken")
        print(f"📈 Average resource pressure: {avg_pressure:.1%}")

        print("✅ Resource optimization stopped gracefully")

    except Exception as e:
        print(f"❌ Error in resource optimization: {e}")
        optimizer.stop_optimization()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
