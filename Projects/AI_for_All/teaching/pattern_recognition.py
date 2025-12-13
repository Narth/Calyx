"""
Pattern Recognition - Identifies successful behavioral patterns for AI-for-All
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics
from collections import defaultdict


@dataclass
class BehavioralPattern:
    """Represents a recognized behavioral pattern"""
    id: str
    agent_id: str
    pattern_type: str  # 'temporal', 'resource', 'interaction', 'performance'
    description: str
    triggers: List[str]
    outcomes: Dict[str, float]
    frequency: int
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    first_observed: datetime
    last_observed: datetime
    context_similarity: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PatternSequence:
    """Sequence of patterns that occur together"""
    id: str
    patterns: List[str]  # Pattern IDs
    sequence_type: str
    combined_outcome: Dict[str, float]
    occurrence_count: int
    success_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


class PatternRecognition:
    """
    Recognizes and analyzes behavioral patterns in agent performance and interactions.
    Identifies successful patterns that can be taught to other agents.
    """

    def __init__(self, config: dict):
        """
        Initialize the pattern recognition system.

        Args:
            config: Configuration dictionary for pattern recognition
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Pattern storage
        self.patterns: Dict[str, BehavioralPattern] = {}
        self.sequences: Dict[str, PatternSequence] = {}
        self.agent_patterns: Dict[str, List[str]] = defaultdict(list)

        # Pattern analysis state
        self.observation_buffer: Dict[str, List[Dict]] = defaultdict(list)
        self.pattern_candidates: Dict[str, List[Dict]] = defaultdict(list)

        # Load existing patterns
        self._load_persistent_patterns()

        # Pattern recognition parameters
        self.min_occurrences = config.get('min_occurrences', 3)
        self.pattern_strength_threshold = config.get('strength_threshold', 0.7)
        self.max_patterns_per_agent = config.get('max_patterns_per_agent', 50)
        self.decay_rate = config.get('decay_rate', 0.9)

    def _load_persistent_patterns(self):
        """Load existing patterns from persistent storage"""
        try:
            patterns_file = Path("outgoing/ai4all/patterns/behavioral_patterns.json")
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                    for pattern_id, data in patterns_data.items():
                        data['first_observed'] = datetime.fromisoformat(data['first_observed'])
                        data['last_observed'] = datetime.fromisoformat(data['last_observed'])
                        self.patterns[pattern_id] = BehavioralPattern(**data)

            # Load agent pattern mappings
            mapping_file = Path("outgoing/ai4all/patterns/agent_patterns.json")
            if mapping_file.exists():
                with open(mapping_file, 'r') as f:
                    self.agent_patterns = defaultdict(list, json.load(f))

        except Exception as e:
            self.logger.warning(f"Failed to load persistent patterns: {e}")

    def _save_persistent_patterns(self):
        """Save patterns to persistent storage"""
        try:
            patterns_dir = Path("outgoing/ai4all/patterns")
            patterns_dir.mkdir(parents=True, exist_ok=True)

            # Save patterns
            patterns_data = {pid: pattern.to_dict() for pid, pattern in self.patterns.items()}
            with open(patterns_dir / "behavioral_patterns.json", 'w') as f:
                json.dump(patterns_data, f, indent=2, default=str)

            # Save agent mappings
            with open(patterns_dir / "agent_patterns.json", 'w') as f:
                json.dump(dict(self.agent_patterns), f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to save persistent patterns: {e}")

    def observe_behavior(self, agent_id: str, behavior_data: Dict,
                        context: Dict = None, performance_metrics: Dict = None):
        """
        Observe agent behavior and add to analysis buffer.

        Args:
            agent_id: Agent being observed
            behavior_data: Description of the behavior
            context: Environmental context
            performance_metrics: Performance metrics at time of behavior
        """
        observation = {
            'timestamp': datetime.now(),
            'behavior': behavior_data,
            'context': context or {},
            'performance': performance_metrics or {}
        }

        # Add to observation buffer
        self.observation_buffer[agent_id].append(observation)

        # Keep buffer manageable (last 100 observations per agent)
        if len(self.observation_buffer[agent_id]) > 100:
            self.observation_buffer[agent_id] = self.observation_buffer[agent_id][-100:]

        # Analyze for patterns
        self._analyze_patterns(agent_id)

    def _analyze_patterns(self, agent_id: str):
        """Analyze recent observations for patterns"""
        observations = self.observation_buffer[agent_id]

        if len(observations) < self.min_occurrences:
            return

        # Look for temporal patterns (behaviors that lead to good outcomes)
        self._find_temporal_patterns(agent_id, observations)

        # Look for resource usage patterns
        self._find_resource_patterns(agent_id, observations)

        # Look for interaction patterns
        self._find_interaction_patterns(agent_id, observations)

        # Look for performance correlation patterns
        self._find_performance_patterns(agent_id, observations)

    def _find_temporal_patterns(self, agent_id: str, observations: List[Dict]):
        """Find patterns in behavior sequences over time"""
        if len(observations) < 5:
            return

        # Group observations by similar behaviors
        behavior_groups = defaultdict(list)
        for obs in observations:
            behavior_key = self._get_behavior_key(obs['behavior'])
            behavior_groups[behavior_key].append(obs)

        # Look for behaviors that consistently lead to good performance
        for behavior_key, obs_group in behavior_groups.items():
            if len(obs_group) >= self.min_occurrences:
                avg_performance = self._calculate_avg_performance(obs_group)

                # Check if this behavior correlates with good performance
                if self._is_good_performance(avg_performance):
                    pattern = self._create_temporal_pattern(
                        agent_id, behavior_key, obs_group, avg_performance
                    )

                    if pattern and pattern.strength > self.pattern_strength_threshold:
                        self._register_pattern(pattern)

    def _find_resource_patterns(self, agent_id: str, observations: List[Dict]):
        """Find patterns in resource usage"""
        resource_observations = [obs for obs in observations if 'resource_usage' in obs['behavior']]

        if len(resource_observations) < self.min_occurrences:
            return

        # Group by resource usage patterns
        usage_patterns = defaultdict(list)
        for obs in resource_observations:
            usage_key = self._get_resource_usage_key(obs['behavior']['resource_usage'])
            usage_patterns[usage_key].append(obs)

        for usage_key, obs_group in usage_patterns.items():
            if len(obs_group) >= self.min_occurrences:
                avg_performance = self._calculate_avg_performance(obs_group)

                if self._is_good_performance(avg_performance):
                    pattern = self._create_resource_pattern(
                        agent_id, usage_key, obs_group, avg_performance
                    )

                    if pattern and pattern.strength > self.pattern_strength_threshold:
                        self._register_pattern(pattern)

    def _find_interaction_patterns(self, agent_id: str, observations: List[Dict]):
        """Find patterns in agent interactions"""
        interaction_observations = [obs for obs in observations if 'interaction' in obs['behavior']]

        if len(interaction_observations) < self.min_occurrences:
            return

        # Group by interaction patterns
        interaction_groups = defaultdict(list)
        for obs in interaction_observations:
            interaction_key = self._get_interaction_key(obs['behavior']['interaction'])
            interaction_groups[interaction_key].append(obs)

        for interaction_key, obs_group in interaction_groups.items():
            if len(obs_group) >= self.min_occurrences:
                avg_performance = self._calculate_avg_performance(obs_group)

                if self._is_good_performance(avg_performance):
                    pattern = self._create_interaction_pattern(
                        agent_id, interaction_key, obs_group, avg_performance
                    )

                    if pattern and pattern.strength > self.pattern_strength_threshold:
                        self._register_pattern(pattern)

    def _find_performance_patterns(self, agent_id: str, observations: List[Dict]):
        """Find patterns that correlate with performance metrics"""
        if len(observations) < 10:  # Need more data for performance patterns
            return

        # Look for context patterns that predict performance
        context_groups = defaultdict(list)
        for obs in observations:
            context_key = self._get_context_key(obs['context'])
            context_groups[context_key].append(obs)

        for context_key, obs_group in context_groups.items():
            if len(obs_group) >= self.min_occurrences:
                avg_performance = self._calculate_avg_performance(obs_group)

                pattern = self._create_performance_pattern(
                    agent_id, context_key, obs_group, avg_performance
                )

                if pattern and pattern.strength > self.pattern_strength_threshold:
                    self._register_pattern(pattern)

    def _get_behavior_key(self, behavior: Dict) -> str:
        """Generate a key for grouping similar behaviors"""
        key_parts = []

        for k, v in behavior.items():
            if isinstance(v, dict):
                # For nested dictionaries, use sorted keys
                nested_key = "_".join(sorted(v.keys()))
                key_parts.append(f"{k}:{nested_key}")
            else:
                key_parts.append(f"{k}:{v}")

        return "|".join(key_parts)

    def _get_resource_usage_key(self, resource_usage: Dict) -> str:
        """Generate key for resource usage patterns"""
        key_parts = []

        for resource, usage in resource_usage.items():
            if isinstance(usage, (int, float)):
                # Quantize usage levels
                if usage < 0.3:
                    level = "low"
                elif usage < 0.7:
                    level = "medium"
                else:
                    level = "high"
                key_parts.append(f"{resource}:{level}")
            else:
                key_parts.append(f"{resource}:{usage}")

        return "|".join(sorted(key_parts))

    def _get_interaction_key(self, interaction: Dict) -> str:
        """Generate key for interaction patterns"""
        key_parts = []

        for k, v in interaction.items():
            if k in ['type', 'target', 'frequency']:
                key_parts.append(f"{k}:{v}")
            elif isinstance(v, dict):
                nested_key = "_".join(sorted(v.keys()))
                key_parts.append(f"{k}:{nested_key}")

        return "|".join(sorted(key_parts))

    def _get_context_key(self, context: Dict) -> str:
        """Generate key for context patterns"""
        key_parts = []

        for k, v in context.items():
            if k in ['time_of_day', 'workload', 'system_state']:
                key_parts.append(f"{k}:{v}")
            elif isinstance(v, (int, float)):
                # Quantize numeric context
                if v < 0.33:
                    quantized = "low"
                elif v < 0.66:
                    quantized = "medium"
                else:
                    quantized = "high"
                key_parts.append(f"{k}:{quantized}")

        return "|".join(sorted(key_parts))

    def _calculate_avg_performance(self, observations: List[Dict]) -> Dict[str, float]:
        """Calculate average performance across observations"""
        all_metrics = defaultdict(list)

        for obs in observations:
            for metric, value in obs['performance'].items():
                all_metrics[metric].append(value)

        avg_performance = {}
        for metric, values in all_metrics.items():
            avg_performance[metric] = statistics.mean(values)

        return avg_performance

    def _is_good_performance(self, performance: Dict[str, float]) -> bool:
        """Determine if performance metrics indicate a successful pattern"""
        # Define thresholds for "good" performance
        thresholds = {
            'tes': 0.7,
            'stability': 0.7,
            'velocity': 0.5,
            'error_rate': 0.3
        }

        score = 0.0
        count = 0

        for metric, threshold in thresholds.items():
            if metric in performance:
                value = performance[metric]
                if metric == 'error_rate':
                    # Lower is better for error rate
                    if value <= threshold:
                        score += 1.0
                else:
                    # Higher is better for other metrics
                    if value >= threshold:
                        score += 1.0
                count += 1

        return (score / count) >= 0.7 if count > 0 else False

    def _create_temporal_pattern(self, agent_id: str, behavior_key: str,
                               observations: List[Dict], avg_performance: Dict[str, float]) -> Optional[BehavioralPattern]:
        """Create a temporal behavioral pattern"""
        if not observations:
            return None

        pattern_id = f"temp_{agent_id}_{behavior_key}_{int(datetime.now().timestamp())}"

        # Calculate pattern strength based on consistency and performance
        performance_consistency = self._calculate_performance_consistency(observations)
        frequency = len(observations)

        # Strength combines frequency, performance, and consistency
        strength = min(1.0, (frequency / 10.0) * performance_consistency)

        return BehavioralPattern(
            id=pattern_id,
            agent_id=agent_id,
            pattern_type='temporal',
            description=f"Temporal pattern: {behavior_key}",
            triggers=[behavior_key],
            outcomes=avg_performance,
            frequency=frequency,
            strength=strength,
            confidence=performance_consistency,
            first_observed=observations[0]['timestamp'],
            last_observed=observations[-1]['timestamp']
        )

    def _create_resource_pattern(self, agent_id: str, usage_key: str,
                               observations: List[Dict], avg_performance: Dict[str, float]) -> Optional[BehavioralPattern]:
        """Create a resource usage pattern"""
        if not observations:
            return None

        pattern_id = f"res_{agent_id}_{usage_key}_{int(datetime.now().timestamp())}"

        frequency = len(observations)
        performance_consistency = self._calculate_performance_consistency(observations)
        strength = min(1.0, (frequency / 8.0) * performance_consistency)

        return BehavioralPattern(
            id=pattern_id,
            agent_id=agent_id,
            pattern_type='resource',
            description=f"Resource usage pattern: {usage_key}",
            triggers=[f"resource_usage:{usage_key}"],
            outcomes=avg_performance,
            frequency=frequency,
            strength=strength,
            confidence=performance_consistency,
            first_observed=observations[0]['timestamp'],
            last_observed=observations[-1]['timestamp']
        )

    def _create_interaction_pattern(self, agent_id: str, interaction_key: str,
                                  observations: List[Dict], avg_performance: Dict[str, float]) -> Optional[BehavioralPattern]:
        """Create an interaction pattern"""
        if not observations:
            return None

        pattern_id = f"int_{agent_id}_{interaction_key}_{int(datetime.now().timestamp())}"

        frequency = len(observations)
        performance_consistency = self._calculate_performance_consistency(observations)
        strength = min(1.0, (frequency / 6.0) * performance_consistency)

        return BehavioralPattern(
            id=pattern_id,
            agent_id=agent_id,
            pattern_type='interaction',
            description=f"Interaction pattern: {interaction_key}",
            triggers=[f"interaction:{interaction_key}"],
            outcomes=avg_performance,
            frequency=frequency,
            strength=strength,
            confidence=performance_consistency,
            first_observed=observations[0]['timestamp'],
            last_observed=observations[-1]['timestamp']
        )

    def _create_performance_pattern(self, agent_id: str, context_key: str,
                                  observations: List[Dict], avg_performance: Dict[str, float]) -> Optional[BehavioralPattern]:
        """Create a performance correlation pattern"""
        if not observations:
            return None

        pattern_id = f"perf_{agent_id}_{context_key}_{int(datetime.now().timestamp())}"

        frequency = len(observations)
        performance_consistency = self._calculate_performance_consistency(observations)
        strength = min(1.0, (frequency / 12.0) * performance_consistency)

        return BehavioralPattern(
            id=pattern_id,
            agent_id=agent_id,
            pattern_type='performance',
            description=f"Performance correlation: {context_key}",
            triggers=[f"context:{context_key}"],
            outcomes=avg_performance,
            frequency=frequency,
            strength=strength,
            confidence=performance_consistency,
            first_observed=observations[0]['timestamp'],
            last_observed=observations[-1]['timestamp']
        )

    def _calculate_performance_consistency(self, observations: List[Dict]) -> float:
        """Calculate how consistent the performance outcomes are"""
        if len(observations) < 2:
            return 0.5

        # Get performance metrics across observations
        all_metrics = defaultdict(list)
        for obs in observations:
            for metric, value in obs['performance'].items():
                all_metrics[metric].append(value)

        # Calculate coefficient of variation for each metric
        consistencies = []
        for metric, values in all_metrics.items():
            if len(values) > 1:
                mean_val = statistics.mean(values)
                std_val = statistics.stdev(values) if len(values) > 1 else 0

                if mean_val > 0:
                    cv = std_val / mean_val  # Coefficient of variation
                    consistency = max(0, 1.0 - cv)  # Lower CV means higher consistency
                    consistencies.append(consistency)

        return statistics.mean(consistencies) if consistencies else 0.5

    def _register_pattern(self, pattern: BehavioralPattern):
        """Register a new pattern and save to storage"""
        # Check if we already have too many patterns for this agent
        current_count = len([p for p in self.patterns.values() if p.agent_id == pattern.agent_id])

        if current_count >= self.max_patterns_per_agent:
            # Remove weakest pattern
            agent_patterns = [p for p in self.patterns.values() if p.agent_id == pattern.agent_id]
            weakest_pattern = min(agent_patterns, key=lambda p: p.strength)

            # Decay strength of remaining patterns
            self._decay_pattern_strengths(pattern.agent_id)

            # Remove the weakest
            if weakest_pattern.id in self.patterns:
                del self.patterns[weakest_pattern.id]
                if pattern.agent_id in self.agent_patterns and weakest_pattern.id in self.agent_patterns[pattern.agent_id]:
                    self.agent_patterns[pattern.agent_id].remove(weakest_pattern.id)

        # Add new pattern
        self.patterns[pattern.id] = pattern
        self.agent_patterns[pattern.agent_id].append(pattern.id)

        # Save to persistent storage
        self._save_persistent_patterns()

        self.logger.info(f"Registered pattern {pattern.id} for {pattern.agent_id}: {pattern.description}")

    def _decay_pattern_strengths(self, agent_id: str):
        """Decay strength of existing patterns to make room for new ones"""
        for pattern_id, pattern in list(self.patterns.items()):
            if pattern.agent_id == agent_id:
                pattern.strength *= self.decay_rate
                pattern.confidence *= self.decay_rate

                # Remove very weak patterns
                if pattern.strength < 0.1:
                    del self.patterns[pattern_id]
                    if agent_id in self.agent_patterns and pattern_id in self.agent_patterns[agent_id]:
                        self.agent_patterns[agent_id].remove(pattern_id)

    def get_agent_patterns(self, agent_id: str) -> List[Dict]:
        """Get all patterns for a specific agent"""
        agent_pattern_ids = self.agent_patterns.get(agent_id, [])
        return [self.patterns[pid].to_dict() for pid in agent_pattern_ids if pid in self.patterns]

    def get_strong_patterns(self, agent_id: str, min_strength: float = None) -> List[Dict]:
        """Get strong patterns for an agent"""
        min_strength = min_strength or self.pattern_strength_threshold
        patterns = self.get_agent_patterns(agent_id)

        return [p for p in patterns if p['strength'] >= min_strength]

    def find_similar_patterns(self, reference_pattern: Dict, other_agents: List[str] = None) -> List[Dict]:
        """Find patterns similar to a reference pattern"""
        if not other_agents:
            other_agents = [agent for agent in self.agent_patterns.keys()
                          if agent != reference_pattern['agent_id']]

        similar_patterns = []

        for agent_id in other_agents:
            agent_patterns = self.get_agent_patterns(agent_id)

            for pattern in agent_patterns:
                similarity = self._calculate_pattern_similarity(reference_pattern, pattern)

                if similarity > 0.7:  # 70% similarity threshold
                    similar_patterns.append({
                        'pattern': pattern,
                        'similarity': similarity,
                        'source_agent': agent_id
                    })

        return sorted(similar_patterns, key=lambda x: x['similarity'], reverse=True)

    def _calculate_pattern_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between two patterns"""
        similarity_factors = []

        # Type similarity
        if pattern1['pattern_type'] == pattern2['pattern_type']:
            similarity_factors.append(1.0)
        else:
            similarity_factors.append(0.0)

        # Outcome similarity
        outcomes1 = pattern1['outcomes']
        outcomes2 = pattern2['outcomes']

        common_metrics = set(outcomes1.keys()) & set(outcomes2.keys())
        if common_metrics:
            outcome_similarity = 0.0
            for metric in common_metrics:
                val1 = outcomes1[metric]
                val2 = outcomes2[metric]
                # Normalize difference to similarity (0 to 1)
                diff = abs(val1 - val2)
                similarity = 1.0 - min(1.0, diff)
                outcome_similarity += similarity
            outcome_similarity /= len(common_metrics)
            similarity_factors.append(outcome_similarity)
        else:
            similarity_factors.append(0.0)

        # Context similarity (if available)
        context1 = pattern1.get('context', {})
        context2 = pattern2.get('context', {})

        if context1 and context2:
            common_context = set(context1.keys()) & set(context2.keys())
            if common_context:
                context_similarity = sum(1.0 for key in common_context
                                       if context1[key] == context2[key]) / len(common_context)
                similarity_factors.append(context_similarity)
            else:
                similarity_factors.append(0.0)
        else:
            similarity_factors.append(0.5)  # Neutral similarity for missing context

        return statistics.mean(similarity_factors) if similarity_factors else 0.0

    def get_pattern_statistics(self, agent_id: str) -> Dict:
        """Get pattern statistics for an agent"""
        patterns = self.get_agent_patterns(agent_id)

        if not patterns:
            return {'total_patterns': 0, 'average_strength': 0.0, 'average_confidence': 0.0}

        strengths = [p['strength'] for p in patterns]
        confidences = [p['confidence'] for p in patterns]

        return {
            'total_patterns': len(patterns),
            'average_strength': statistics.mean(strengths),
            'average_confidence': statistics.mean(confidences),
            'pattern_types': list(set(p['pattern_type'] for p in patterns)),
            'strong_patterns': len([p for p in patterns if p['strength'] > self.pattern_strength_threshold])
        }

    def cleanup_old_patterns(self, max_age_days: int = 90):
        """Remove patterns older than specified age"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        for pattern_id, pattern in list(self.patterns.items()):
            if pattern.last_observed < cutoff_date:
                # Decay strength first
                pattern.strength *= 0.5

                # Remove if too weak
                if pattern.strength < 0.1:
                    del self.patterns[pattern_id]
                    if pattern.agent_id in self.agent_patterns and pattern_id in self.agent_patterns[pattern.agent_id]:
                        self.agent_patterns[pattern.agent_id].remove(pattern_id)

        # Save updated patterns
        self._save_persistent_patterns()

        self.logger.info(f"Cleaned up patterns older than {max_age_days} days")
