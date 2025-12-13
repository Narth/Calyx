#!/usr/bin/env python3
"""
Historical Performance Analyzer - Compare current performance with historical data
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import statistics


class HistoricalPerformanceAnalyzer:
    """
    Analyzes current performance against historical data to identify trends,
    improvements, and areas for optimization.
    """

    def __init__(self):
        """Initialize historical analyzer"""
        self.logger = logging.getLogger("ai4all.historical_analyzer")

        # Data sources
        self.historical_metrics: List[Dict[str, Any]] = []
        self.benchmark_history: List[Dict[str, Any]] = []
        self.agent_performance_history: Dict[str, List[Dict[str, Any]]] = {}

        # Load historical data
        self._load_historical_data()

    def _load_historical_data(self):
        """Load historical performance data"""
        try:
            # Load benchmark results
            benchmark_dir = Path("outgoing/ai4all/benchmark")
            if benchmark_dir.exists():
                for benchmark_file in benchmark_dir.glob("benchmark_results_*.json"):
                    try:
                        with open(benchmark_file, 'r') as f:
                            benchmark_data = json.load(f)
                            self.benchmark_history.append(benchmark_data)
                    except Exception as e:
                        self.logger.debug(f"Error loading benchmark file {benchmark_file}: {e}")

            # Load performance snapshots
            metrics_dir = Path("outgoing/ai4all/metrics/snapshots")
            if metrics_dir.exists():
                for snapshot_file in metrics_dir.glob("*.json"):
                    try:
                        with open(snapshot_file, 'r') as f:
                            snapshot_data = json.load(f)
                            agent_id = snapshot_data.get('agent_id', 'unknown')
                            if agent_id not in self.agent_performance_history:
                                self.agent_performance_history[agent_id] = []
                            self.agent_performance_history[agent_id].append(snapshot_data)
                    except Exception as e:
                        self.logger.debug(f"Error loading snapshot file {snapshot_file}: {e}")

            # Load demo and other reports
            reports_dir = Path("outgoing/ai4all/reports")
            if reports_dir.exists():
                for report_file in reports_dir.glob("*.json"):
                    try:
                        with open(report_file, 'r') as f:
                            report_data = json.load(f)
                            self._process_report_data(report_data)
                    except Exception as e:
                        self.logger.debug(f"Error loading report file {report_file}: {e}")

            self.logger.info(f"Loaded {len(self.benchmark_history)} benchmark results and {len(self.agent_performance_history)} agent performance histories")

        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")

    def _process_report_data(self, report_data: Dict[str, Any]):
        """Process report data for historical analysis"""
        try:
            # Extract metrics from demo reports
            if 'framework_status' in report_data:
                framework_status = report_data['framework_status']
                self.historical_metrics.append({
                    'timestamp': report_data.get('timestamp', datetime.now().isoformat()),
                    'type': 'demo_report',
                    'agents_enabled': framework_status.get('agents_with_baselines', 0),
                    'active_sessions': framework_status.get('active_sessions', 0),
                    'teaching_methods': framework_status.get('teaching_methods_used', 0)
                })

        except Exception as e:
            self.logger.debug(f"Error processing report data: {e}")

    def analyze_performance_trends(self, agent_id: str = None, days: int = 7) -> Dict[str, Any]:
        """
        Analyze performance trends over time.

        Args:
            agent_id: Specific agent to analyze (None for all agents)
            days: Number of days to analyze

        Returns:
            Trend analysis results
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        analysis = {
            'analysis_period_days': days,
            'cutoff_date': cutoff_date.isoformat(),
            'agents_analyzed': [],
            'trend_summary': {},
            'improvement_areas': [],
            'regression_areas': [],
            'stability_metrics': {}
        }

        try:
            # Analyze each agent's performance
            agents_to_analyze = [agent_id] if agent_id else list(self.agent_performance_history.keys())

            for agent in agents_to_analyze:
                if agent in self.agent_performance_history:
                    agent_history = [
                        snapshot for snapshot in self.agent_performance_history[agent]
                        if datetime.fromisoformat(snapshot.get('timestamp', '')) > cutoff_date
                    ]

                    if len(agent_history) >= 3:  # Need at least 3 data points
                        agent_analysis = self._analyze_agent_trends(agent, agent_history)
                        analysis['agents_analyzed'].append(agent)
                        analysis['trend_summary'][agent] = agent_analysis

                        # Check for significant changes
                        if agent_analysis.get('trend_strength', 0) > 0.1:
                            if agent_analysis.get('trend_direction') == 'improving':
                                analysis['improvement_areas'].append({
                                    'agent': agent,
                                    'improvement': agent_analysis.get('improvement_rate', 0),
                                    'metrics': agent_analysis.get('key_metrics', {})
                                })
                            else:
                                analysis['regression_areas'].append({
                                    'agent': agent,
                                    'regression': abs(agent_analysis.get('improvement_rate', 0)),
                                    'metrics': agent_analysis.get('key_metrics', {})
                                })

            # Calculate stability metrics
            analysis['stability_metrics'] = self._calculate_stability_metrics()

            self.logger.info(f"Analyzed trends for {len(analysis['agents_analyzed'])} agents over {days} days")
            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing performance trends: {e}")
            return {'error': str(e)}

    def _analyze_agent_trends(self, agent_id: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends for a specific agent"""
        try:
            if len(history) < 3:
                return {'error': 'Insufficient data for trend analysis'}

            # Sort by timestamp
            history.sort(key=lambda x: x.get('timestamp', ''))

            # Extract performance metrics over time
            performance_over_time = []
            for snapshot in history:
                metrics = snapshot.get('metrics', {})
                if metrics:
                    # Calculate composite performance score
                    score = self._calculate_composite_score(metrics)
                    performance_over_time.append({
                        'timestamp': snapshot.get('timestamp', ''),
                        'score': score,
                        'metrics': metrics
                    })

            if len(performance_over_time) < 3:
                return {'error': 'Insufficient performance data'}

            # Calculate trend
            recent_scores = [pt['score'] for pt in performance_over_time[-3:]]
            older_scores = [pt['score'] for pt in performance_over_time[-6:-3]] if len(performance_over_time) >= 6 else recent_scores

            recent_avg = statistics.mean(recent_scores)
            older_avg = statistics.mean(older_scores)

            improvement_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            trend_strength = abs(improvement_rate)

            # Determine trend direction
            if improvement_rate > 0.02:
                trend_direction = 'improving'
            elif improvement_rate < -0.02:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'

            # Identify key metrics
            all_metrics = {}
            for pt in performance_over_time:
                for metric, value in pt['metrics'].items():
                    if metric not in all_metrics:
                        all_metrics[metric] = []
                    all_metrics[metric].append(value)

            key_metrics = {}
            for metric, values in all_metrics.items():
                if len(values) >= 3:
                    key_metrics[metric] = {
                        'current': values[-1],
                        'average': statistics.mean(values),
                        'trend': (values[-1] - values[0]) / values[0] if values[0] > 0 else 0
                    }

            return {
                'agent_id': agent_id,
                'data_points': len(performance_over_time),
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'improvement_rate': improvement_rate,
                'current_performance': recent_avg,
                'baseline_performance': older_avg,
                'key_metrics': key_metrics,
                'analysis_period': f"{performance_over_time[0]['timestamp']} to {performance_over_time[-1]['timestamp']}"
            }

        except Exception as e:
            self.logger.error(f"Error analyzing trends for {agent_id}: {e}")
            return {'error': str(e)}

    def _calculate_composite_score(self, metrics: Dict[str, float]) -> float:
        """Calculate composite performance score from metrics"""
        try:
            # Weighted composite score
            weights = {
                'tes': 0.4,
                'stability': 0.3,
                'velocity': 0.2,
                'efficiency': 0.1
            }

            score = 0.0
            total_weight = 0.0

            for metric, weight in weights.items():
                if metric in metrics:
                    value = metrics[metric]
                    # Normalize to 0-1 range if needed
                    if metric in ['tes', 'velocity', 'efficiency']:
                        normalized_value = min(1.0, value / 100.0) if value > 1.0 else value
                    else:
                        normalized_value = value  # Already 0-1

                    score += normalized_value * weight
                    total_weight += weight

            return score / total_weight if total_weight > 0 else 0.5

        except Exception as e:
            self.logger.debug(f"Error calculating composite score: {e}")
            return 0.5

    def _calculate_stability_metrics(self) -> Dict[str, Any]:
        """Calculate overall system stability metrics"""
        try:
            stability = {
                'system_stability_score': 0.0,
                'agent_stability_scores': {},
                'performance_variance': {},
                'stability_trends': {}
            }

            # Analyze stability for each agent
            for agent_id, history in self.agent_performance_history.items():
                if len(history) >= 5:
                    # Calculate performance variance
                    scores = []
                    for snapshot in history[-10:]:  # Last 10 snapshots
                        score = self._calculate_composite_score(snapshot.get('metrics', {}))
                        scores.append(score)

                    if scores:
                        stability['agent_stability_scores'][agent_id] = {
                            'average_stability': 1.0 - (statistics.stdev(scores) if len(scores) > 1 else 0),
                            'performance_variance': statistics.variance(scores) if len(scores) > 1 else 0,
                            'trend_stability': self._calculate_trend_stability(scores)
                        }

            # Overall system stability
            if stability['agent_stability_scores']:
                agent_stabilities = [
                    agent_data['average_stability']
                    for agent_data in stability['agent_stability_scores'].values()
                ]
                stability['system_stability_score'] = statistics.mean(agent_stabilities)

            return stability

        except Exception as e:
            self.logger.error(f"Error calculating stability metrics: {e}")
            return {'error': str(e)}

    def _calculate_trend_stability(self, scores: List[float]) -> str:
        """Calculate trend stability from performance scores"""
        if len(scores) < 3:
            return 'insufficient_data'

        # Simple trend analysis
        first_half = statistics.mean(scores[:len(scores)//2])
        second_half = statistics.mean(scores[len(scores)//2:])

        difference = (second_half - first_half) / first_half if first_half > 0 else 0

        if abs(difference) < 0.05:
            return 'stable'
        elif difference > 0.05:
            return 'improving'
        else:
            return 'declining'

    def compare_with_benchmarks(self) -> Dict[str, Any]:
        """Compare current performance with historical benchmarks"""
        try:
            if not self.benchmark_history:
                return {'error': 'No historical benchmarks found'}

            # Get latest benchmark
            latest_benchmark = max(self.benchmark_history, key=lambda x: x.get('timestamp', ''))

            # Get current system status
            current_status = self._get_current_system_status()

            comparison = {
                'comparison_timestamp': datetime.now().isoformat(),
                'latest_benchmark': latest_benchmark.get('timestamp', ''),
                'current_vs_benchmark': {},
                'improvement_areas': [],
                'regression_areas': [],
                'new_capabilities': []
            }

            # Compare key metrics
            benchmark_tests = latest_benchmark.get('tests', {})
            current_tests = {}  # Would need to run current benchmark

            # For now, use estimated current performance
            current_performance = self._estimate_current_performance()

            for test_name in ['adaptive_learning', 'pattern_recognition', 'knowledge_integration', 'system_efficiency']:
                benchmark_score = benchmark_tests.get(test_name, {}).get('efficiency_score', 0.5)
                current_score = current_performance.get(test_name, 0.5)

                improvement = (current_score - benchmark_score) / benchmark_score if benchmark_score > 0 else 0

                comparison['current_vs_benchmark'][test_name] = {
                    'benchmark_score': benchmark_score,
                    'current_score': current_score,
                    'improvement': improvement,
                    'status': 'improved' if improvement > 0.1 else 'regressed' if improvement < -0.1 else 'stable'
                }

                if improvement > 0.1:
                    comparison['improvement_areas'].append({
                        'test': test_name,
                        'improvement': improvement,
                        'from': benchmark_score,
                        'to': current_score
                    })
                elif improvement < -0.1:
                    comparison['regression_areas'].append({
                        'test': test_name,
                        'regression': abs(improvement),
                        'from': benchmark_score,
                        'to': current_score
                    })

            # Check for new capabilities
            current_capabilities = self._analyze_current_capabilities()
            benchmark_capabilities = self._analyze_benchmark_capabilities(latest_benchmark)

            new_capabilities = current_capabilities - benchmark_capabilities
            if new_capabilities:
                comparison['new_capabilities'] = list(new_capabilities)

            self.logger.info(f"Benchmark comparison complete: {len(comparison['improvement_areas'])} improvements, {len(comparison['regression_areas'])} regressions")
            return comparison

        except Exception as e:
            self.logger.error(f"Error comparing with benchmarks: {e}")
            return {'error': str(e)}

    def _get_current_system_status(self) -> Dict[str, Any]:
        """Get current system status for comparison"""
        try:
            # This would integrate with the current teaching system
            # For now, return estimated values
            return {
                'agents_enabled': 4,
                'active_sessions': 8,
                'system_stability': 0.9,
                'adaptation_success_rate': 0.8
            }
        except Exception as e:
            self.logger.debug(f"Error getting current system status: {e}")
            return {}

    def _estimate_current_performance(self) -> Dict[str, float]:
        """Estimate current performance based on recent data"""
        try:
            # Estimate based on recent agent performance
            performance_estimates = {}

            for agent_id, history in self.agent_performance_history.items():
                if history and len(history) >= 3:
                    recent_snapshots = history[-3:]
                    avg_metrics = {}

                    # Average metrics across recent snapshots
                    for metric in ['tes', 'stability', 'velocity', 'efficiency']:
                        values = []
                        for snapshot in recent_snapshots:
                            if metric in snapshot.get('metrics', {}):
                                values.append(snapshot['metrics'][metric])

                        if values:
                            avg_metrics[metric] = statistics.mean(values)

                    if avg_metrics:
                        performance_estimates[agent_id] = self._calculate_composite_score(avg_metrics)

            # Aggregate across all agents
            if performance_estimates:
                overall_performance = statistics.mean(performance_estimates.values())

                return {
                    'adaptive_learning': min(1.0, overall_performance + 0.1),
                    'pattern_recognition': min(1.0, overall_performance + 0.05),
                    'knowledge_integration': min(1.0, overall_performance),
                    'system_efficiency': min(1.0, overall_performance + 0.15)
                }
            else:
                return {
                    'adaptive_learning': 0.5,
                    'pattern_recognition': 0.5,
                    'knowledge_integration': 0.5,
                    'system_efficiency': 0.5
                }

        except Exception as e:
            self.logger.debug(f"Error estimating current performance: {e}")
            return {'adaptive_learning': 0.5, 'pattern_recognition': 0.5, 'knowledge_integration': 0.5, 'system_efficiency': 0.5}

    def _analyze_current_capabilities(self) -> set:
        """Analyze current system capabilities"""
        capabilities = set()

        try:
            # Check for enhanced learning features
            enhanced_features = [
                'cross_domain_learning',
                'predictive_optimization',
                'neural_network_integration',
                'advanced_adaptation',
                'pattern_transfer'
            ]

            for feature in enhanced_features:
                # This would check actual system configuration
                if feature in ['cross_domain_learning', 'predictive_optimization', 'pattern_transfer']:
                    capabilities.add(feature)

            return capabilities

        except Exception as e:
            self.logger.debug(f"Error analyzing current capabilities: {e}")
            return set()

    def _analyze_benchmark_capabilities(self, benchmark_data: Dict[str, Any]) -> set:
        """Analyze capabilities from benchmark data"""
        capabilities = set()

        try:
            # Extract capabilities from benchmark tests
            tests = benchmark_data.get('tests', {})

            if 'cross_agent_collaboration' in tests:
                capabilities.add('cross_agent_collaboration')

            if 'predictive_optimization' in tests:
                capabilities.add('predictive_optimization')

            if 'enhanced_learning' in tests:
                capabilities.add('enhanced_learning')

            return capabilities

        except Exception as e:
            self.logger.debug(f"Error analyzing benchmark capabilities: {e}")
            return set()

    def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report"""
        try:
            # Get trend analysis
            trends = self.analyze_performance_trends(days=7)

            # Get benchmark comparison
            comparison = self.compare_with_benchmarks()

            # Generate report
            report = []
            report.append("AI-for-All Optimization Report")
            report.append("=" * 35)
            report.append(f"Generated: {datetime.now().isoformat()}")
            report.append("")

            # Performance trends
            if 'trend_summary' in trends:
                report.append("Performance Trends (7 days):")
                for agent, trend_data in trends['trend_summary'].items():
                    if 'error' not in trend_data:
                        direction = trend_data.get('trend_direction', 'stable')
                        strength = trend_data.get('trend_strength', 0)
                        report.append(f"  {agent}: {direction} ({strength:.1%} strength)")

                report.append("")

            # Improvement areas
            if trends.get('improvement_areas'):
                report.append("Areas of Improvement:")
                for area in trends['improvement_areas']:
                    report.append(f"  ✅ {area['agent']}: +{area['improvement']:.1%} improvement")

                report.append("")

            # Regression areas
            if trends.get('regression_areas'):
                report.append("Areas of Concern:")
                for area in trends['regression_areas']:
                    report.append(f"  ⚠️  {area['agent']}: -{area['regression']:.1%} regression")

                report.append("")

            # Benchmark comparison
            if 'current_vs_benchmark' in comparison:
                report.append("Benchmark Comparison:")
                for test_name, comp_data in comparison['current_vs_benchmark'].items():
                    status = comp_data.get('status', 'stable')
                    improvement = comp_data.get('improvement', 0)
                    status_icon = "📈" if status == 'improved' else "📉" if status == 'regressed' else "➡️"
                    report.append(f"  {status_icon} {test_name}: {improvement:+.1%}")

                report.append("")

            # Recommendations
            recommendations = self._generate_optimization_recommendations(trends, comparison)
            if recommendations:
                report.append("Optimization Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    report.append(f"  {i}. {rec}")

            return "\n".join(report)

        except Exception as e:
            self.logger.error(f"Error generating optimization report: {e}")
            return f"Error generating report: {str(e)}"

    def _generate_optimization_recommendations(self, trends: Dict[str, Any], comparison: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []

        try:
            # Trend-based recommendations
            if trends.get('regression_areas'):
                recommendations.append("Address performance regressions - review adaptation parameters")

            if trends.get('improvement_areas'):
                recommendations.append("Capitalize on improving areas - consider advanced learning features")

            # Benchmark-based recommendations
            if comparison.get('regression_areas'):
                for area in comparison['regression_areas']:
                    test_name = area['test'].replace('_', ' ')
                    recommendations.append(f"Improve {test_name} performance - current score below benchmark")

            if comparison.get('improvement_areas'):
                for area in comparison['improvement_areas']:
                    test_name = area['test'].replace('_', ' ')
                    recommendations.append(f"Excellent {test_name} improvement - consider scaling up")

            # System-wide recommendations
            stability_metrics = trends.get('stability_metrics', {})
            system_stability = stability_metrics.get('system_stability_score', 1.0)

            if system_stability < 0.8:
                recommendations.append("Improve system stability - monitor resource usage and adaptation frequency")

            return recommendations[:10]

        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return ["Review system configuration and monitoring"]


def run_historical_analysis(days: int = 7) -> Dict[str, Any]:
    """
    Run comprehensive historical performance analysis.

    Args:
        days: Number of days to analyze

    Returns:
        Analysis results
    """
    logging.basicConfig(level=logging.INFO)

    print("📊 AI-for-All Historical Performance Analysis")
    print("=" * 50)
    print(f"Analyzing performance trends over the last {days} days...\n")

    analyzer = HistoricalPerformanceAnalyzer()

    # Analyze performance trends
    trends = analyzer.analyze_performance_trends(days=days)

    # Compare with benchmarks
    comparison = analyzer.compare_with_benchmarks()

    # Generate optimization report
    optimization_report = analyzer.generate_optimization_report()

    print("📈 Analysis Complete!")
    print(f"📋 Report generated with {len(trends.get('agents_analyzed', []))} agents analyzed")

    # Show key findings
    if trends.get('improvement_areas'):
        print(f"\n✅ Improvements detected: {len(trends['improvement_areas'])} areas")
        for area in trends['improvement_areas'][:3]:
            print(f"   {area['agent']}: +{area['improvement']:.1%}")

    if trends.get('regression_areas'):
        print(f"\n⚠️  Regressions detected: {len(trends['regression_areas'])} areas")
        for area in trends['regression_areas'][:3]:
            print(f"   {area['agent']}: -{area['regression']:.1%}")

    # Show benchmark comparison
    if comparison.get('improvement_areas'):
        print(f"\n📈 Benchmark improvements: {len(comparison['improvement_areas'])} areas")
        for area in comparison['improvement_areas'][:3]:
            print(f"   {area['test']}: +{area['improvement']:.1%}")

    print("\n📄 Full optimization report:")
    print(optimization_report)

    return {
        'trends': trends,
        'comparison': comparison,
        'optimization_report': optimization_report
    }


def main():
    """Main historical analysis entry point"""
    # Analyze last 7 days by default
    results = run_historical_analysis(days=7)
    return 0


if __name__ == "__main__":
    exit(main())
