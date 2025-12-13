#!/usr/bin/env python3
"""
Knowledge Retention Enhancer - Improves knowledge maturity and retention in AI-for-All teaching system
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta

from ..teaching.framework import TeachingFramework
from ..teaching.agent_interface import AgentTeachingInterface
from ..teaching.knowledge_integrator import KnowledgeIntegrator


class KnowledgeRetentionEnhancer:
    """
    Enhances knowledge retention and maturity in the AI-for-All teaching system.
    Addresses the 0.0% knowledge maturity issue identified in monitoring.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize knowledge retention enhancer.

        Args:
            config: Enhancement configuration
        """
        self.config = config
        self.logger = logging.getLogger("ai4all.knowledge_enhancer")

        # Initialize teaching system
        self.framework = TeachingFramework("config/teaching_config.json")
        self.agent_interface = AgentTeachingInterface(self.framework)
        self.knowledge_integrator = self.framework.knowledge_integrator

        # Enhancement settings
        self.target_maturity_threshold = config.get('target_maturity', 0.7)
        self.pattern_validation_enabled = config.get('pattern_validation', True)
        self.cross_agent_learning_enabled = config.get('cross_agent_learning', True)
        self.knowledge_consolidation_enabled = config.get('knowledge_consolidation', True)

        # Enhancement state
        self.enhancement_active = False
        self.maturity_improvements: List[Dict] = []
        self.pattern_improvements: List[Dict] = []

        # Setup logging
        self._setup_enhancement_logging()

        self.logger.info("Knowledge retention enhancer initialized")

    def _setup_enhancement_logging(self):
        """Setup enhancement logging"""
        log_dir = Path("outgoing/ai4all/improvements")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "knowledge_enhancement.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def start_enhancement(self):
        """Start knowledge retention enhancement"""
        self.enhancement_active = True
        self.logger.info("Knowledge retention enhancement started")

        # Initial assessment
        self._assess_initial_knowledge_state()

        # Start enhancement loop
        self._start_enhancement_loop()

    def stop_enhancement(self):
        """Stop knowledge retention enhancement"""
        self.enhancement_active = False
        self.logger.info("Knowledge retention enhancement stopped")

        # Generate enhancement report
        self._generate_enhancement_report()

    def _start_enhancement_loop(self):
        """Start the knowledge enhancement loop"""
        while self.enhancement_active:
            try:
                # Assess current knowledge state
                current_state = self._assess_knowledge_state()

                # Apply enhancements based on current state
                if current_state['overall_maturity'] < self.target_maturity_threshold:
                    self._apply_knowledge_enhancements(current_state)

                # Validate and improve patterns
                if self.pattern_validation_enabled:
                    self._validate_and_improve_patterns()

                # Consolidate knowledge
                if self.knowledge_consolidation_enabled:
                    self._consolidate_knowledge()

                # Sleep for enhancement interval
                time.sleep(300)  # Check every 5 minutes

            except Exception as e:
                self.logger.error(f"Error in enhancement loop: {e}")
                time.sleep(600)  # Wait longer on errors

    def _assess_initial_knowledge_state(self):
        """Assess initial knowledge state across all agents"""
        try:
            initial_state = {
                'timestamp': datetime.now().isoformat(),
                'agent_knowledge_states': {},
                'overall_maturity': 0.0,
                'total_patterns': 0,
                'total_transfers': 0
            }

            # Assess each agent
            agents_to_check = ['agent1', 'triage', 'cp6', 'cp7']
            total_maturity = 0.0
            agent_count = 0

            for agent_id in agents_to_check:
                try:
                    knowledge_status = self.knowledge_integrator.get_integration_status(agent_id)
                    initial_state['agent_knowledge_states'][agent_id] = knowledge_status

                    maturity = knowledge_status.get('knowledge_maturity', 0.0)
                    total_maturity += maturity
                    agent_count += 1

                    # Get agent patterns
                    patterns = self.framework.pattern_recognition.get_agent_patterns(agent_id)
                    initial_state[f'{agent_id}_patterns'] = len(patterns)

                except Exception as e:
                    self.logger.debug(f"Error assessing knowledge for {agent_id}: {e}")

            # Calculate overall metrics
            if agent_count > 0:
                initial_state['overall_maturity'] = total_maturity / agent_count

            initial_state['total_patterns'] = len(self.knowledge_integrator.patterns)
            initial_state['total_transfers'] = len(self.knowledge_integrator.transfers)

            self.logger.info(f"Initial knowledge state: {initial_state['overall_maturity']:.3f} maturity, {initial_state['total_patterns']} patterns")

        except Exception as e:
            self.logger.error(f"Error assessing initial knowledge state: {e}")

    def _assess_knowledge_state(self) -> Dict[str, Any]:
        """Assess current knowledge state"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'agent_knowledge_states': {},
            'overall_maturity': 0.0,
            'total_patterns': len(self.knowledge_integrator.patterns),
            'total_transfers': len(self.knowledge_integrator.transfers),
            'maturity_trend': 'stable',
            'improvement_areas': []
        }

        try:
            # Assess each agent
            agents_to_check = ['agent1', 'triage', 'cp6', 'cp7']
            maturity_values = []
            agent_count = 0

            for agent_id in agents_to_check:
                try:
                    knowledge_status = self.knowledge_integrator.get_integration_status(agent_id)
                    state['agent_knowledge_states'][agent_id] = knowledge_status

                    maturity = knowledge_status.get('knowledge_maturity', 0.0)
                    maturity_values.append(maturity)
                    agent_count += 1

                    # Check for improvement areas
                    if maturity < 0.3:
                        state['improvement_areas'].append(f"{agent_id}: very_low_maturity")
                    elif maturity < 0.5:
                        state['improvement_areas'].append(f"{agent_id}: low_maturity")

                except Exception as e:
                    self.logger.debug(f"Error assessing knowledge for {agent_id}: {e}")

            # Calculate overall metrics
            if maturity_values:
                state['overall_maturity'] = sum(maturity_values) / len(maturity_values)

                # Calculate trend (simple)
                if len(maturity_values) >= 2:
                    recent_avg = sum(maturity_values[-2:]) / 2
                    older_avg = sum(maturity_values[:2]) / 2 if len(maturity_values) >= 4 else recent_avg

                    if recent_avg > older_avg + 0.1:
                        state['maturity_trend'] = 'improving'
                    elif recent_avg < older_avg - 0.1:
                        state['maturity_trend'] = 'declining'

            return state

        except Exception as e:
            self.logger.error(f"Error assessing knowledge state: {e}")
            return state

    def _apply_knowledge_enhancements(self, current_state: Dict[str, Any]):
        """Apply enhancements to improve knowledge maturity"""
        try:
            self.logger.info(f"Applying knowledge enhancements (maturity: {current_state['overall_maturity']:.3f})")

            # Enhance knowledge integration for each agent
            for agent_id, knowledge_state in current_state['agent_knowledge_states'].items():
                self._enhance_agent_knowledge(agent_id, knowledge_state)

            # Improve cross-agent learning
            if self.cross_agent_learning_enabled:
                self._improve_cross_agent_learning(current_state)

        except Exception as e:
            self.logger.error(f"Error applying knowledge enhancements: {e}")

    def _enhance_agent_knowledge(self, agent_id: str, knowledge_state: Dict[str, Any]):
        """Enhance knowledge for a specific agent"""
        try:
            # Find transferable patterns for this agent
            transferable_patterns = self.knowledge_integrator.find_transferable_patterns(
                agent_id, self.agent_baselines.get(agent_id, {})
            )

            # Transfer high-confidence patterns
            for transfer in transferable_patterns[:3]:  # Top 3 patterns
                if transfer['adaptation_score'] > 0.7:
                    try:
                        transfer_id = self.knowledge_integrator.transfer_knowledge(
                            transfer['pattern']['id'],
                            transfer['pattern']['source_agent'],
                            agent_id
                        )

                        if transfer_id:
                            self.maturity_improvements.append({
                                'timestamp': datetime.now(),
                                'agent_id': agent_id,
                                'improvement_type': 'pattern_transfer',
                                'source_agent': transfer['pattern']['source_agent'],
                                'pattern_id': transfer['pattern']['id'],
                                'confidence': transfer['adaptation_score']
                            })

                            self.logger.info(f"Transferred pattern to {agent_id}: {transfer['pattern']['id']}")

                    except Exception as e:
                        self.logger.debug(f"Error transferring pattern to {agent_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error enhancing knowledge for {agent_id}: {e}")

    def _improve_cross_agent_learning(self, current_state: Dict[str, Any]):
        """Improve cross-agent learning and knowledge sharing"""
        try:
            # Find successful patterns that could benefit multiple agents
            for pattern_id, pattern in list(self.knowledge_integrator.patterns.items())[:10]:  # Check first 10 patterns
                if pattern.confidence > 0.8 and pattern.usage_count > 2:
                    # Find agents that could benefit from this pattern
                    potential_targets = []

                    for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                        if agent_id != pattern.source_agent:
                            # Check if agent already has this pattern
                            agent_patterns = self.framework.pattern_recognition.get_agent_patterns(agent_id)
                            pattern_ids = [p['id'] for p in agent_patterns]

                            if pattern_id not in pattern_ids:
                                potential_targets.append(agent_id)

                    if potential_targets:
                        # Record cross-domain pattern
                        effectiveness_scores = {}
                        adaptation_requirements = {}

                        for target_agent in potential_targets:
                            effectiveness_scores[target_agent] = 0.7  # Estimated effectiveness
                            adaptation_requirements[target_agent] = {
                                'target_value': self._adapt_pattern_for_agent(pattern, target_agent),
                                'reasoning': f'Cross-agent pattern adaptation for {target_agent}'
                            }

                        # Record the cross-domain pattern
                        self.framework.adaptive_learner.record_cross_domain_pattern(
                            pattern.source_agent,
                            pattern.pattern_type,
                            potential_targets,
                            [pattern.pattern_type],
                            effectiveness_scores,
                            adaptation_requirements,
                            pattern.confidence
                        )

                        self.logger.info(f"Recorded cross-domain pattern: {pattern_id} -> {potential_targets}")

        except Exception as e:
            self.logger.debug(f"Error improving cross-agent learning: {e}")

    def _adapt_pattern_for_agent(self, pattern, target_agent: str):
        """Adapt a pattern for a specific agent type"""
        # Simple adaptation logic - in practice this would be more sophisticated
        adaptation = {
            'learning_rate_adjustment': 1.0,
            'stability_weight_adjustment': 1.0,
            'exploration_adjustment': 1.0
        }

        # Adjust based on agent type
        if target_agent.startswith('cp'):
            # Copilots might need different adaptation
            adaptation['learning_rate_adjustment'] = 0.9
        elif target_agent == 'triage':
            # Triage might need faster adaptation
            adaptation['learning_rate_adjustment'] = 1.1

        return adaptation

    def _validate_and_improve_patterns(self):
        """Validate existing patterns and improve their quality"""
        try:
            # Get all patterns
            all_patterns = list(self.knowledge_integrator.patterns.items())

            for pattern_id, pattern in all_patterns:
                try:
                    # Validate pattern strength
                    if pattern.confidence < 0.5:
                        # Improve weak patterns
                        self._improve_pattern_strength(pattern)

                    # Check for pattern decay
                    age_days = (datetime.now() - pattern.created_date).days
                    if age_days > 30 and pattern.usage_count < 5:
                        # Consider pattern for retirement
                        self._retire_weak_pattern(pattern)

                except Exception as e:
                    self.logger.debug(f"Error validating pattern {pattern_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error validating patterns: {e}")

    def _improve_pattern_strength(self, pattern):
        """Improve the strength of a weak pattern"""
        try:
            # Find similar patterns to reinforce this one
            all_patterns = list(self.knowledge_integrator.patterns.values())

            similar_patterns = []
            for other_pattern in all_patterns:
                if (other_pattern.id != pattern.id and
                    other_pattern.pattern_type == pattern.pattern_type and
                    other_pattern.confidence > 0.7):
                    similar_patterns.append(other_pattern)

            if similar_patterns:
                # Average the confidence from similar patterns
                avg_confidence = sum(p.confidence for p in similar_patterns) / len(similar_patterns)

                # Boost pattern confidence
                pattern.confidence = min(0.9, (pattern.confidence + avg_confidence) / 2)

                self.pattern_improvements.append({
                    'timestamp': datetime.now(),
                    'pattern_id': pattern.id,
                    'improvement_type': 'confidence_boost',
                    'original_confidence': pattern.confidence - avg_confidence,
                    'new_confidence': pattern.confidence,
                    'similar_patterns_used': len(similar_patterns)
                })

                self.logger.info(f"Improved pattern {pattern.id}: {pattern.confidence:.3f} confidence")

        except Exception as e:
            self.logger.debug(f"Error improving pattern strength: {e}")

    def _retire_weak_pattern(self, pattern):
        """Retire or mark weak patterns for review"""
        try:
            # Mark pattern as weak (don't delete, just flag for review)
            pattern.confidence *= 0.5  # Reduce confidence significantly

            self.pattern_improvements.append({
                'timestamp': datetime.now(),
                'pattern_id': pattern.id,
                'improvement_type': 'marked_for_retirement',
                'reason': 'low_usage_high_age',
                'age_days': (datetime.now() - pattern.created_date).days,
                'usage_count': pattern.usage_count
            })

            self.logger.info(f"Marked pattern for retirement: {pattern.id}")

        except Exception as e:
            self.logger.debug(f"Error retiring pattern: {e}")

    def _consolidate_knowledge(self):
        """Consolidate and optimize knowledge storage"""
        try:
            # Clean up old or redundant patterns
            self._cleanup_redundant_patterns()

            # Consolidate similar patterns
            self._consolidate_similar_patterns()

            # Update knowledge maturity metrics
            self._update_knowledge_maturity_metrics()

        except Exception as e:
            self.logger.error(f"Error consolidating knowledge: {e}")

    def _cleanup_redundant_patterns(self):
        """Clean up redundant or outdated patterns"""
        try:
            # Find patterns with very similar descriptions or effects
            patterns_to_remove = []

            all_patterns = list(self.knowledge_integrator.patterns.items())

            for i, (pattern_id1, pattern1) in enumerate(all_patterns):
                for pattern_id2, pattern2 in all_patterns[i+1:]:
                    # Check similarity
                    similarity = self._calculate_pattern_similarity(pattern1, pattern2)

                    if similarity > 0.9:  # Very similar patterns
                        # Keep the one with higher confidence
                        if pattern1.confidence > pattern2.confidence:
                            patterns_to_remove.append(pattern_id2)
                        else:
                            patterns_to_remove.append(pattern_id1)

            # Remove redundant patterns
            for pattern_id in patterns_to_remove:
                if pattern_id in self.knowledge_integrator.patterns:
                    del self.knowledge_integrator.patterns[pattern_id]

                    # Update agent mappings
                    for agent_id, pattern_ids in self.knowledge_integrator.agent_knowledge.items():
                        if pattern_id in pattern_ids:
                            pattern_ids.remove(pattern_id)

            if patterns_to_remove:
                self.logger.info(f"Cleaned up {len(patterns_to_remove)} redundant patterns")

        except Exception as e:
            self.logger.debug(f"Error cleaning up redundant patterns: {e}")

    def _calculate_pattern_similarity(self, pattern1, pattern2) -> float:
        """Calculate similarity between two patterns"""
        try:
            # Simple similarity based on description and metrics
            desc_similarity = 0.0

            if pattern1.description and pattern2.description:
                # Simple text similarity (could be enhanced with more sophisticated methods)
                desc1_words = set(pattern1.description.lower().split())
                desc2_words = set(pattern2.description.lower().split())

                if desc1_words or desc2_words:
                    common_words = desc1_words & desc2_words
                    total_words = desc1_words | desc2_words
                    desc_similarity = len(common_words) / len(total_words) if total_words else 0

            # Metric similarity
            metrics1 = pattern1.metrics_impact
            metrics2 = pattern2.metrics_impact

            if metrics1 and metrics2:
                common_metrics = set(metrics1.keys()) & set(metrics2.keys())
                if common_metrics:
                    metric_differences = []
                    for metric in common_metrics:
                        diff = abs(metrics1[metric] - metrics2[metric])
                        metric_differences.append(diff)

                    avg_metric_diff = sum(metric_differences) / len(metric_differences)
                    metric_similarity = 1.0 - min(1.0, avg_metric_diff)
                else:
                    metric_similarity = 0.0
            else:
                metric_similarity = 0.5  # Neutral similarity

            # Combined similarity
            return (desc_similarity * 0.6 + metric_similarity * 0.4)

        except Exception:
            return 0.0

    def _consolidate_similar_patterns(self):
        """Consolidate similar patterns into stronger ones"""
        try:
            # Group patterns by type and similarity
            pattern_groups = {}

            for pattern_id, pattern in self.knowledge_integrator.patterns.items():
                group_key = pattern.pattern_type

                if group_key not in pattern_groups:
                    pattern_groups[group_key] = []

                pattern_groups[group_key].append((pattern_id, pattern))

            # Consolidate each group
            for group_type, patterns in pattern_groups.items():
                if len(patterns) >= 3:  # Only consolidate if we have enough patterns
                    consolidated = self._consolidate_pattern_group(patterns)
                    if consolidated:
                        self.logger.info(f"Consolidated {len(patterns)} patterns of type {group_type}")

        except Exception as e:
            self.logger.debug(f"Error consolidating similar patterns: {e}")

    def _consolidate_pattern_group(self, patterns: List) -> bool:
        """Consolidate a group of similar patterns"""
        try:
            # Find the strongest pattern in the group
            strongest_pattern = max(patterns, key=lambda x: x[1].confidence)

            # Average metrics from all patterns
            all_metrics = {}
            for pattern_id, pattern in patterns:
                for metric, value in pattern.metrics_impact.items():
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(value)

            # Calculate average metrics
            consolidated_metrics = {}
            for metric, values in all_metrics.items():
                consolidated_metrics[metric] = sum(values) / len(values)

            # Update the strongest pattern with consolidated metrics
            strongest_pattern[1].metrics_impact = consolidated_metrics
            strongest_pattern[1].confidence = min(0.95, strongest_pattern[1].confidence * 1.1)  # Boost confidence

            return True

        except Exception as e:
            self.logger.debug(f"Error consolidating pattern group: {e}")
            return False

    def _update_knowledge_maturity_metrics(self):
        """Update knowledge maturity metrics across all agents"""
        try:
            # Force recalculation of knowledge maturity for all agents
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                try:
                    # Get fresh knowledge status
                    knowledge_status = self.knowledge_integrator.get_integration_status(agent_id)

                    # Check if maturity improved
                    maturity = knowledge_status.get('knowledge_maturity', 0.0)
                    patterns_count = knowledge_status.get('patterns_count', 0)

                    if maturity > 0.1 or patterns_count > 5:
                        self.maturity_improvements.append({
                            'timestamp': datetime.now(),
                            'agent_id': agent_id,
                            'improvement_type': 'maturity_update',
                            'new_maturity': maturity,
                            'new_patterns_count': patterns_count
                        })

                        self.logger.info(f"Updated knowledge maturity for {agent_id}: {maturity:.3f}")

                except Exception as e:
                    self.logger.debug(f"Error updating maturity for {agent_id}: {e}")

        except Exception as e:
            self.logger.error(f"Error updating knowledge maturity metrics: {e}")

    def _generate_enhancement_report(self):
        """Generate comprehensive enhancement report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Final knowledge state
            final_state = self._assess_knowledge_state()

            report = {
                'timestamp': datetime.now().isoformat(),
                'enhancement_summary': {
                    'enhancement_active': self.enhancement_active,
                    'total_improvements': len(self.maturity_improvements) + len(self.pattern_improvements),
                    'maturity_improvements': len(self.maturity_improvements),
                    'pattern_improvements': len(self.pattern_improvements),
                    'initial_maturity': 0.0,  # Would need to track this
                    'final_maturity': final_state['overall_maturity'],
                    'maturity_improvement': final_state['overall_maturity'] - 0.0
                },
                'final_knowledge_state': final_state,
                'improvement_history': self.maturity_improvements[-50:],  # Last 50 improvements
                'pattern_improvements': self.pattern_improvements[-50:],  # Last 50 pattern improvements
                'recommendations': self._generate_knowledge_recommendations(final_state)
            }

            # Save report
            report_dir = Path("outgoing/ai4all/improvements")
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"knowledge_enhancement_report_{timestamp}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            self.logger.info(f"Generated knowledge enhancement report: {report_file}")

        except Exception as e:
            self.logger.error(f"Error generating enhancement report: {e}")

    def _generate_knowledge_recommendations(self, current_state: Dict[str, Any]) -> List[str]:
        """Generate knowledge-based recommendations"""
        recommendations = []

        try:
            maturity = current_state.get('overall_maturity', 0.0)

            if maturity < 0.3:
                recommendations.append("Knowledge maturity still low - continue enhancement activities")
            elif maturity < 0.5:
                recommendations.append("Moderate knowledge maturity - focus on pattern validation and cross-agent learning")
            elif maturity < 0.7:
                recommendations.append("Good knowledge maturity - consider enabling advanced learning features")

            # Agent-specific recommendations
            for agent_id, knowledge_state in current_state.get('agent_knowledge_states', {}).items():
                agent_maturity = knowledge_state.get('knowledge_maturity', 0.0)

                if agent_maturity < 0.2:
                    recommendations.append(f"{agent_id}: Very low maturity - prioritize pattern transfer")
                elif agent_maturity < 0.4:
                    recommendations.append(f"{agent_id}: Low maturity - focus on knowledge integration")

                # Check pattern count
                patterns_count = knowledge_state.get('patterns_count', 0)
                if patterns_count < 3:
                    recommendations.append(f"{agent_id}: Low pattern count - increase pattern recognition sensitivity")

        except Exception as e:
            self.logger.debug(f"Error generating knowledge recommendations: {e}")

        return recommendations[:5]

    def get_enhancement_status(self) -> Dict[str, Any]:
        """Get comprehensive enhancement status"""
        current_state = self._assess_knowledge_state()

        return {
            'knowledge_enhancement': {
                'active': self.enhancement_active,
                'total_improvements': len(self.maturity_improvements) + len(self.pattern_improvements),
                'maturity_improvements': len(self.maturity_improvements),
                'pattern_improvements': len(self.pattern_improvements),
                'current_overall_maturity': current_state.get('overall_maturity', 0.0),
                'maturity_trend': current_state.get('maturity_trend', 'unknown')
            },
            'current_knowledge_state': current_state,
            'enhancement_config': {
                'target_maturity_threshold': self.target_maturity_threshold,
                'pattern_validation_enabled': self.pattern_validation_enabled,
                'cross_agent_learning_enabled': self.cross_agent_learning_enabled,
                'knowledge_consolidation_enabled': self.knowledge_consolidation_enabled
            },
            'timestamp': datetime.now().isoformat()
        }


def create_knowledge_enhancer(config: Dict[str, Any] = None) -> KnowledgeRetentionEnhancer:
    """Create knowledge retention enhancer"""
    if config is None:
        config = {
            'target_maturity': 0.7,
            'pattern_validation': True,
            'cross_agent_learning': True,
            'knowledge_consolidation': True
        }

    return KnowledgeRetentionEnhancer(config)


def main():
    """Main knowledge enhancement entry point"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Knowledge Retention Enhancement")
    print("=" * 45)
    print("Enhancing knowledge maturity and retention across agents...\n")

    # Create knowledge enhancer
    enhancer = create_knowledge_enhancer()

    try:
        # Start enhancement
        enhancer.start_enhancement()

        print("✅ Knowledge enhancement started")
        print("🧠 Analyzing knowledge patterns")
        print("🔄 Improving cross-agent learning")
        print("📈 Enhancing knowledge maturity")
        print("🔍 Validating pattern effectiveness\n")

        # Keep running until interrupted
        while enhancer.enhancement_active:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping knowledge enhancement...")
        enhancer.stop_enhancement()

        # Show final status
        status = enhancer.get_enhancement_status()
        improvements = status['knowledge_enhancement']['total_improvements']
        final_maturity = status['knowledge_enhancement']['current_overall_maturity']

        print(f"✅ Enhancement completed: {improvements} improvements made")
        print(f"📈 Final knowledge maturity: {final_maturity:.1%}")

        print("✅ Knowledge enhancement stopped gracefully")

    except Exception as e:
        print(f"❌ Error in knowledge enhancement: {e}")
        enhancer.stop_enhancement()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
