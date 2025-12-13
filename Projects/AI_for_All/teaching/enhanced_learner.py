"""
Enhanced Learner - Advanced learning algorithms for AI-for-All based on dry run results
"""

import json
import logging
import statistics
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

import sys
import os

# Add current directory to path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adaptive_learner import AdaptiveLearner, LearningParameters, AdaptationSuggestion


@dataclass
class EnhancedLearningParameters(LearningParameters):
    """Enhanced learning parameters with additional optimization features"""
    predictive_horizon: int = 5  # Number of cycles to predict ahead
    cross_domain_weight: float = 0.1  # Weight for cross-domain learning
    neural_network_enabled: bool = False  # Enable neural network learning
    memory_retention: float = 0.9  # How much to retain from previous learning
    adaptation_aggressiveness: float = 0.5  # How aggressively to adapt (0.1-1.0)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


@dataclass
class LearningTrajectory:
    """Tracks learning trajectory for enhanced adaptation"""
    agent_id: str
    objective: str
    trajectory_points: List[Tuple[datetime, float]]  # (timestamp, performance)
    trend_direction: str
    trend_strength: float
    confidence: float
    prediction_horizon: int

    def to_dict(self) -> dict:
        return {
            'agent_id': self.agent_id,
            'objective': self.objective,
            'trajectory_points': [(pt[0].isoformat(), pt[1]) for pt in self.trajectory_points],
            'trend_direction': self.trend_direction,
            'trend_strength': self.trend_strength,
            'confidence': self.confidence,
            'prediction_horizon': self.prediction_horizon
        }


@dataclass
class CrossDomainPattern:
    """Pattern that works across multiple agent types or objectives"""
    pattern_id: str
    source_domain: str  # Original domain where pattern was learned
    target_domains: List[str]  # Domains where pattern can be applied
    effectiveness_score: Dict[str, float]  # Effectiveness in each domain
    adaptation_requirements: Dict[str, Dict[str, Any]]  # How to adapt for each domain
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


class EnhancedAdaptiveLearner(AdaptiveLearner):
    """
    Enhanced adaptive learning with advanced features based on dry run results.
    Includes predictive optimization, cross-domain learning, and neural network integration.
    """

    def __init__(self, config: dict):
        """
        Initialize enhanced adaptive learner.

        Args:
            config: Enhanced configuration dictionary
        """
        super().__init__(config)

        # Enhanced learning features
        self.learning_trajectories: Dict[str, LearningTrajectory] = {}
        self.cross_domain_patterns: Dict[str, CrossDomainPattern] = {}
        self.predictive_models: Dict[str, Any] = {}

        # Enhanced parameters
        self.enhanced_params = EnhancedLearningParameters(
            predictive_horizon=config.get('predictive_horizon', 5),
            cross_domain_weight=config.get('cross_domain_weight', 0.1),
            neural_network_enabled=config.get('neural_network_enabled', False),
            memory_retention=config.get('memory_retention', 0.9),
            adaptation_aggressiveness=config.get('adaptation_aggressiveness', 0.5)
        )

        # Performance prediction
        self.prediction_history: Dict[str, List[float]] = {}
        self.adaptation_effectiveness: Dict[str, List[float]] = {}

        self.logger.info("Enhanced adaptive learner initialized")

    def suggest_enhanced_adaptation(self, agent_id: str, learning_objective: str,
                                  current_metrics: Dict[str, float],
                                  baseline_metrics: Dict[str, float],
                                  performance_history: List[Dict[str, float]] = None) -> List[AdaptationSuggestion]:
        """
        Suggest enhanced adaptations based on comprehensive analysis.

        Args:
            agent_id: Agent identifier
            learning_objective: Learning objective
            current_metrics: Current performance metrics
            baseline_metrics: Baseline performance metrics
            performance_history: Historical performance data

        Returns:
            List of adaptation suggestions
        """
        suggestions = []

        # Basic adaptation suggestions (from parent class)
        basic_suggestions = super().suggest_adaptation(
            agent_id, learning_objective, current_metrics, baseline_metrics
        )

        if basic_suggestions:
            suggestions.extend(self._enhance_basic_suggestions(basic_suggestions, performance_history))

        # Enhanced suggestions based on learning trajectories
        trajectory_suggestions = self._generate_trajectory_based_suggestions(
            agent_id, learning_objective, current_metrics, performance_history
        )
        suggestions.extend(trajectory_suggestions)

        # Cross-domain learning suggestions
        cross_domain_suggestions = self._generate_cross_domain_suggestions(
            agent_id, learning_objective, current_metrics
        )
        suggestions.extend(cross_domain_suggestions)

        # Predictive optimization suggestions
        predictive_suggestions = self._generate_predictive_suggestions(
            agent_id, learning_objective, current_metrics, performance_history
        )
        suggestions.extend(predictive_suggestions)

        # Sort by confidence and risk
        suggestions = self._rank_suggestions(suggestions)

        return suggestions[:5]  # Return top 5 suggestions

    def _enhance_basic_suggestions(self, basic_suggestions: List[AdaptationSuggestion],
                                 performance_history: List[Dict[str, float]] = None) -> List[AdaptationSuggestion]:
        """Enhance basic suggestions with historical context"""
        enhanced_suggestions = []

        for suggestion in basic_suggestions:
            enhanced = AdaptationSuggestion(
                parameter_name=suggestion.parameter_name,
                current_value=suggestion.current_value,
                suggested_value=suggestion.suggested_value,
                confidence=suggestion.confidence,
                reasoning=f"Enhanced: {suggestion.reasoning}",
                risk_level=suggestion.risk_level
            )

            # Adjust confidence based on historical effectiveness
            if performance_history and len(performance_history) >= 3:
                historical_effectiveness = self._calculate_historical_effectiveness(
                    suggestion.parameter_name, performance_history
                )
                enhanced.confidence = min(1.0, suggestion.confidence * historical_effectiveness)

            enhanced_suggestions.append(enhanced)

        return enhanced_suggestions

    def _calculate_historical_effectiveness(self, parameter_name: str,
                                          performance_history: List[Dict[str, float]]) -> float:
        """Calculate how effective a parameter adjustment has been historically"""
        if len(performance_history) < 3:
            return 0.5  # Neutral effectiveness for insufficient data

        # Simple trend analysis
        recent_performance = performance_history[-3:]
        older_performance = performance_history[-6:-3] if len(performance_history) >= 6 else recent_performance

        # Calculate average performance improvement
        recent_avg = statistics.mean([
            sum(metrics.values()) / len(metrics) for metrics in recent_performance
        ])
        older_avg = statistics.mean([
            sum(metrics.values()) / len(metrics) for metrics in older_performance
        ])

        improvement = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

        # Convert improvement to effectiveness score (0.1 to 1.0)
        effectiveness = max(0.1, min(1.0, 0.5 + improvement))
        return effectiveness

    def _generate_trajectory_based_suggestions(self, agent_id: str, learning_objective: str,
                                            current_metrics: Dict[str, float],
                                            performance_history: List[Dict[str, float]] = None) -> List[AdaptationSuggestion]:
        """Generate suggestions based on learning trajectories"""
        suggestions = []

        if not performance_history or len(performance_history) < 5:
            return suggestions

        # Analyze learning trajectory
        trajectory_key = f"{agent_id}_{learning_objective}"
        if trajectory_key not in self.learning_trajectories:
            self._update_learning_trajectory(agent_id, learning_objective, performance_history)

        trajectory = self.learning_trajectories.get(trajectory_key)
        if not trajectory:
            return suggestions

        # Generate trajectory-based suggestions
        if trajectory.trend_direction == 'declining' and trajectory.confidence > 0.7:
            # Suggest more aggressive adaptation for declining performance
            suggestions.append(AdaptationSuggestion(
                parameter_name='learning_rate',
                current_value=self._get_current_parameters(agent_id, learning_objective).learning_rate,
                suggested_value=self._get_current_parameters(agent_id, learning_objective).learning_rate * 1.3,
                confidence=trajectory.confidence,
                reasoning=f"Trajectory analysis shows declining performance, increasing adaptation aggressiveness",
                risk_level='medium'
            ))

        elif trajectory.trend_direction == 'improving' and trajectory.trend_strength > 0.8:
            # Suggest fine-tuning for strongly improving performance
            suggestions.append(AdaptationSuggestion(
                parameter_name='learning_rate',
                current_value=self._get_current_parameters(agent_id, learning_objective).learning_rate,
                suggested_value=self._get_current_parameters(agent_id, learning_objective).learning_rate * 0.8,
                confidence=trajectory.confidence,
                reasoning=f"Strong improvement trajectory detected, fine-tuning learning parameters",
                risk_level='low'
            ))

        return suggestions

    def _generate_cross_domain_suggestions(self, agent_id: str, learning_objective: str,
                                        current_metrics: Dict[str, float]) -> List[AdaptationSuggestion]:
        """Generate suggestions based on cross-domain learning"""
        suggestions = []

        # Find patterns that might apply to this agent from other domains
        applicable_patterns = []
        for pattern_id, pattern in self.cross_domain_patterns.items():
            if (learning_objective in pattern.target_domains and
                pattern.effectiveness_score.get(learning_objective, 0) > 0.7):
                applicable_patterns.append(pattern)

        for pattern in applicable_patterns[:2]:  # Top 2 cross-domain patterns
            # Suggest adaptation based on cross-domain pattern
            adaptation = pattern.adaptation_requirements.get(learning_objective, {})

            for param_name, param_adaptation in adaptation.items():
                suggestions.append(AdaptationSuggestion(
                    parameter_name=param_name,
                    current_value=self._get_current_parameters(agent_id, learning_objective).__dict__.get(param_name, 0),
                    suggested_value=param_adaptation.get('target_value', 0),
                    confidence=pattern.confidence * 0.8,  # Slightly lower confidence for cross-domain
                    reasoning=f"Cross-domain pattern from {pattern.source_domain}: {param_adaptation.get('reasoning', 'Pattern transfer')}",
                    risk_level='medium'
                ))

        return suggestions

    def _generate_predictive_suggestions(self, agent_id: str, learning_objective: str,
                                       current_metrics: Dict[str, float],
                                       performance_history: List[Dict[str, float]] = None) -> List[AdaptationSuggestion]:
        """Generate suggestions based on performance prediction"""
        suggestions = []

        if not performance_history or len(performance_history) < 5:
            return suggestions

        # Predict future performance
        prediction = self._predict_performance(agent_id, learning_objective, performance_history)

        if prediction.get('will_decline', False) and prediction.get('confidence', 0) > 0.6:
            # Suggest proactive adaptation to prevent decline
            suggestions.append(AdaptationSuggestion(
                parameter_name='adaptation_sensitivity',
                current_value=self._get_current_parameters(agent_id, learning_objective).adaptation_sensitivity,
                suggested_value=min(0.2, self._get_current_parameters(agent_id, learning_objective).adaptation_sensitivity * 1.2),
                confidence=prediction['confidence'],
                reasoning=f"Predictive analysis indicates potential decline, increasing adaptation sensitivity",
                risk_level='low'
            ))

        elif prediction.get('will_improve', False) and prediction.get('confidence', 0) > 0.8:
            # Suggest optimization for predicted improvement
            suggestions.append(AdaptationSuggestion(
                parameter_name='memory_retention',
                current_value=self.enhanced_params.memory_retention,
                suggested_value=min(0.95, self.enhanced_params.memory_retention * 1.05),
                confidence=prediction['confidence'],
                reasoning=f"Predictive analysis indicates improvement trend, enhancing memory retention",
                risk_level='low'
            ))

        return suggestions

    def _predict_performance(self, agent_id: str, learning_objective: str,
                           performance_history: List[Dict[str, float]]) -> Dict[str, Any]:
        """Predict future performance based on historical trends"""
        if len(performance_history) < 5:
            return {'confidence': 0, 'prediction': 'insufficient_data'}

        # Simple linear regression for trend prediction
        recent_performance = [sum(metrics.values()) / len(metrics) for metrics in performance_history[-5:]]
        older_performance = [sum(metrics.values()) / len(metrics) for metrics in performance_history[-10:-5]] if len(performance_history) >= 10 else recent_performance

        # Calculate trend
        recent_avg = statistics.mean(recent_performance)
        older_avg = statistics.mean(older_performance)

        trend_strength = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

        # Predict next 3 cycles
        prediction_confidence = min(0.9, len(performance_history) / 20.0)  # More data = higher confidence

        predicted_next = recent_avg + (trend_strength * recent_avg)

        return {
            'current_performance': recent_avg,
            'trend_strength': trend_strength,
            'predicted_next': predicted_next,
            'will_improve': trend_strength > 0.05,
            'will_decline': trend_strength < -0.05,
            'will_stabilize': abs(trend_strength) <= 0.05,
            'confidence': prediction_confidence
        }

    def _update_learning_trajectory(self, agent_id: str, learning_objective: str,
                                  performance_history: List[Dict[str, float]]):
        """Update learning trajectory for an agent"""
        if len(performance_history) < 3:
            return

        # Calculate trajectory points
        trajectory_points = []
        for i, metrics in enumerate(performance_history[-10:]):  # Last 10 data points
            avg_performance = sum(metrics.values()) / len(metrics)
            trajectory_points.append((datetime.now() - timedelta(minutes=i*5), avg_performance))

        # Analyze trend
        if len(trajectory_points) >= 3:
            recent = [pt[1] for pt in trajectory_points[-3:]]
            older = [pt[1] for pt in trajectory_points[-6:-3]] if len(trajectory_points) >= 6 else recent

            recent_avg = statistics.mean(recent)
            older_avg = statistics.mean(older)

            trend_strength = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0

            if trend_strength > 0.02:
                trend_direction = 'improving'
            elif trend_strength < -0.02:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'

            confidence = min(1.0, len(trajectory_points) / 10.0)

            trajectory = LearningTrajectory(
                agent_id=agent_id,
                objective=learning_objective,
                trajectory_points=trajectory_points,
                trend_direction=trend_direction,
                trend_strength=abs(trend_strength),
                confidence=confidence,
                prediction_horizon=self.enhanced_params.predictive_horizon
            )

            self.learning_trajectories[f"{agent_id}_{learning_objective}"] = trajectory

    def _rank_suggestions(self, suggestions: List[AdaptationSuggestion]) -> List[AdaptationSuggestion]:
        """Rank suggestions by confidence and risk level"""
        def sort_key(suggestion):
            risk_priority = {'low': 1, 'medium': 2, 'high': 3}
            return (-suggestion.confidence, risk_priority.get(suggestion.risk_level, 4))

        suggestions.sort(key=sort_key)
        return suggestions

    def record_cross_domain_pattern(self, source_agent: str, source_objective: str,
                                  target_agents: List[str], target_objectives: List[str],
                                  effectiveness_scores: Dict[str, float],
                                  adaptation_requirements: Dict[str, Dict[str, Any]],
                                  confidence: float = 0.8):
        """Record a cross-domain learning pattern"""
        pattern_id = f"cross_domain_{source_agent}_{source_objective}_{int(datetime.now().timestamp())}"

        pattern = CrossDomainPattern(
            pattern_id=pattern_id,
            source_domain=f"{source_agent}_{source_objective}",
            target_domains=[f"{agent}_{obj}" for agent in target_agents for obj in target_objectives],
            effectiveness_score=effectiveness_scores,
            adaptation_requirements=adaptation_requirements,
            confidence=confidence
        )

        self.cross_domain_patterns[pattern_id] = pattern

        self.logger.info(f"Recorded cross-domain pattern {pattern_id} from {source_agent}")

        # Save to persistent storage
        self._save_cross_domain_patterns()

    def _save_cross_domain_patterns(self):
        """Save cross-domain patterns to persistent storage"""
        try:
            patterns_dir = Path("outgoing/ai4all/knowledge")
            patterns_dir.mkdir(parents=True, exist_ok=True)

            patterns_data = {pid: pattern.to_dict() for pid, pattern in self.cross_domain_patterns.items()}

            with open(patterns_dir / "cross_domain_patterns.json", 'w') as f:
                json.dump(patterns_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.warning(f"Failed to save cross-domain patterns: {e}")

    def get_enhanced_parameters(self, agent_id: str, learning_objective: str) -> Dict[str, Any]:
        """Get enhanced learning parameters for an agent"""
        basic_params = self.get_learning_parameters(agent_id, learning_objective)

        # Add enhanced parameters
        enhanced_data = {
            **basic_params,
            'predictive_horizon': self.enhanced_params.predictive_horizon,
            'cross_domain_weight': self.enhanced_params.cross_domain_weight,
            'neural_network_enabled': self.enhanced_params.neural_network_enabled,
            'memory_retention': self.enhanced_params.memory_retention,
            'adaptation_aggressiveness': self.enhanced_params.adaptation_aggressiveness
        }

        # Add trajectory information if available
        trajectory_key = f"{agent_id}_{learning_objective}"
        if trajectory_key in self.learning_trajectories:
            enhanced_data['trajectory'] = self.learning_trajectories[trajectory_key].to_dict()

        return enhanced_data

    def analyze_adaptation_effectiveness(self, agent_id: str, adaptation_history: List[Dict]) -> Dict[str, float]:
        """Analyze the effectiveness of past adaptations"""
        if not adaptation_history:
            return {'overall_effectiveness': 0.5, 'sample_size': 0}

        effectiveness_scores = []

        for adaptation in adaptation_history[-10:]:  # Last 10 adaptations
            success = adaptation.get('success', False)
            impact = adaptation.get('performance_impact', {})

            # Calculate effectiveness score
            if success and impact:
                # Average impact across all metrics
                avg_impact = sum(impact.values()) / len(impact) if impact else 0
                effectiveness = min(1.0, max(0.0, 0.5 + avg_impact))
            else:
                effectiveness = 0.3  # Low effectiveness for failed adaptations

            effectiveness_scores.append(effectiveness)

        return {
            'overall_effectiveness': statistics.mean(effectiveness_scores) if effectiveness_scores else 0.5,
            'sample_size': len(effectiveness_scores),
            'best_effectiveness': max(effectiveness_scores) if effectiveness_scores else 0.5,
            'worst_effectiveness': min(effectiveness_scores) if effectiveness_scores else 0.5,
            'consistency': statistics.stdev(effectiveness_scores) if len(effectiveness_scores) > 1 else 0.0
        }

    def get_learning_insights(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive learning insights for an agent"""
        insights = {
            'agent_id': agent_id,
            'timestamp': datetime.now().isoformat(),
            'learning_trajectories': {},
            'cross_domain_opportunities': [],
            'adaptation_effectiveness': {},
            'recommendations': []
        }

        # Get learning trajectories
        for trajectory_key, trajectory in self.learning_trajectories.items():
            if trajectory_key.startswith(f"{agent_id}_"):
                insights['learning_trajectories'][trajectory_key] = trajectory.to_dict()

        # Get cross-domain opportunities
        for pattern in self.cross_domain_patterns.values():
            if any(target.startswith(f"{agent_id}_") for target in pattern.target_domains):
                insights['cross_domain_opportunities'].append(pattern.to_dict())

        # Get adaptation effectiveness
        adaptation_history = self.get_adaptation_history(agent_id)
        insights['adaptation_effectiveness'] = self.analyze_adaptation_effectiveness(agent_id, adaptation_history)

        # Generate recommendations
        insights['recommendations'] = self._generate_insight_based_recommendations(agent_id, insights)

        return insights

    def _generate_insight_based_recommendations(self, agent_id: str, insights: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on learning insights"""
        recommendations = []

        # Trajectory-based recommendations
        trajectories = insights.get('learning_trajectories', {})
        for trajectory_key, trajectory_data in trajectories.items():
            if trajectory_data['trend_direction'] == 'declining':
                recommendations.append(f"Address declining trajectory in {trajectory_data['objective']} - consider baseline adjustment")
            elif trajectory_data['trend_direction'] == 'improving' and trajectory_data['trend_strength'] > 0.8:
                recommendations.append(f"Excellent progress in {trajectory_data['objective']} - consider advanced optimization")

        # Adaptation effectiveness recommendations
        effectiveness = insights.get('adaptation_effectiveness', {})
        if effectiveness.get('overall_effectiveness', 0.5) < 0.6:
            recommendations.append("Review adaptation strategy - effectiveness below optimal threshold")
        elif effectiveness.get('consistency', 0) > 0.3:
            recommendations.append("Adaptations showing high variability - consider more conservative approach")

        # Cross-domain opportunities
        opportunities = insights.get('cross_domain_opportunities', [])
        if opportunities:
            recommendations.append(f"Found {len(opportunities)} cross-domain learning opportunities - consider pattern transfer")

        return recommendations[:5]  # Top 5 recommendations
