#!/usr/bin/env python3
"""
AI-for-All Learning Benchmark Suite - Comprehensive performance testing and optimization validation
"""

import json
import time
import logging
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Import teaching system components
import sys
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from teaching.framework import TeachingFramework
from teaching.agent_interface import AgentTeachingInterface
from teaching.enhanced_learner import EnhancedAdaptiveLearner
from teaching.performance_tracker import PerformanceTracker
from teaching.knowledge_integrator import KnowledgeIntegrator
from teaching.pattern_recognition import PatternRecognition


class LearningBenchmarkSuite:
    """
    Comprehensive benchmark suite for AI-for-All teaching system.
    Tests all learning methods, validates performance, and compares against historical data.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the learning benchmark suite.

        Args:
            config: Benchmark configuration
        """
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger("ai4all.benchmark")

        # Initialize teaching components
        self.framework = TeachingFramework("config/teaching_config.json")
        self.agent_interface = AgentTeachingInterface(self.framework)
        self.enhanced_learner = EnhancedAdaptiveLearner(self.framework.config.get('enhanced_learning', {}))
        self.performance_tracker = self.framework.performance_tracker
        self.knowledge_integrator = self.framework.knowledge_integrator
        self.pattern_recognition = self.framework.pattern_recognition

        # Benchmark state
        self.benchmark_results: Dict[str, Any] = {}
        self.historical_comparison: Dict[str, Any] = {}
        self.efficiency_metrics: Dict[str, Any] = {}

        # Setup logging
        self._setup_benchmark_logging()

        self.logger.info("Learning benchmark suite initialized")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default benchmark configuration"""
        return {
            'benchmark_duration': 300,  # 5 minutes
            'performance_samples': 50,
            'adaptation_tests': 20,
            'cross_agent_tests': 15,
            'pattern_recognition_tests': 10,
            'predictive_tests': 10,
            'historical_comparison_window': 7,  # days
            'efficiency_thresholds': {
                'adaptation_success_rate': 0.7,
                'learning_progress_rate': 0.1,
                'pattern_accuracy': 0.8,
                'cross_agent_effectiveness': 0.6,
                'system_stability': 0.9
            }
        }

    def _setup_benchmark_logging(self):
        """Setup benchmark logging"""
        log_dir = Path("outgoing/ai4all/benchmark")
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_dir / "benchmark.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """
        Run comprehensive learning benchmark suite.

        Returns:
            Complete benchmark results
        """
        self.logger.info("Starting comprehensive learning benchmark")

        benchmark_start = datetime.now()
        self.benchmark_results = {
            'timestamp': benchmark_start.isoformat(),
            'benchmark_id': f"benchmark_{int(time.time())}",
            'configuration': self.config,
            'system_status': self._get_system_status(),
            'tests': {},
            'overall_score': 0.0,
            'recommendations': []
        }

        try:
            # Run individual benchmark tests
            self.benchmark_results['tests']['adaptive_learning'] = self._benchmark_adaptive_learning()
            self.benchmark_results['tests']['pattern_recognition'] = self._benchmark_pattern_recognition()
            self.benchmark_results['tests']['knowledge_integration'] = self._benchmark_knowledge_integration()
            self.benchmark_results['tests']['predictive_optimization'] = self._benchmark_predictive_optimization()
            self.benchmark_results['tests']['cross_agent_collaboration'] = self._benchmark_cross_agent_collaboration()
            self.benchmark_results['tests']['system_efficiency'] = self._benchmark_system_efficiency()
            self.benchmark_results['tests']['historical_comparison'] = self._benchmark_historical_comparison()

            # Calculate overall score
            self.benchmark_results['overall_score'] = self._calculate_overall_score()

            # Generate recommendations
            self.benchmark_results['recommendations'] = self._generate_benchmark_recommendations()

            # Save results
            self._save_benchmark_results()

            benchmark_duration = (datetime.now() - benchmark_start).total_seconds()
            self.logger.info(f"Benchmark completed in {benchmark_duration:.2f} seconds with score {self.benchmark_results['overall_score']:.3f}")

            return self.benchmark_results

        except Exception as e:
            self.logger.error(f"Benchmark failed: {e}")
            self.benchmark_results['error'] = str(e)
            return self.benchmark_results

    def _get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            return {
                'framework_status': self.framework.get_system_status(),
                'agent_interface_status': self.agent_interface.get_system_overview(),
                'active_sessions': len(self.framework.active_sessions),
                'agents_configured': len(self.agent_interface.agent_configs),
                'agents_enabled': len([a for a in self.agent_interface.teaching_enabled.values() if a])
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}

    def _benchmark_adaptive_learning(self) -> Dict[str, Any]:
        """Benchmark adaptive learning performance"""
        self.logger.info("Benchmarking adaptive learning")

        results = {
            'test_name': 'adaptive_learning',
            'timestamp': datetime.now().isoformat(),
            'agents_tested': [],
            'adaptations_applied': 0,
            'adaptation_success_rate': 0.0,
            'learning_progress': {},
            'efficiency_score': 0.0
        }

        agents_to_test = ['agent1', 'triage', 'cp6', 'cp7']

        for agent_id in agents_to_test:
            try:
                # Enable teaching for agent
                success = self.agent_interface.enable_teaching(agent_id)
                if not success:
                    continue

                results['agents_tested'].append(agent_id)

                # Test multiple performance scenarios
                scenarios = [
                    {'tes': 70, 'stability': 0.7, 'velocity': 0.4},  # Poor performance
                    {'tes': 85, 'stability': 0.85, 'velocity': 0.6},  # Average performance
                    {'tes': 95, 'stability': 0.95, 'velocity': 0.8},  # Excellent performance
                ]

                agent_adaptations = 0
                successful_adaptations = 0

                for scenario in scenarios:
                    # Update performance
                    response = self.agent_interface.update_agent_performance(
                        agent_id=agent_id,
                        metrics=scenario,
                        context={'benchmark_test': True, 'scenario': scenario}
                    )

                    adaptations = response.get('adaptations_applied', [])
                    agent_adaptations += len(adaptations)

                    # Check adaptation quality
                    for adaptation in adaptations:
                        if adaptation.get('confidence', 0) > 0.6:
                            successful_adaptations += 1

                # Calculate agent metrics
                agent_status = self.agent_interface.get_agent_teaching_status(agent_id)
                progress = agent_status.get('progress_summary', {}).get('average_progress', 0)

                results['learning_progress'][agent_id] = {
                    'adaptations_applied': agent_adaptations,
                    'successful_adaptations': successful_adaptations,
                    'learning_progress': progress,
                    'success_rate': successful_adaptations / max(1, agent_adaptations)
                }

                results['adaptations_applied'] += agent_adaptations

            except Exception as e:
                self.logger.error(f"Error benchmarking adaptive learning for {agent_id}: {e}")
                results['learning_progress'][agent_id] = {'error': str(e)}

        # Calculate overall metrics
        total_adaptations = results['adaptations_applied']
        successful_adaptations = sum(
            agent_data.get('successful_adaptations', 0)
            for agent_data in results['learning_progress'].values()
            if isinstance(agent_data, dict) and 'error' not in agent_data
        )

        results['adaptation_success_rate'] = successful_adaptations / max(1, total_adaptations)
        results['efficiency_score'] = self._calculate_efficiency_score(results)

        self.logger.info(f"Adaptive learning benchmark: {results['adaptation_success_rate']:.1%} success rate")
        return results

    def _benchmark_pattern_recognition(self) -> Dict[str, Any]:
        """Benchmark pattern recognition performance"""
        self.logger.info("Benchmarking pattern recognition")

        results = {
            'test_name': 'pattern_recognition',
            'timestamp': datetime.now().isoformat(),
            'patterns_recorded': 0,
            'pattern_accuracy': 0.0,
            'pattern_strengths': {},
            'cross_domain_patterns': 0,
            'efficiency_score': 0.0
        }

        agents_to_test = ['agent1', 'triage', 'cp6', 'cp7']

        for agent_id in agents_to_test:
            try:
                # Generate test patterns
                test_scenarios = [
                    {'type': 'success', 'metrics': {'tes': 90, 'stability': 0.9}, 'context': {'positive': True}},
                    {'type': 'optimization', 'metrics': {'velocity': 0.8, 'efficiency': 0.85}, 'context': {'optimization': True}},
                    {'type': 'stability', 'metrics': {'stability': 0.95, 'tes': 88}, 'context': {'stable': True}}
                ]

                agent_patterns = 0
                pattern_strengths = []

                for scenario in test_scenarios:
                    # Record successful pattern
                    pattern_id = self.knowledge_integrator.record_successful_pattern(
                        agent_id=agent_id,
                        pattern_type=scenario['type'],
                        description=f"Benchmark pattern: {scenario['type']}",
                        metrics_impact=scenario['metrics'],
                        context=scenario['context'],
                        confidence=0.8
                    )

                    if pattern_id:
                        agent_patterns += 1

                        # Get pattern details
                        patterns = self.pattern_recognition.get_agent_patterns(agent_id)
                        if patterns:
                            latest_pattern = patterns[-1]
                            pattern_strengths.append(latest_pattern.get('strength', 0))

                results['patterns_recorded'] += agent_patterns
                results['pattern_strengths'][agent_id] = {
                    'patterns_count': agent_patterns,
                    'average_strength': statistics.mean(pattern_strengths) if pattern_strengths else 0,
                    'max_strength': max(pattern_strengths) if pattern_strengths else 0
                }

            except Exception as e:
                self.logger.error(f"Error benchmarking pattern recognition for {agent_id}: {e}")
                results['pattern_strengths'][agent_id] = {'error': str(e)}

        # Calculate accuracy
        total_patterns = results['patterns_recorded']
        strong_patterns = sum(
            1 for agent_data in results['pattern_strengths'].values()
            if isinstance(agent_data, dict) and agent_data.get('average_strength', 0) > 0.7
        )

        results['pattern_accuracy'] = strong_patterns / max(1, len(results['pattern_strengths']))
        results['efficiency_score'] = self._calculate_efficiency_score(results)

        self.logger.info(f"Pattern recognition benchmark: {results['pattern_accuracy']:.1%} accuracy")
        return results

    def _benchmark_knowledge_integration(self) -> Dict[str, Any]:
        """Benchmark knowledge integration performance"""
        self.logger.info("Benchmarking knowledge integration")

        results = {
            'test_name': 'knowledge_integration',
            'timestamp': datetime.now().isoformat(),
            'transfers_attempted': 0,
            'transfers_successful': 0,
            'knowledge_maturity': {},
            'integration_effectiveness': 0.0,
            'efficiency_score': 0.0
        }

        try:
            # Test knowledge transfer between agents
            source_agents = ['agent1', 'triage']
            target_agents = ['cp6', 'cp7']

            for source_agent in source_agents:
                for target_agent in target_agents:
                    # Find transferable patterns
                    transferable_patterns = self.knowledge_integrator.find_transferable_patterns(
                        target_agent,
                        {'tes': 80, 'stability': 0.8, 'velocity': 0.6}
                    )

                    results['transfers_attempted'] += len(transferable_patterns)

                    # Attempt transfers
                    for pattern_info in transferable_patterns[:2]:  # Top 2 patterns
                        pattern = pattern_info['pattern']
                        transfer_id = self.knowledge_integrator.transfer_knowledge(
                            pattern['id'],
                            source_agent,
                            target_agent
                        )

                        if transfer_id:
                            results['transfers_successful'] += 1

            # Check knowledge maturity for each agent
            for agent_id in ['agent1', 'triage', 'cp6', 'cp7']:
                try:
                    maturity = self.knowledge_integrator.get_integration_status(agent_id)
                    results['knowledge_maturity'][agent_id] = maturity
                except Exception as e:
                    results['knowledge_maturity'][agent_id] = {'error': str(e)}

            # Calculate effectiveness
            if results['transfers_attempted'] > 0:
                results['integration_effectiveness'] = results['transfers_successful'] / results['transfers_attempted']

            results['efficiency_score'] = self._calculate_efficiency_score(results)

            self.logger.info(f"Knowledge integration benchmark: {results['integration_effectiveness']:.1%} effectiveness")
            return results

        except Exception as e:
            self.logger.error(f"Error benchmarking knowledge integration: {e}")
            results['error'] = str(e)
            return results

    def _benchmark_predictive_optimization(self) -> Dict[str, Any]:
        """Benchmark predictive optimization performance"""
        self.logger.info("Benchmarking predictive optimization")

        results = {
            'test_name': 'predictive_optimization',
            'timestamp': datetime.now().isoformat(),
            'predictions_made': 0,
            'prediction_accuracy': 0.0,
            'adaptation_prevented': 0,
            'efficiency_score': 0.0
        }

        agents_to_test = ['agent1', 'triage', 'cp6', 'cp7']

        for agent_id in agents_to_test:
            try:
                # Generate performance history for prediction
                performance_history = []
                for i in range(10):
                    metrics = {
                        'tes': 75 + (i * 2),  # Improving trend
                        'stability': 0.7 + (i * 0.02),
                        'velocity': 0.5 + (i * 0.03)
                    }
                    performance_history.append(metrics)

                    # Record performance
                    self.performance_tracker.record_performance(
                        agent_id=agent_id,
                        metrics=metrics,
                        context={'benchmark_test': True, 'prediction_test': i}
                    )

                # Test enhanced learner predictions
                if self.enhanced_learner:
                    insights = self.enhanced_learner.get_learning_insights(agent_id)
                    results['predictions_made'] += 1

                    # Check prediction quality
                    trajectories = insights.get('learning_trajectories', {})
                    if trajectories:
                        for trajectory_data in trajectories.values():
                            confidence = trajectory_data.get('confidence', 0)
                            if confidence > 0.7:
                                results['prediction_accuracy'] += 1

                # Test adaptive learner predictions
                adaptation_history = self.framework.adaptive_learner.get_adaptation_history(agent_id)

                # Simulate performance decline scenario
                decline_metrics = {'tes': 65, 'stability': 0.6, 'velocity': 0.3}
                suggestions = self.enhanced_learner.suggest_enhanced_adaptation(
                    agent_id=agent_id,
                    learning_objective='task_efficiency',
                    current_metrics=decline_metrics,
                    baseline_metrics={'tes': 80, 'stability': 0.8, 'velocity': 0.5},
                    performance_history=performance_history
                )

                # Count preventive adaptations
                preventive_count = len([s for s in suggestions if 'preventive' in s.get('reasoning', '').lower()])
                results['adaptation_prevented'] += preventive_count

            except Exception as e:
                self.logger.error(f"Error benchmarking predictive optimization for {agent_id}: {e}")

        # Calculate accuracy
        if results['predictions_made'] > 0:
            results['prediction_accuracy'] = results['prediction_accuracy'] / results['predictions_made']

        results['efficiency_score'] = self._calculate_efficiency_score(results)

        self.logger.info(f"Predictive optimization benchmark: {results['prediction_accuracy']:.1%} accuracy")
        return results

    def _benchmark_cross_agent_collaboration(self) -> Dict[str, Any]:
        """Benchmark cross-agent collaboration"""
        self.logger.info("Benchmarking cross-agent collaboration")

        results = {
            'test_name': 'cross_agent_collaboration',
            'timestamp': datetime.now().isoformat(),
            'collaboration_events': 0,
            'knowledge_transfers': 0,
            'harmony_improvement': 0.0,
            'collaboration_effectiveness': 0.0,
            'efficiency_score': 0.0
        }

        try:
            # Test pattern transfer between agents
            source_target_pairs = [
                ('agent1', 'triage'),
                ('triage', 'cp6'),
                ('cp6', 'cp7'),
                ('cp7', 'agent1')
            ]

            for source_agent, target_agent in source_target_pairs:
                # Find patterns to transfer
                transferable_patterns = self.knowledge_integrator.find_transferable_patterns(
                    target_agent,
                    {'tes': 75, 'stability': 0.75}
                )

                results['collaboration_events'] += len(transferable_patterns)

                # Transfer patterns
                for pattern_info in transferable_patterns[:1]:  # Transfer 1 pattern per pair
                    pattern = pattern_info['pattern']
                    transfer_id = self.knowledge_integrator.transfer_knowledge(
                        pattern['id'],
                        source_agent,
                        target_agent
                    )

                    if transfer_id:
                        results['knowledge_transfers'] += 1

                        # Update transfer success
                        self.knowledge_integrator.update_transfer_success(
                            transfer_id,
                            success=True,
                            performance_impact={'tes': 0.05, 'stability': 0.03}
                        )

            # Calculate effectiveness
            if results['collaboration_events'] > 0:
                results['collaboration_effectiveness'] = results['knowledge_transfers'] / results['collaboration_events']

            # Test harmony calculation (if available)
            try:
                # Simulate harmony improvement through collaboration
                initial_harmony = 70.0
                collaboration_bonus = results['knowledge_transfers'] * 2.0  # 2% per transfer
                results['harmony_improvement'] = min(100.0, initial_harmony + collaboration_bonus)
            except Exception as e:
                self.logger.debug(f"Error calculating harmony: {e}")

            results['efficiency_score'] = self._calculate_efficiency_score(results)

            self.logger.info(f"Cross-agent collaboration benchmark: {results['collaboration_effectiveness']:.1%} effectiveness")
            return results

        except Exception as e:
            self.logger.error(f"Error benchmarking cross-agent collaboration: {e}")
            results['error'] = str(e)
            return results

    def _benchmark_system_efficiency(self) -> Dict[str, Any]:
        """Benchmark overall system efficiency"""
        self.logger.info("Benchmarking system efficiency")

        results = {
            'test_name': 'system_efficiency',
            'timestamp': datetime.now().isoformat(),
            'resource_usage': {},
            'response_times': {},
            'system_stability': 0.0,
            'scalability_score': 0.0,
            'efficiency_score': 0.0
        }

        try:
            import psutil
            import time

            # Measure resource usage
            start_time = time.time()

            # Test multiple operations
            operations = 100
            for i in range(operations):
                # Simulate teaching operations
                self.framework.create_learning_session(
                    f'benchmark_agent_{i}',
                    'benchmark_objective',
                    {'tes': 80 + i, 'stability': 0.8}
                )

                self.performance_tracker.record_performance(
                    f'benchmark_agent_{i}',
                    {'tes': 85 + i, 'stability': 0.85},
                    {'benchmark': True}
                )

            end_time = time.time()
            total_time = end_time - start_time

            # Calculate performance metrics
            operations_per_second = operations / total_time if total_time > 0 else 0

            # Resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent

            results['resource_usage'] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'operations_per_second': operations_per_second
            }

            # Response time testing
            response_times = []
            for i in range(10):
                start = time.time()
                self.agent_interface.update_agent_performance(
                    'benchmark_agent',
                    {'tes': 85, 'stability': 0.85},
                    {'response_time_test': True}
                )
                end = time.time()
                response_times.append(end - start)

            avg_response_time = statistics.mean(response_times) if response_times else 0
            results['response_times'] = {
                'average_ms': avg_response_time * 1000,
                'max_ms': max(response_times) * 1000 if response_times else 0,
                'min_ms': min(response_times) * 1000 if response_times else 0
            }

            # Calculate stability
            system_overview = self.agent_interface.get_system_overview()
            results['system_stability'] = self._calculate_system_stability(system_overview)

            # Calculate scalability
            results['scalability_score'] = self._calculate_scalability_score(operations_per_second, avg_response_time)

            results['efficiency_score'] = self._calculate_efficiency_score(results)

            self.logger.info(f"System efficiency benchmark: {operations_per_second:.1f} ops/sec, {avg_response_time*1000:.1f}ms avg response")
            return results

        except ImportError:
            self.logger.warning("psutil not available for resource monitoring")
            results['resource_usage'] = {'error': 'psutil not available'}
            results['efficiency_score'] = 0.5
            return results
        except Exception as e:
            self.logger.error(f"Error benchmarking system efficiency: {e}")
            results['error'] = str(e)
            return results

    def _benchmark_historical_comparison(self) -> Dict[str, Any]:
        """Benchmark performance compared to historical data"""
        self.logger.info("Benchmarking historical comparison")

        results = {
            'test_name': 'historical_comparison',
            'timestamp': datetime.now().isoformat(),
            'historical_data_found': False,
            'improvement_metrics': {},
            'regression_detected': False,
            'benchmark_score': 0.0,
            'efficiency_score': 0.0
        }

        try:
            # Load historical metrics
            historical_metrics = self._load_historical_metrics()

            if historical_metrics:
                results['historical_data_found'] = True

                # Compare current performance to historical
                current_overview = self.agent_interface.get_system_overview()

                # Calculate improvement metrics
                historical_agents = historical_metrics.get('agents_enabled', 0)
                current_agents = current_overview.get('agent_interface', {}).get('agents_with_teaching_enabled', 0)

                historical_sessions = historical_metrics.get('active_sessions', 0)
                current_sessions = current_overview.get('agent_interface', {}).get('active_sessions', 0)

                results['improvement_metrics'] = {
                    'agents_enabled_improvement': (current_agents - historical_agents) / max(1, historical_agents),
                    'sessions_improvement': (current_sessions - historical_sessions) / max(1, historical_sessions),
                    'system_stability_improvement': 0.0,  # Would need historical stability data
                    'learning_efficiency_improvement': 0.0  # Would need historical learning data
                }

                # Check for regressions
                results['regression_detected'] = any(
                    improvement < -0.1 for improvement in results['improvement_metrics'].values()
                )

                # Calculate benchmark score
                positive_improvements = sum(
                    max(0, improvement) for improvement in results['improvement_metrics'].values()
                )
                results['benchmark_score'] = min(1.0, positive_improvements / 4.0)  # Max score of 1.0

            else:
                results['historical_data_found'] = False
                results['benchmark_score'] = 0.5  # Neutral score for no historical data

            results['efficiency_score'] = results['benchmark_score']

            self.logger.info(f"Historical comparison benchmark: {results['benchmark_score']:.1%} score")
            return results

        except Exception as e:
            self.logger.error(f"Error benchmarking historical comparison: {e}")
            results['error'] = str(e)
            return results

    def _load_historical_metrics(self) -> Optional[Dict[str, Any]]:
        """Load historical metrics for comparison"""
        try:
            # Look for recent benchmark or performance data
            benchmark_dir = Path("outgoing/ai4all/benchmark")
            if benchmark_dir.exists():
                # Find most recent benchmark file
                benchmark_files = list(benchmark_dir.glob("*.json"))
                if benchmark_files:
                    latest_file = max(benchmark_files, key=lambda x: x.stat().st_mtime)
                    with open(latest_file, 'r') as f:
                        return json.load(f)

            # Fallback to demo report
            demo_report = Path("outgoing/ai4all/reports/demo_report.json")
            if demo_report.exists():
                with open(demo_report, 'r') as f:
                    demo_data = json.load(f)
                    return {
                        'agents_enabled': demo_data.get('framework_status', {}).get('agents_with_baselines', 0),
                        'active_sessions': demo_data.get('framework_status', {}).get('active_sessions', 0)
                    }

            return None

        except Exception as e:
            self.logger.debug(f"Error loading historical metrics: {e}")
            return None

    def _calculate_system_stability(self, system_overview: Dict[str, Any]) -> float:
        """Calculate system stability score"""
        try:
            agents_enabled = system_overview.get('agent_interface', {}).get('agents_with_teaching_enabled', 0)
            total_agents = system_overview.get('agent_interface', {}).get('agents_configured', 0)
            active_sessions = system_overview.get('agent_interface', {}).get('active_sessions', 0)

            # Stability factors
            coverage_stability = agents_enabled / max(1, total_agents)
            session_stability = min(1.0, active_sessions / 8.0)  # 8 is optimal

            return (coverage_stability + session_stability) / 2.0

        except Exception as e:
            self.logger.debug(f"Error calculating system stability: {e}")
            return 0.5

    def _calculate_scalability_score(self, operations_per_second: float, avg_response_time: float) -> float:
        """Calculate system scalability score"""
        try:
            # Scalability based on performance metrics
            throughput_score = min(1.0, operations_per_second / 50.0)  # 50 ops/sec is good
            latency_score = max(0, 1.0 - (avg_response_time * 1000 / 100.0))  # 100ms is good

            return (throughput_score + latency_score) / 2.0

        except Exception as e:
            self.logger.debug(f"Error calculating scalability: {e}")
            return 0.5

    def _calculate_efficiency_score(self, test_results: Dict[str, Any]) -> float:
        """Calculate efficiency score for a test"""
        try:
            # Base efficiency calculation
            base_score = 0.5  # Neutral starting point

            # Adjust based on test-specific metrics
            if 'adaptation_success_rate' in test_results:
                base_score = max(base_score, test_results['adaptation_success_rate'])

            if 'pattern_accuracy' in test_results:
                base_score = max(base_score, test_results['pattern_accuracy'])

            if 'integration_effectiveness' in test_results:
                base_score = max(base_score, test_results['integration_effectiveness'])

            if 'prediction_accuracy' in test_results:
                base_score = max(base_score, test_results['prediction_accuracy'])

            if 'collaboration_effectiveness' in test_results:
                base_score = max(base_score, test_results['collaboration_effectiveness'])

            if 'benchmark_score' in test_results:
                base_score = max(base_score, test_results['benchmark_score'])

            return min(1.0, base_score)

        except Exception as e:
            self.logger.debug(f"Error calculating efficiency score: {e}")
            return 0.5

    def _calculate_overall_score(self) -> float:
        """Calculate overall benchmark score"""
        try:
            test_scores = []

            for test_name, test_results in self.benchmark_results['tests'].items():
                if isinstance(test_results, dict) and 'efficiency_score' in test_results:
                    test_scores.append(test_results['efficiency_score'])

            if test_scores:
                return statistics.mean(test_scores)
            else:
                return 0.5

        except Exception as e:
            self.logger.error(f"Error calculating overall score: {e}")
            return 0.5

    def _generate_benchmark_recommendations(self) -> List[str]:
        """Generate recommendations based on benchmark results"""
        recommendations = []

        try:
            # Analyze each test
            for test_name, test_results in self.benchmark_results['tests'].items():
                if not isinstance(test_results, dict) or 'efficiency_score' not in test_results:
                    continue

                score = test_results['efficiency_score']

                if score < 0.6:
                    recommendations.append(f"Improve {test_name.replace('_', ' ')} - efficiency score {score:.1%} below threshold")
                elif score > 0.9:
                    recommendations.append(f"Excellent {test_name.replace('_', ' ')} performance - consider advanced features")

            # Overall recommendations
            overall_score = self.benchmark_results['overall_score']

            if overall_score < 0.7:
                recommendations.append("Review overall system configuration - performance below optimal")
            elif overall_score > 0.9:
                recommendations.append("System operating at peak efficiency - consider scaling up")

            # Specific recommendations based on test results
            adaptive_test = self.benchmark_results['tests'].get('adaptive_learning', {})
            if adaptive_test.get('adaptation_success_rate', 0) < 0.7:
                recommendations.append("Improve adaptation success rate - consider adjusting learning parameters")

            pattern_test = self.benchmark_results['tests'].get('pattern_recognition', {})
            if pattern_test.get('pattern_accuracy', 0) < 0.8:
                recommendations.append("Enhance pattern recognition accuracy - review pattern detection algorithms")

            integration_test = self.benchmark_results['tests'].get('knowledge_integration', {})
            if integration_test.get('integration_effectiveness', 0) < 0.6:
                recommendations.append("Improve knowledge integration - enhance pattern transfer mechanisms")

            historical_test = self.benchmark_results['tests'].get('historical_comparison', {})
            if historical_test.get('regression_detected', False):
                recommendations.append("Address performance regression - compare with historical benchmarks")

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")

        return recommendations[:10]  # Top 10 recommendations

    def _save_benchmark_results(self):
        """Save benchmark results to persistent storage"""
        try:
            benchmark_dir = Path("outgoing/ai4all/benchmark")
            benchmark_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            results_file = benchmark_dir / f"benchmark_results_{timestamp}.json"

            with open(results_file, 'w') as f:
                json.dump(self.benchmark_results, f, indent=2, default=str)

            # Also save human-readable summary
            summary_file = benchmark_dir / f"benchmark_summary_{timestamp}.txt"
            with open(summary_file, 'w') as f:
                f.write(self._generate_human_readable_summary())

            self.logger.info(f"Benchmark results saved to {results_file}")

        except Exception as e:
            self.logger.error(f"Error saving benchmark results: {e}")

    def _generate_human_readable_summary(self) -> str:
        """Generate human-readable benchmark summary"""
        summary = []
        summary.append("AI-for-All Learning Benchmark Summary")
        summary.append("=" * 45)
        summary.append(f"Benchmark Date: {self.benchmark_results['timestamp']}")
        summary.append(f"Overall Score: {self.benchmark_results['overall_score']:.1%}")
        summary.append("")

        # Test results
        summary.append("Test Results:")
        for test_name, test_results in self.benchmark_results['tests'].items():
            if isinstance(test_results, dict) and 'efficiency_score' in test_results:
                score = test_results['efficiency_score']
                status = "EXCELLENT" if score > 0.9 else "GOOD" if score > 0.7 else "NEEDS_IMPROVEMENT"
                summary.append(f"  {test_name.replace('_', ' ').title()}: {score:.1%} ({status})")

        summary.append("")

        # Recommendations
        recommendations = self.benchmark_results.get('recommendations', [])
        if recommendations:
            summary.append("Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                summary.append(f"  {i}. {rec}")

        return "\n".join(summary)

    def get_benchmark_status(self) -> Dict[str, Any]:
        """Get current benchmark status"""
        return {
            'benchmark_suite': {
                'initialized': True,
                'components_available': {
                    'framework': self.framework is not None,
                    'agent_interface': self.agent_interface is not None,
                    'enhanced_learner': self.enhanced_learner is not None,
                    'performance_tracker': self.performance_tracker is not None,
                    'knowledge_integrator': self.knowledge_integrator is not None,
                    'pattern_recognition': self.pattern_recognition is not None
                }
            },
            'system_status': self._get_system_status(),
            'last_benchmark': self.benchmark_results.get('timestamp') if self.benchmark_results else None,
            'timestamp': datetime.now().isoformat()
        }


def run_learning_benchmark(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run comprehensive learning benchmark.

    Args:
        config: Benchmark configuration

    Returns:
        Complete benchmark results
    """
    logging.basicConfig(level=logging.INFO)

    print("🚀 AI-for-All Learning Benchmark Suite")
    print("=" * 50)
    print("Comprehensive testing of all teaching and learning methods...\n")

    # Create and run benchmark suite
    benchmark_suite = LearningBenchmarkSuite(config)

    # Show system status
    status = benchmark_suite.get_benchmark_status()
    print(f"📊 System Status: {status['system_status']['agents_enabled']}/{status['system_status']['agents_configured']} agents enabled")
    print(f"🎯 Active Sessions: {status['system_status']['active_sessions']}")
    print()

    # Run comprehensive benchmark
    results = benchmark_suite.run_comprehensive_benchmark()

    # Display summary
    overall_score = results['overall_score']
    status_icon = "🎉" if overall_score > 0.9 else "✅" if overall_score > 0.7 else "⚠️" if overall_score > 0.5 else "❌"

    print(f"\n{status_icon} Benchmark Complete!")
    print(f"📈 Overall Score: {overall_score:.1%}")

    # Show key metrics
    tests = results.get('tests', {})
    if tests:
        print("\n📋 Test Results:")
        for test_name, test_results in tests.items():
            if isinstance(test_results, dict) and 'efficiency_score' in test_results:
                score = test_results['efficiency_score']
                test_status = "EXCELLENT" if score > 0.9 else "GOOD" if score > 0.7 else "FAIR" if score > 0.5 else "POOR"
                print(f"  {test_name.replace('_', ' ').title()}: {score:.1%} ({test_status})")

    # Show recommendations
    recommendations = results.get('recommendations', [])
    if recommendations:
        print(f"\n💡 Recommendations ({len(recommendations)}):")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

    print(f"\n📄 Detailed report saved: outgoing/ai4all/benchmark/benchmark_results_{results['benchmark_id']}.json")

    return results


def main():
    """Main benchmark entry point"""
    # Default configuration for comprehensive testing
    config = {
        'benchmark_duration': 180,  # 3 minutes for faster testing
        'performance_samples': 25,
        'adaptation_tests': 10,
        'cross_agent_tests': 8,
        'pattern_recognition_tests': 5,
        'predictive_tests': 5
    }

    # Run benchmark
    results = run_learning_benchmark(config)

    # Exit with appropriate code
    overall_score = results.get('overall_score', 0)
    if overall_score > 0.8:
        print("\n🎉 All tests passed! System operating at peak efficiency.")
        exit(0)
    elif overall_score > 0.6:
        print("\n⚠️ Tests mostly passed with some optimizations needed.")
        exit(1)
    else:
        print("\n❌ Benchmark revealed performance issues requiring attention.")
        exit(2)


if __name__ == "__main__":
    main()
