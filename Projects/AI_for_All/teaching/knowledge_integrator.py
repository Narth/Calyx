"""
Knowledge Integrator - Cross-agent knowledge sharing for AI-for-All
"""

import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class KnowledgePattern:
    """Represents a learned knowledge pattern"""
    id: str
    source_agent: str
    pattern_type: str  # 'success', 'failure', 'optimization', 'stability'
    description: str
    metrics_impact: Dict[str, float]
    context: Dict[str, str]
    confidence: float
    created_date: datetime
    usage_count: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgeTransfer:
    """Record of knowledge transfer between agents"""
    id: str
    source_agent: str
    target_agent: str
    pattern_id: str
    transfer_date: datetime
    adaptation_required: bool
    success: bool
    performance_impact: Dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


class KnowledgeIntegrator:
    """
    Manages knowledge integration and sharing across agents in the Calyx Terminal.
    Identifies successful patterns and facilitates their transfer to other agents.
    """

    def __init__(self, config: dict):
        """
        Initialize the knowledge integrator.

        Args:
            config: Configuration dictionary for knowledge integration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Knowledge storage
        self.patterns: Dict[str, KnowledgePattern] = {}
        self.transfers: List[KnowledgeTransfer] = []
        self.agent_knowledge: Dict[str, Set[str]] = {}  # agent -> set of pattern IDs

        # Load existing knowledge
        self._load_persistent_knowledge()

        # Pattern matching thresholds
        self.similarity_threshold = config.get('similarity_threshold', 0.8)
        self.min_pattern_strength = config.get('min_pattern_strength', 0.7)

    def _load_persistent_knowledge(self):
        """Load existing knowledge patterns and transfers"""
        try:
            # Load patterns
            patterns_file = Path("outgoing/ai4all/knowledge/patterns.json")
            if patterns_file.exists():
                with open(patterns_file, 'r') as f:
                    patterns_data = json.load(f)
                    for pattern_id, data in patterns_data.items():
                        data['created_date'] = datetime.fromisoformat(data['created_date'])
                        self.patterns[pattern_id] = KnowledgePattern(**data)

            # Load transfers
            transfers_file = Path("outgoing/ai4all/knowledge/transfers.json")
            if transfers_file.exists():
                with open(transfers_file, 'r') as f:
                    transfers_data = json.load(f)
                    for transfer_data in transfers_data:
                        transfer_data['transfer_date'] = datetime.fromisoformat(transfer_data['transfer_date'])
                        self.transfers.append(KnowledgeTransfer(**transfer_data))

            # Load agent knowledge mapping (convert lists back to sets)
            mapping_file = Path("outgoing/ai4all/knowledge/agent_mapping.json")
            if mapping_file.exists():
                with open(mapping_file, 'r') as f:
                    loaded_mapping = json.load(f)
                    self.agent_knowledge = {agent: set(patterns) for agent, patterns in loaded_mapping.items()}

        except Exception as e:
            self.logger.warning(f"Failed to load persistent knowledge: {e}")

    def _save_persistent_knowledge(self):
        """Save knowledge patterns and transfers to persistent storage"""
        try:
            knowledge_dir = Path("outgoing/ai4all/knowledge")
            knowledge_dir.mkdir(parents=True, exist_ok=True)

            # Save patterns
            patterns_data = {pid: pattern.to_dict() for pid, pattern in self.patterns.items()}
            with open(knowledge_dir / "patterns.json", 'w') as f:
                json.dump(patterns_data, f, indent=2, default=str)

            # Save transfers
            transfers_data = [transfer.to_dict() for transfer in self.transfers]
            with open(knowledge_dir / "transfers.json", 'w') as f:
                json.dump(transfers_data, f, indent=2, default=str)

            # Save agent mapping (convert sets to lists for JSON serialization)
            agent_mapping_serializable = {agent: list(patterns) for agent, patterns in self.agent_knowledge.items()}
            with open(knowledge_dir / "agent_mapping.json", 'w') as f:
                json.dump(agent_mapping_serializable, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to save persistent knowledge: {e}")

    def record_successful_pattern(self, agent_id: str, pattern_type: str,
                                description: str, metrics_impact: Dict[str, float],
                                context: Dict[str, str], confidence: float = 0.8) -> str:
        """
        Record a successful pattern from an agent's performance.

        Args:
            agent_id: Agent that demonstrated the pattern
            pattern_type: Type of pattern (success, failure, optimization, stability)
            description: Human-readable description of the pattern
            metrics_impact: Impact on performance metrics
            context: Additional context about when/how the pattern occurred
            confidence: Confidence in the pattern's effectiveness

        Returns:
            Pattern ID
        """
        pattern_id = f"{agent_id}_{pattern_type}_{int(datetime.now().timestamp())}"

        pattern = KnowledgePattern(
            id=pattern_id,
            source_agent=agent_id,
            pattern_type=pattern_type,
            description=description,
            metrics_impact=metrics_impact.copy(),
            context=context.copy(),
            confidence=confidence,
            created_date=datetime.now()
        )

        self.patterns[pattern_id] = pattern

        # Add to agent's knowledge
        if agent_id not in self.agent_knowledge:
            self.agent_knowledge[agent_id] = set()
        self.agent_knowledge[agent_id].add(pattern_id)

        # Save to persistent storage
        self._save_persistent_knowledge()

        self.logger.info(f"Recorded pattern {pattern_id} for {agent_id}: {description}")
        return pattern_id

    def find_transferable_patterns(self, target_agent: str, performance_metrics: Dict[str, float]) -> List[Dict]:
        """
        Find patterns from other agents that could benefit the target agent.

        Args:
            target_agent: Agent that might benefit from pattern transfer
            performance_metrics: Current performance metrics of target agent

        Returns:
            List of transferable patterns with adaptation suggestions
        """
        transferable = []

        # Get patterns from other agents
        other_agents_patterns = []
        for agent_id, pattern_ids in self.agent_knowledge.items():
            if agent_id != target_agent:
                for pattern_id in pattern_ids:
                    if pattern_id in self.patterns:
                        pattern = self.patterns[pattern_id]
                        # Only consider strong, recent patterns
                        if (pattern.confidence > self.min_pattern_strength and
                            (datetime.now() - pattern.created_date).days < 30):
                            other_agents_patterns.append(pattern)

        for pattern in other_agents_patterns:
            # Check if this pattern could help the target agent
            adaptation_score = self._calculate_adaptation_score(pattern, performance_metrics)

            if adaptation_score > self.similarity_threshold:
                transferable.append({
                    'pattern': pattern.to_dict(),
                    'adaptation_score': adaptation_score,
                    'suggested_adaptations': self._suggest_adaptations(pattern, target_agent),
                    'expected_impact': self._calculate_expected_impact(pattern, performance_metrics)
                })

        # Sort by adaptation score
        transferable.sort(key=lambda x: x['adaptation_score'], reverse=True)

        return transferable[:10]  # Return top 10 matches

    def _calculate_adaptation_score(self, pattern: KnowledgePattern,
                                  current_metrics: Dict[str, float]) -> float:
        """Calculate how well a pattern could adapt to current performance"""
        if not pattern.metrics_impact or not current_metrics:
            return 0.0

        # Find metrics that both pattern and current performance have
        common_metrics = set(pattern.metrics_impact.keys()) & set(current_metrics.keys())

        if not common_metrics:
            return 0.0

        # Calculate similarity based on metric improvements needed
        similarity = 0.0
        for metric in common_metrics:
            current_value = current_metrics[metric]
            pattern_impact = pattern.metrics_impact[metric]

            # If pattern has positive impact on a metric where current is low, it's relevant
            if pattern_impact > 0 and current_value < 0.7:  # Assuming 0.7 is "good" threshold
                similarity += pattern_impact * (1 - current_value)
            elif pattern_impact < 0 and current_value > 0.3:  # Negative impact when value is high
                similarity += abs(pattern_impact) * current_value

        return min(1.0, similarity / len(common_metrics))

    def _suggest_adaptations(self, pattern: KnowledgePattern, target_agent: str) -> List[str]:
        """Suggest how to adapt a pattern for a different agent"""
        adaptations = []

        # Context-based adaptations
        if pattern.context.get('agent_type') != self._get_agent_type(target_agent):
            adaptations.append(f"Adapt pattern for {target_agent} agent characteristics")

        # Performance-based adaptations
        if pattern.pattern_type == 'optimization':
            adaptations.append("Scale optimization parameters based on target agent baseline")

        if pattern.pattern_type == 'stability':
            adaptations.append("Adjust stability thresholds for target agent workload")

        # Time-based adaptations
        age_days = (datetime.now() - pattern.created_date).days
        if age_days > 7:
            adaptations.append("Review pattern effectiveness given system evolution")

        return adaptations

    def _calculate_expected_impact(self, pattern: KnowledgePattern,
                                 current_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate expected impact of applying a pattern"""
        expected_impact = {}

        for metric, current_value in current_metrics.items():
            if metric in pattern.metrics_impact:
                impact = pattern.metrics_impact[metric]

                # Scale impact based on current performance (bigger impact when further from optimal)
                if metric in ['tes', 'stability', 'velocity']:
                    # Higher impact when current value is lower
                    scaling_factor = 1 - current_value
                    expected_impact[metric] = impact * scaling_factor
                elif metric == 'error_rate':
                    # Higher impact when error rate is higher
                    scaling_factor = current_value
                    expected_impact[metric] = -impact * scaling_factor  # Negative because lower error is better

        return expected_impact

    def _get_agent_type(self, agent_id: str) -> str:
        """Determine agent type from ID"""
        if agent_id.startswith('cp'):
            return 'copilot'
        elif agent_id.startswith('agent'):
            return 'agent'
        else:
            return 'system'

    def transfer_knowledge(self, pattern_id: str, source_agent: str,
                          target_agent: str) -> Optional[str]:
        """
        Transfer a knowledge pattern from one agent to another.

        Args:
            pattern_id: ID of pattern to transfer
            source_agent: Agent providing the knowledge
            target_agent: Agent receiving the knowledge

        Returns:
            Transfer ID if successful, None otherwise
        """
        if pattern_id not in self.patterns:
            self.logger.warning(f"Pattern {pattern_id} not found")
            return None

        pattern = self.patterns[pattern_id]

        # Check if transfer is appropriate
        if not self._validate_transfer(pattern, source_agent, target_agent):
            self.logger.warning(f"Transfer of pattern {pattern_id} not appropriate")
            return None

        # Create transfer record
        transfer_id = f"transfer_{int(datetime.now().timestamp())}"

        transfer = KnowledgeTransfer(
            id=transfer_id,
            source_agent=source_agent,
            target_agent=target_agent,
            pattern_id=pattern_id,
            transfer_date=datetime.now(),
            adaptation_required=self._needs_adaptation(pattern, target_agent),
            success=False,  # Will be updated when impact is measured
            performance_impact={}
        )

        self.transfers.append(transfer)

        # Add pattern to target agent's knowledge
        if target_agent not in self.agent_knowledge:
            self.agent_knowledge[target_agent] = set()
        self.agent_knowledge[target_agent].add(pattern_id)

        # Save to persistent storage
        self._save_persistent_knowledge()

        self.logger.info(f"Transferred pattern {pattern_id} from {source_agent} to {target_agent}")
        return transfer_id

    def _validate_transfer(self, pattern: KnowledgePattern, source_agent: str,
                          target_agent: str) -> bool:
        """Validate if a pattern transfer is appropriate"""
        # Don't transfer from agent to itself
        if source_agent == target_agent:
            return False

        # Check pattern strength
        if pattern.confidence < self.min_pattern_strength:
            return False

        # Check pattern age (prefer recent patterns)
        age_days = (datetime.now() - pattern.created_date).days
        if age_days > 60:  # 60 days
            return False

        # Check if target already has this pattern
        if (target_agent in self.agent_knowledge and
            pattern.id in self.agent_knowledge[target_agent]):
            return False

        return True

    def _needs_adaptation(self, pattern: KnowledgePattern, target_agent: str) -> bool:
        """Determine if a pattern needs adaptation for the target agent"""
        # Simple heuristic: different agent types usually need adaptation
        pattern_agent_type = self._get_agent_type(pattern.source_agent)
        target_agent_type = self._get_agent_type(target_agent)

        return pattern_agent_type != target_agent_type

    def update_transfer_success(self, transfer_id: str, success: bool,
                               performance_impact: Dict[str, float]):
        """
        Update the success status of a knowledge transfer.

        Args:
            transfer_id: ID of the transfer to update
            success: Whether the transfer was successful
            performance_impact: Actual performance impact observed
        """
        for transfer in self.transfers:
            if transfer.id == transfer_id:
                transfer.success = success
                transfer.performance_impact = performance_impact.copy()
                break

        # Save updated transfers
        self._save_persistent_knowledge()

        self.logger.info(f"Updated transfer {transfer_id}: success={success}, impact={performance_impact}")

    def get_integration_status(self, agent_id: str) -> Dict:
        """Get knowledge integration status for an agent"""
        if agent_id not in self.agent_knowledge:
            return {'patterns_count': 0, 'transfers_received': 0, 'transfers_sent': 0}

        agent_patterns = self.agent_knowledge[agent_id]

        # Count transfers
        transfers_received = len([t for t in self.transfers if t.target_agent == agent_id])
        transfers_sent = len([t for t in self.transfers if t.source_agent == agent_id])

        # Calculate pattern effectiveness
        effective_patterns = 0
        total_impact = 0.0

        for pattern_id in agent_patterns:
            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                pattern_effectiveness = pattern.confidence * pattern.success_rate
                if pattern_effectiveness > 0.7:
                    effective_patterns += 1
                total_impact += pattern_effectiveness

        return {
            'patterns_count': len(agent_patterns),
            'effective_patterns': effective_patterns,
            'transfers_received': transfers_received,
            'transfers_sent': transfers_sent,
            'average_impact': total_impact / len(agent_patterns) if agent_patterns else 0.0,
            'knowledge_maturity': self._calculate_knowledge_maturity(agent_id)
        }

    def _calculate_knowledge_maturity(self, agent_id: str) -> float:
        """Calculate knowledge maturity score for an agent"""
        if agent_id not in self.agent_knowledge or not self.agent_knowledge[agent_id]:
            return 0.0

        agent_patterns = self.agent_knowledge[agent_id]
        maturity_factors = []

        for pattern_id in agent_patterns:
            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]

                # Age factor (newer patterns contribute more to maturity)
                age_days = (datetime.now() - pattern.created_date).days
                age_factor = min(1.0, age_days / 30.0)  # Full maturity after 30 days

                # Usage factor
                usage_factor = min(1.0, pattern.usage_count / 10.0)

                # Success factor
                success_factor = pattern.success_rate

                # Combined maturity for this pattern
                pattern_maturity = (age_factor * 0.3 + usage_factor * 0.3 + success_factor * 0.4)
                maturity_factors.append(pattern_maturity)

        return sum(maturity_factors) / len(maturity_factors) if maturity_factors else 0.0

    def get_knowledge_report(self, agent_id: str) -> str:
        """Generate a human-readable knowledge report for an agent"""
        status = self.get_integration_status(agent_id)

        report = []
        report.append(f"Knowledge Integration Report for {agent_id}")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().isoformat()}")

        report.append(f"\nPatterns Available: {status['patterns_count']}")
        report.append(f"Effective Patterns: {status['effective_patterns']}")
        maturity_formatted = f"{status['knowledge_maturity']:.3f}"
        report.append(f"Knowledge Maturity: {maturity_formatted}")
        report.append(f"Transfers Received: {status['transfers_received']}")
        report.append(f"Transfers Sent: {status['transfers_sent']}")

        if agent_id in self.agent_knowledge and self.agent_knowledge[agent_id]:
            report.append("\nTop Patterns:")
            agent_patterns = list(self.agent_knowledge[agent_id])[:5]  # Top 5

            for pattern_id in agent_patterns:
                if pattern_id in self.patterns:
                    pattern = self.patterns[pattern_id]
                    report.append(f"  - {pattern.pattern_type}: {pattern.description[:50]}...")
                    report.append(f"    Impact: {pattern.metrics_impact}")
                    confidence_formatted = f"{pattern.confidence:.2f}"
                    report.append(f"    Confidence: {confidence_formatted}")

        return "\n".join(report)
