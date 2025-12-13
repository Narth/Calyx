"""
Adaptive Learner - Dynamic learning parameter adjustment for AI-for-All
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from gpu_accelerator import GPUAccelerator


@dataclass
class LearningParameters:
    """Learning parameters that can be adapted"""
    learning_rate: float = 0.1
    momentum: float = 0.9
    decay_rate: float = 0.95
    exploration_factor: float = 0.1
    stability_weight: float = 0.7
    efficiency_weight: float = 0.3
    adaptation_sensitivity: float = 0.05

    def to_dict(self) -> dict:
        return {
            'learning_rate': self.learning_rate,
            'momentum': self.momentum,
            'decay_rate': self.decay_rate,
            'exploration_factor': self.exploration_factor,
            'stability_weight': self.stability_weight,
            'efficiency_weight': self.efficiency_weight,
            'adaptation_sensitivity': self.adaptation_sensitivity
        }


@dataclass
class AdaptationSuggestion:
    """Suggested adaptation for learning parameters"""
    parameter_name: str
    current_value: float
    suggested_value: float
    confidence: float
    reasoning: str
    risk_level: str  # 'low', 'medium', 'high'

    def to_dict(self) -> dict:
        return {
            'parameter_name': self.parameter_name,
            'current_value': self.current_value,
            'suggested_value': self.suggested_value,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'risk_level': self.risk_level
        }


class AdaptiveLearner:
    """
    Implements adaptive learning algorithms that dynamically adjust teaching
    parameters based on agent performance and learning progress.
    """

    def __init__(self, config: dict):
        """
        Initialize the adaptive learner.

        Args:
            config: Configuration dictionary for adaptive learning
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize GPU accelerator if enabled
        gpu_config = config.get('gpu_acceleration', {})
        self.gpu_enabled = gpu_config.get('enabled', False)
        
        if self.gpu_enabled:
            self.gpu_accelerator = GPUAccelerator(gpu_config)
            self.logger.info(f"GPU acceleration initialized: {self.gpu_accelerator.get_status()}")
        else:
            self.gpu_accelerator = None
            self.logger.info("GPU acceleration disabled")

        # Learning parameter templates for different objectives
        self.parameter_templates = {
            'task_efficiency': LearningParameters(
                learning_rate=0.15,
                momentum=0.85,
                efficiency_weight=0.5,
                stability_weight=0.5
            ),
            'stability': LearningParameters(
                learning_rate=0.05,
                momentum=0.95,
                stability_weight=0.8,
                efficiency_weight=0.2
            ),
            'latency_optimization': LearningParameters(
                learning_rate=0.12,
                exploration_factor=0.15,
                efficiency_weight=0.6,
                stability_weight=0.4
            ),
            'error_reduction': LearningParameters(
                learning_rate=0.08,
                decay_rate=0.98,
                stability_weight=0.9,
                efficiency_weight=0.1
            )
        }

        # Performance history for adaptation decisions
        self.performance_history: Dict[str, List[Dict]] = {}
        self.adaptation_history: Dict[str, List[AdaptationSuggestion]] = {}

        # Safety constraints
        self.safety_constraints = {
            'learning_rate': {'min': 0.001, 'max': 0.5},
            'momentum': {'min': 0.5, 'max': 0.99},
            'exploration_factor': {'min': 0.01, 'max': 0.3},
            'adaptation_sensitivity': {'min': 0.01, 'max': 0.2}
        }

    def suggest_adaptation(self, agent_id: str, learning_objective: str,
                          current_metrics: Dict[str, float],
                          baseline_metrics: Dict[str, float]) -> Optional[str]:
        """
        Suggest adaptation based on current performance vs baseline.

        Args:
            agent_id: Agent identifier
            learning_objective: Learning objective being pursued
            current_metrics: Current performance metrics
            baseline_metrics: Baseline performance metrics

        Returns:
            Description of adaptation applied, or None if no adaptation needed
        """
        # Update performance history
        self._update_performance_history(agent_id, current_metrics)

        # Analyze performance trends
        trends = self._analyze_performance_trends(agent_id)

        # Generate adaptation suggestions
        suggestions = self._generate_adaptations(agent_id, learning_objective, trends, current_metrics, baseline_metrics)

        if not suggestions:
            return None

        # Apply the highest confidence, lowest risk suggestion
        best_suggestion = self._select_best_adaptation(suggestions)

        if best_suggestion.confidence > 0.6:  # Confidence threshold
            adaptation_result = self._apply_adaptation(agent_id, learning_objective, best_suggestion)

            # Record adaptation in history
            if agent_id not in self.adaptation_history:
                self.adaptation_history[agent_id] = []
            self.adaptation_history[agent_id].append(best_suggestion)

            self.logger.info(f"Applied adaptation for {agent_id}: {best_suggestion.parameter_name} "
                           f"{best_suggestion.current_value:.3f} -> {best_suggestion.suggested_value:.3f}")
            return adaptation_result

        return None

    def _update_performance_history(self, agent_id: str, metrics: Dict[str, float]):
        """Update performance history for trend analysis"""
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []

        # Keep only recent history (last 50 entries)
        history_entry = {
            'timestamp': datetime.now(),
            'metrics': metrics.copy()
        }

        self.performance_history[agent_id].append(history_entry)

        if len(self.performance_history[agent_id]) > 50:
            self.performance_history[agent_id] = self.performance_history[agent_id][-50:]

    def _analyze_performance_trends(self, agent_id: str) -> Dict[str, str]:
        """Analyze performance trends to inform adaptation decisions"""
        if agent_id not in self.performance_history or len(self.performance_history[agent_id]) < 5:
            return {'trend': 'insufficient_data'}

        recent = self.performance_history[agent_id][-5:]
        older = self.performance_history[agent_id][-10:-5] if len(self.performance_history[agent_id]) >= 10 else recent

        trends = {}

        for metric in ['tes', 'stability', 'velocity', 'error_rate']:
            if metric in recent[0]['metrics']:
                recent_avg = sum([entry['metrics'].get(metric, 0) for entry in recent]) / len(recent)
                older_avg = sum([entry['metrics'].get(metric, 0) for entry in older]) / len(older)

                if recent_avg > older_avg * 1.05:
                    trends[metric] = 'improving'
                elif recent_avg < older_avg * 0.95:
                    trends[metric] = 'declining'
                else:
                    trends[metric] = 'stable'

        return trends

    def _generate_adaptations(self, agent_id: str, learning_objective: str,
                            trends: Dict[str, str], current_metrics: Dict[str, float],
                            baseline_metrics: Dict[str, float]) -> List[AdaptationSuggestion]:
        """Generate adaptation suggestions based on performance analysis"""
        suggestions = []

        # Get current parameters
        current_params = self._get_current_parameters(agent_id, learning_objective)

        # Use GPU-accelerated adaptation calculation if available
        if self.gpu_accelerator and self.gpu_enabled:
            try:
                # Prepare performance history
                performance_history = []
                if agent_id in self.performance_history:
                    performance_history = self.performance_history[agent_id]
                
                # Get GPU-accelerated parameters
                gpu_result = self.gpu_accelerator.accelerate_adaptation_calculation(
                    performance_history, baseline_metrics
                )
                
                # Override improvement rate from GPU calculation
                improvement_rate = gpu_result.get('improvement_rate', 0.0)
                
                # Use GPU-calculated learning rate and momentum
                if improvement_rate < 0.05:
                    suggestions.append(AdaptationSuggestion(
                        parameter_name='learning_rate',
                        current_value=current_params.learning_rate,
                        suggested_value=gpu_result.get('learning_rate', current_params.learning_rate),
                        confidence=0.75,
                        reasoning='GPU-accelerated adaptation: low improvement rate',
                        risk_level='low'
                    ))
                
                self.logger.debug(f"GPU-accelerated adaptation calculation completed")
                
            except Exception as e:
                self.logger.warning(f"GPU adaptation generation failed: {e}, falling back to CPU")
                improvement_rate = self._calculate_improvement_rate(current_metrics, baseline_metrics)
        else:
            # CPU-based improvement rate calculation
            improvement_rate = self._calculate_improvement_rate(current_metrics, baseline_metrics)

        if improvement_rate < 0.05:  # Less than 5% improvement
            # Increase learning rate to speed up learning
            if current_params.learning_rate < self.safety_constraints['learning_rate']['max']:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='learning_rate',
                    current_value=current_params.learning_rate,
                    suggested_value=min(current_params.learning_rate * 1.2,
                                      self.safety_constraints['learning_rate']['max']),
                    confidence=0.7,
                    reasoning='Low improvement rate detected, increasing learning rate',
                    risk_level='low'
                ))

            # Increase exploration for better pattern discovery
            if current_params.exploration_factor < self.safety_constraints['exploration_factor']['max']:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='exploration_factor',
                    current_value=current_params.exploration_factor,
                    suggested_value=min(current_params.exploration_factor * 1.15,
                                      self.safety_constraints['exploration_factor']['max']),
                    confidence=0.6,
                    reasoning='Increasing exploration to discover better patterns',
                    risk_level='medium'
                ))

        elif improvement_rate > 0.2:  # More than 20% improvement
            # Decrease learning rate for fine-tuning
            if current_params.learning_rate > self.safety_constraints['learning_rate']['min']:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='learning_rate',
                    current_value=current_params.learning_rate,
                    suggested_value=max(current_params.learning_rate * 0.9,
                                      self.safety_constraints['learning_rate']['min']),
                    confidence=0.8,
                    reasoning='Good improvement rate, fine-tuning with lower learning rate',
                    risk_level='low'
                ))

        # Stability-based adaptations
        if trends.get('stability') == 'declining':
            # Increase stability weight and decrease exploration
            if current_params.stability_weight < 0.9:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='stability_weight',
                    current_value=current_params.stability_weight,
                    suggested_value=min(current_params.stability_weight * 1.1, 0.9),
                    confidence=0.8,
                    reasoning='Stability declining, prioritizing stability over efficiency',
                    risk_level='low'
                ))

            if current_params.exploration_factor > self.safety_constraints['exploration_factor']['min']:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='exploration_factor',
                    current_value=current_params.exploration_factor,
                    suggested_value=max(current_params.exploration_factor * 0.8,
                                      self.safety_constraints['exploration_factor']['min']),
                    confidence=0.7,
                    reasoning='Reducing exploration to improve stability',
                    risk_level='low'
                ))

        # Efficiency-based adaptations
        if trends.get('velocity') == 'declining' and trends.get('stability') != 'declining':
            # Increase efficiency weight
            if current_params.efficiency_weight < 0.7:
                suggestions.append(AdaptationSuggestion(
                    parameter_name='efficiency_weight',
                    current_value=current_params.efficiency_weight,
                    suggested_value=min(current_params.efficiency_weight * 1.15, 0.7),
                    confidence=0.6,
                    reasoning='Velocity declining, prioritizing efficiency improvements',
                    risk_level='medium'
                ))

        return suggestions

    def _calculate_improvement_rate(self, current_metrics: Dict[str, float],
                                  baseline_metrics: Dict[str, float]) -> float:
        """Calculate overall improvement rate from baseline"""
        # Use GPU acceleration if available
        if self.gpu_accelerator and self.gpu_enabled:
            try:
                # Pack metrics for GPU analysis
                metrics_data = {**current_metrics}
                result = self.gpu_accelerator.accelerate_performance_analysis(metrics_data)
                
                # Use composite score for improvement rate estimation
                return result.get('composite_score', 0.0) / 100.0
            except Exception as e:
                self.logger.warning(f"GPU improvement calculation failed: {e}, falling back to CPU")
        
        # CPU fallback
        total_improvement = 0.0
        metric_count = 0

        for metric in ['tes', 'stability', 'velocity']:
            if metric in current_metrics and metric in baseline_metrics:
                current = current_metrics[metric]
                baseline = baseline_metrics[metric]

                if baseline > 0:
                    improvement = (current - baseline) / baseline
                    total_improvement += max(0, improvement)  # Only count positive improvements
                    metric_count += 1

        # For error_rate (lower is better)
        if 'error_rate' in current_metrics and 'error_rate' in baseline_metrics:
            current = current_metrics['error_rate']
            baseline = baseline_metrics['error_rate']

            if baseline > 0:
                improvement = (baseline - current) / baseline
                total_improvement += max(0, improvement)
                metric_count += 1

        return total_improvement / metric_count if metric_count > 0 else 0.0

    def _get_current_parameters(self, agent_id: str, learning_objective: str) -> LearningParameters:
        """Get current learning parameters for an agent and objective"""
        # Check if we have recorded parameters for this agent
        param_key = f"{agent_id}_{learning_objective}"

        # For now, return template parameters
        # In a full implementation, this would load from persistent storage
        return self.parameter_templates.get(learning_objective,
                                          self.parameter_templates['task_efficiency'])

    def _select_best_adaptation(self, suggestions: List[AdaptationSuggestion]) -> AdaptationSuggestion:
        """Select the best adaptation from multiple suggestions"""
        # Sort by confidence (descending) then by risk level (ascending)
        risk_priority = {'low': 1, 'medium': 2, 'high': 3}

        def sort_key(suggestion):
            return (-suggestion.confidence, risk_priority.get(suggestion.risk_level, 4))

        suggestions.sort(key=sort_key)
        return suggestions[0] if suggestions else None

    def _apply_adaptation(self, agent_id: str, learning_objective: str,
                         suggestion: AdaptationSuggestion) -> str:
        """Apply the suggested adaptation and return description"""
        # In a full implementation, this would update persistent parameter storage
        # For now, just return a description of what was changed

        return (f"Adapted {suggestion.parameter_name} from {suggestion.current_value:.3f} "
                f"to {suggestion.suggested_value:.3f} ({suggestion.reasoning})")

    def get_learning_parameters(self, agent_id: str, learning_objective: str) -> Dict[str, float]:
        """Get current learning parameters for an agent"""
        params = self._get_current_parameters(agent_id, learning_objective)
        return params.to_dict()

    def get_adaptation_history(self, agent_id: str) -> List[Dict]:
        """Get adaptation history for an agent"""
        if agent_id not in self.adaptation_history:
            return []

        return [suggestion.to_dict() for suggestion in self.adaptation_history[agent_id]]

    def reset_adaptations(self, agent_id: str, learning_objective: str):
        """Reset adaptations for a specific agent and objective"""
        param_key = f"{agent_id}_{learning_objective}"

        # Remove from history
        if agent_id in self.adaptation_history:
            self.adaptation_history[agent_id] = [
                s for s in self.adaptation_history[agent_id]
                if s.parameter_name != param_key
            ]

        self.logger.info(f"Reset adaptations for {agent_id} on {learning_objective}")
