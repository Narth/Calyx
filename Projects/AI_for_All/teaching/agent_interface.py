"""
Agent Teaching Interface - Integration layer for teaching methods with Calyx Terminal agents
"""

import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

import sys
import os

# Add current directory to path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from framework import TeachingFramework, LearningSession
from adaptive_learner import AdaptiveLearner
from performance_tracker import PerformanceTracker


class AgentTeachingInterface:
    """
    Interface for integrating teaching methods with Calyx Terminal agents.
    Provides a bridge between the teaching framework and individual agents.
    """

    def __init__(
        self,
        teaching_framework: TeachingFramework,
        *,
        auto_enable_configured_agents: bool = True,
        load_existing_sessions: bool = True,
    ):
        """
        Initialize the agent teaching interface.

        Args:
            teaching_framework: Instance of the teaching framework
        """
        self.framework = teaching_framework
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Agent-specific teaching state
        self.agent_sessions: Dict[str, str] = {}  # agent_id -> session_id
        self.agent_baselines: Dict[str, Dict[str, float]] = {}
        self.teaching_enabled: Dict[str, bool] = {}

        # Load agent configurations
        self._load_agent_configurations()

        if load_existing_sessions:
            self._load_existing_sessions()

        # Auto-enable teaching for configured agents when requested
        if auto_enable_configured_agents:
            self._auto_enable_configured_agents()

    def _load_agent_configurations(self):
        """Load teaching configurations for different agent types"""
        config_path = Path("config/agent_teaching_configs.json")

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self.agent_configs = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load agent configurations: {e}")
                self.agent_configs = self._get_default_agent_configs()
        else:
            self.agent_configs = self._get_default_agent_configs()

    def _auto_enable_configured_agents(self):
        """Auto-enable teaching for all agents configured for it"""
        for agent_id, config in self.agent_configs.items():
            if config.get('teaching_enabled', False):
                success = self.enable_teaching(agent_id)
                if success:
                    self.logger.info(f"Auto-enabled teaching for {agent_id}")
                else:
                    self.logger.warning(f"Failed to auto-enable teaching for {agent_id}")

    def _load_existing_sessions(self):
        """Populate internal caches from persisted framework sessions."""
        try:
            self.framework.load_existing_sessions()
        except Exception as exc:
            self.logger.warning(f"Failed to load existing sessions: {exc}")
            return

        for session in self.framework.active_sessions.values():
            key = f"{session.agent_id}_{session.learning_objective}"
            self.agent_sessions[key] = session.id
            self.teaching_enabled[session.agent_id] = True
            if session.agent_id not in self.agent_baselines:
                self.agent_baselines[session.agent_id] = session.baseline_metrics.copy()

    def _get_default_agent_configs(self) -> Dict:
        """Default configurations for different agent types"""
        return {
            'agent1': {
                'teaching_enabled': True,
                'learning_objectives': ['task_efficiency', 'stability'],
                'baseline_metrics': {'tes': 85, 'stability': 0.9, 'velocity': 0.5},
                'adaptation_frequency': 300,  # 5 minutes
                'max_sessions': 3
            },
            'triage': {
                'teaching_enabled': True,
                'learning_objectives': ['latency_optimization', 'stability'],
                'baseline_metrics': {'tes': 90, 'stability': 0.95, 'velocity': 0.8},
                'adaptation_frequency': 600,  # 10 minutes
                'max_sessions': 2
            },
            'cp6': {
                'teaching_enabled': True,
                'learning_objectives': ['interaction_efficiency', 'harmony'],
                'baseline_metrics': {'harmony_score': 75, 'interaction_quality': 0.8},
                'adaptation_frequency': 900,  # 15 minutes
                'max_sessions': 2
            },
            'cp7': {
                'teaching_enabled': True,
                'learning_objectives': ['diagnostic_accuracy', 'reporting_efficiency'],
                'baseline_metrics': {'accuracy': 0.9, 'efficiency': 0.85},
                'adaptation_frequency': 1200,  # 20 minutes
                'max_sessions': 2
            }
        }

    def enable_teaching(self, agent_id: str, learning_objectives: List[str] = None) -> bool:
        """
        Enable teaching for a specific agent.

        Args:
            agent_id: Agent identifier
            learning_objectives: List of learning objectives (optional)

        Returns:
            True if teaching was enabled successfully
        """
        if agent_id not in self.agent_configs:
            self.logger.warning(f"No configuration found for agent {agent_id}")
            return False

        config = self.agent_configs[agent_id]

        if not config.get('teaching_enabled', False):
            self.logger.info(f"Teaching not enabled for agent {agent_id}")
            return False

        # Use configured objectives if none specified
        if not learning_objectives:
            learning_objectives = config['learning_objectives']

        self.teaching_enabled[agent_id] = True

        # Establish baselines if not already done
        if agent_id not in self.agent_baselines:
            self.agent_baselines[agent_id] = config['baseline_metrics'].copy()

        # Start learning sessions for each objective
        for objective in learning_objectives:
            baseline = config['baseline_metrics'].copy()

            # Check if we already have an active session for this agent/objective
            existing_session_key = f"{agent_id}_{objective}"
            active_session = None

            for session_id, session in self.framework.active_sessions.items():
                if session.agent_id == agent_id and session.learning_objective == objective:
                    active_session = session
                    break

            if not active_session:
                # Create new learning session
                session = self.framework.create_learning_session(
                    agent_id=agent_id,
                    learning_objective=objective,
                    baseline_metrics=baseline
                )
                self.agent_sessions[f"{agent_id}_{objective}"] = session.id
                self.logger.info(f"Started teaching session {session.id} for {agent_id} on {objective}")
            else:
                self.agent_sessions[f"{agent_id}_{objective}"] = active_session.id
                self.logger.info(f"Resumed teaching session {active_session.id} for {agent_id} on {objective}")

        self.logger.info(f"Teaching enabled for agent {agent_id}")
        return True

    def disable_teaching(self, agent_id: str) -> bool:
        """
        Disable teaching for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if teaching was disabled successfully
        """
        if agent_id not in self.teaching_enabled or not self.teaching_enabled[agent_id]:
            return True  # Already disabled

        # End all active sessions for this agent
        sessions_to_end = []
        for session_key, session_id in self.agent_sessions.items():
            if session_key.startswith(f"{agent_id}_"):
                sessions_to_end.append(session_id)

        for session_id in sessions_to_end:
            if session_id in self.framework.active_sessions:
                session = self.framework.active_sessions[session_id]
                final_metrics = self.agent_baselines.get(agent_id, {})

                self.framework.end_learning_session(session_id, final_metrics)
                self.logger.info(f"Ended teaching session {session_id} for {agent_id}")

        # Clean up agent state
        self.teaching_enabled[agent_id] = False
        for key in list(self.agent_sessions.keys()):
            if key.startswith(f"{agent_id}_"):
                del self.agent_sessions[key]

        self.logger.info(f"Teaching disabled for agent {agent_id}")
        return True

    def update_agent_performance(self, agent_id: str, metrics: Dict[str, float],
                               context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update performance metrics for an agent and trigger teaching adaptations.

        Args:
            agent_id: Agent identifier
            metrics: Current performance metrics
            context: Additional context information

        Returns:
            Dictionary with teaching updates and suggestions
        """
        if agent_id not in self.teaching_enabled or not self.teaching_enabled[agent_id]:
            return {'teaching_enabled': False}

        updates = {
            'teaching_enabled': True,
            'sessions_updated': [],
            'adaptations_applied': [],
            'progress_scores': {}
        }

        # Update all active sessions for this agent
        for session_key, session_id in self.agent_sessions.items():
            if session_key.startswith(f"{agent_id}_") and session_id in self.framework.active_sessions:
                session = self.framework.active_sessions[session_id]

                # Record performance in tracker
                self.framework.performance_tracker.record_performance(
                    agent_id=agent_id,
                    metrics=metrics,
                    context=context,
                    session_id=session_id
                )

                # Update learning progress
                adaptation_applied = None
                progress_score = self.framework.update_learning_progress(
                    session_id=session_id,
                    current_metrics=metrics,
                    adaptation_applied=adaptation_applied
                )

                updates['sessions_updated'].append(session_id)
                updates['progress_scores'][session.learning_objective] = progress_score

                # Check if adaptation is needed
                adaptation_suggestion = self.framework.adaptive_learner.suggest_adaptation(
                    agent_id=agent_id,
                    learning_objective=session.learning_objective,
                    current_metrics=metrics,
                    baseline_metrics=session.baseline_metrics
                )

                if adaptation_suggestion:
                    updates['adaptations_applied'].append({
                        'session_id': session_id,
                        'objective': session.learning_objective,
                        'adaptation': adaptation_suggestion
                    })

        # Record in knowledge integrator if this is a successful pattern
        if self._is_successful_performance(metrics, agent_id):
            self.framework.knowledge_integrator.record_successful_pattern(
                agent_id=agent_id,
                pattern_type='success',
                description=f"Agent {agent_id} achieved good performance metrics",
                metrics_impact=metrics,
                context=context or {},
                confidence=self._calculate_confidence(metrics, agent_id)
            )

        # Record in pattern recognition system
        self.framework.pattern_recognition.observe_behavior(
            agent_id=agent_id,
            behavior_data={'performance_update': metrics},
            context=context,
            performance_metrics=metrics
        )

        return updates

    def _is_successful_performance(self, metrics: Dict[str, float], agent_id: str) -> bool:
        """Determine if current performance indicates a successful pattern"""
        if agent_id not in self.agent_baselines:
            return False

        baseline = self.agent_baselines[agent_id]

        # Check if metrics exceed baseline thresholds
        success_thresholds = {
            'tes': 0.05,  # 5% improvement
            'stability': 0.03,  # 3% improvement
            'velocity': 0.1,  # 10% improvement
            'error_rate': -0.05  # 5% reduction
        }

        success_count = 0
        total_metrics = 0

        for metric, threshold in success_thresholds.items():
            if metric in metrics and metric in baseline:
                current = metrics[metric]
                base = baseline[metric]

                if metric == 'error_rate':
                    # Lower is better for error rate
                    if base - current >= abs(threshold):
                        success_count += 1
                else:
                    # Higher is better for other metrics
                    if current - base >= threshold:
                        success_count += 1

                total_metrics += 1

        return (success_count / total_metrics) >= 0.7 if total_metrics > 0 else False

    def _calculate_confidence(self, metrics: Dict[str, float], agent_id: str) -> float:
        """Calculate confidence in the success pattern"""
        if agent_id not in self.agent_baselines:
            return 0.5

        baseline = self.agent_baselines[agent_id]
        confidence_factors = []

        for metric in ['tes', 'stability', 'velocity']:
            if metric in metrics and metric in baseline:
                current = metrics[metric]
                base = baseline[metric]

                improvement = (current - base) / base if base > 0 else 0
                # Confidence increases with improvement up to a point
                confidence = min(1.0, improvement * 2)  # 50% improvement = 100% confidence
                confidence_factors.append(confidence)

        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5

    def get_agent_teaching_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get comprehensive teaching status for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with teaching status and progress
        """
        if agent_id not in self.teaching_enabled:
            return {'teaching_enabled': False, 'reason': 'Agent not configured for teaching'}

        status = {
            'teaching_enabled': self.teaching_enabled[agent_id],
            'agent_config': self.agent_configs.get(agent_id, {}),
            'active_sessions': [],
            'baselines': self.agent_baselines.get(agent_id, {}),
            'progress_summary': {},
            'adaptations': {},
            'knowledge_patterns': [],
            'performance_trends': []
        }

        # Get active sessions
        for session_key, session_id in self.agent_sessions.items():
            if session_key.startswith(f"{agent_id}_") and session_id in self.framework.active_sessions:
                session = self.framework.active_sessions[session_id]
                session_data = self.framework.get_learning_progress(session_id)

                if session_data:
                    status['active_sessions'].append(session_data)

        # Get performance trends
        performance_data = self.framework.performance_tracker.get_agent_performance(agent_id)
        if 'trends' in performance_data:
            status['performance_trends'] = performance_data['trends']

        # Get knowledge patterns
        patterns = self.framework.pattern_recognition.get_strong_patterns(agent_id)
        status['knowledge_patterns'] = patterns

        # Get adaptations
        adaptations = self.framework.adaptive_learner.get_adaptation_history(agent_id)
        status['adaptations'] = adaptations

        # Calculate progress summary
        total_progress = 0.0
        session_count = 0

        for session_data in status['active_sessions']:
            if 'session' in session_data:
                progress = session_data['session']['progress_score']
                total_progress += progress
                session_count += 1

        if session_count > 0:
            status['progress_summary'] = {
                'average_progress': total_progress / session_count,
                'session_count': session_count,
                'overall_status': 'excellent' if (total_progress / session_count) > 0.8
                               else 'good' if (total_progress / session_count) > 0.6
                               else 'improving' if (total_progress / session_count) > 0.3
                               else 'needs_attention'
            }

        return status

    def get_teaching_recommendations(self, agent_id: str) -> List[str]:
        """
        Get teaching recommendations for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if agent_id not in self.teaching_enabled or not self.teaching_enabled[agent_id]:
            recommendations.append(f"Enable teaching for {agent_id} to improve performance")
            return recommendations

        # Get current status
        status = self.get_agent_teaching_status(agent_id)

        # Analyze progress and make recommendations
        if status['progress_summary'].get('overall_status') == 'needs_attention':
            recommendations.append("Consider adjusting learning objectives or baseline metrics")

        # Check for transferable patterns
        transferable_patterns = self.framework.knowledge_integrator.find_transferable_patterns(
            agent_id, status.get('baselines', {})
        )

        if transferable_patterns:
            recommendations.append(f"Found {len(transferable_patterns)} transferable patterns from other agents")

        # Check adaptation effectiveness
        adaptations = status.get('adaptations', [])
        if adaptations:
            successful_adaptations = len([a for a in adaptations if a.get('success', False)])
            if successful_adaptations / len(adaptations) < 0.5:
                recommendations.append("Review adaptation strategy - low success rate")

        # Performance-based recommendations
        if status['performance_trends']:
            for trend in status['performance_trends']:
                if trend['trend_direction'] == 'declining':
                    recommendations.append(f"Address declining {trend['metric_name']} trend")

        return recommendations

    def emit_teaching_heartbeat(self):
        """Emit teaching heartbeat for system monitoring"""
        heartbeat = {
            'name': 'ai4all_teaching_interface',
            'status': 'running',
            'agents_with_teaching': list(self.teaching_enabled.keys()),
            'active_sessions': len(self.framework.active_sessions),
            'total_patterns': len(self.framework.pattern_recognition.patterns),
            'timestamp': datetime.now().isoformat()
        }

        heartbeat_file = Path("outgoing/ai4all/teaching_heartbeat.json")
        with open(heartbeat_file, 'w') as f:
            json.dump(heartbeat, f, indent=2, default=str)

        # Also emit through the framework
        self.framework.emit_heartbeat()

    def get_system_overview(self) -> Dict[str, Any]:
        """Get overview of teaching system status"""
        overview = {
            'teaching_framework': self.framework.get_system_status(),
            'agent_interface': {
                'agents_configured': len(self.agent_configs),
                'agents_with_teaching_enabled': len([a for a in self.teaching_enabled.values() if a]),
                'active_sessions': len(self.framework.active_sessions),
                'total_patterns': len(self.framework.pattern_recognition.patterns),
                'knowledge_transfers': len(self.framework.knowledge_integrator.transfers)
            },
            'performance_summary': {},
            'recommendations': []
        }

        # Calculate system-wide performance summary
        all_agents = set(self.agent_configs.keys())
        total_progress = 0.0
        agent_count = 0

        for agent_id in all_agents:
            if self.teaching_enabled.get(agent_id, False):
                status = self.get_agent_teaching_status(agent_id)
                progress = status['progress_summary'].get('average_progress', 0.0)
                if progress > 0:
                    total_progress += progress
                    agent_count += 1

        if agent_count > 0:
            overview['performance_summary'] = {
                'system_average_progress': total_progress / agent_count,
                'agents_reporting_progress': agent_count,
                'system_health': 'excellent' if (total_progress / agent_count) > 0.8
                               else 'good' if (total_progress / agent_count) > 0.6
                               else 'needs_improvement'
            }

        return overview

