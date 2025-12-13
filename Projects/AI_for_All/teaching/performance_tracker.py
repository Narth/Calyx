"""
Performance Tracker - Comprehensive performance analysis for AI-for-All
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics


@dataclass
class PerformanceSnapshot:
    """Snapshot of agent performance at a point in time"""
    agent_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    context: Dict[str, str]
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PerformanceTrend:
    """Analysis of performance trends over time"""
    agent_id: str
    metric_name: str
    trend_direction: str  # 'improving', 'declining', 'stable'
    trend_strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    time_period: str
    data_points: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BaselineDefinition:
    """Definition of performance baseline for an agent"""
    agent_id: str
    objective: str
    metrics: Dict[str, float]
    established_date: datetime
    confidence: float
    sample_size: int
    validity_period_days: int = 30

    def to_dict(self) -> dict:
        return asdict(self)


class PerformanceTracker:
    """
    Tracks and analyzes agent performance to support adaptive teaching methods.
    Provides comprehensive performance insights including trends, baselines, and predictions.
    """

    def __init__(self, config: dict):
        """
        Initialize the performance tracker.

        Args:
            config: Configuration dictionary for performance tracking
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Performance data storage
        self.performance_history: Dict[str, List[PerformanceSnapshot]] = {}
        self.baselines: Dict[str, BaselineDefinition] = {}
        self.trends: Dict[str, List[PerformanceTrend]] = {}

        # Load existing data
        self._load_persistent_data()

        # Metrics weights for composite scores
        self.metric_weights = {
            'tes': 0.4,
            'stability': 0.3,
            'velocity': 0.2,
            'error_rate': 0.1
        }

    def _load_persistent_data(self):
        """Load existing performance data from files"""
        try:
            # Load baselines
            baseline_file = Path("outgoing/ai4all/baselines/baselines.json")
            if baseline_file.exists():
                with open(baseline_file, 'r') as f:
                    baseline_data = json.load(f)
                    for key, data in baseline_data.items():
                        data['established_date'] = datetime.fromisoformat(data['established_date'])
                        self.baselines[key] = BaselineDefinition(**data)

            # Load performance history (recent data only)
            history_dir = Path("outgoing/ai4all/metrics/history")
            if history_dir.exists():
                for history_file in history_dir.glob("*.json"):
                    with open(history_file, 'r') as f:
                        data = json.load(f)
                        agent_id = data['agent_id']
                        if agent_id not in self.performance_history:
                            self.performance_history[agent_id] = []

                        snapshot = PerformanceSnapshot(
                            agent_id=agent_id,
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            metrics=data['metrics'],
                            context=data.get('context', {})
                        )
                        self.performance_history[agent_id].append(snapshot)

        except Exception as e:
            self.logger.warning(f"Failed to load persistent data: {e}")

    def record_performance(self, agent_id: str, metrics: Dict[str, float],
                          context: Dict[str, str] = None, session_id: str = None):
        """
        Record a performance snapshot for an agent.

        Args:
            agent_id: Agent identifier
            metrics: Performance metrics to record
            context: Additional context information
            session_id: Learning session identifier
        """
        snapshot = PerformanceSnapshot(
            agent_id=agent_id,
            timestamp=datetime.now(),
            metrics=metrics.copy(),
            context=context or {},
            session_id=session_id
        )

        # Add to history
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []
        self.performance_history[agent_id].append(snapshot)

        # Keep only recent history based on retention policy
        retention_days = self.config.get('retention_days', 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        self.performance_history[agent_id] = [
            s for s in self.performance_history[agent_id]
            if s.timestamp > cutoff_date
        ]

        # Update trends
        self._update_trends(agent_id)

        # Save to persistent storage
        self._save_performance_snapshot(snapshot)

        self.logger.debug(f"Recorded performance for {agent_id}: {metrics}")

    def _save_performance_snapshot(self, snapshot: PerformanceSnapshot):
        """Save performance snapshot to persistent storage"""
        try:
            # Save individual snapshot
            snapshot_dir = Path("outgoing/ai4all/metrics/snapshots")
            snapshot_dir.mkdir(parents=True, exist_ok=True)

            # Replace colons with underscores for Windows compatibility
            timestamp_str = snapshot.timestamp.isoformat().replace(':', '_')
            snapshot_file = snapshot_dir / f"{snapshot.agent_id}_{timestamp_str}.json"
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot.to_dict(), f, indent=2, default=str)

            # Periodically update history file
            if len(self.performance_history.get(snapshot.agent_id, [])) % 10 == 0:
                self._save_performance_history(snapshot.agent_id)

        except Exception as e:
            self.logger.warning(f"Failed to save performance snapshot: {e}")

    def _save_performance_history(self, agent_id: str):
        """Save performance history for an agent"""
        try:
            history_dir = Path("outgoing/ai4all/metrics/history")
            history_dir.mkdir(parents=True, exist_ok=True)

            history_file = history_dir / f"{agent_id}_history.json"
            history_data = {
                'agent_id': agent_id,
                'snapshots': [s.to_dict() for s in self.performance_history.get(agent_id, [])]
            }

            with open(history_file, 'w') as f:
                json.dump(history_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.warning(f"Failed to save performance history: {e}")

    def _update_trends(self, agent_id: str):
        """Update performance trends for an agent"""
        if agent_id not in self.performance_history or len(self.performance_history[agent_id]) < 5:
            return

        snapshots = self.performance_history[agent_id]
        trends = []

        # Analyze trends for each metric
        for metric in ['tes', 'stability', 'velocity', 'error_rate']:
            metric_snapshots = [s for s in snapshots if metric in s.metrics]

            if len(metric_snapshots) >= 5:
                trend = self._calculate_trend(metric_snapshots, metric, agent_id)
                if trend:
                    trends.append(trend)

        self.trends[agent_id] = trends

    def _calculate_trend(self, snapshots: List[PerformanceSnapshot], metric: str,
                        agent_id: str) -> Optional[PerformanceTrend]:
        """Calculate trend for a specific metric"""
        if len(snapshots) < 5:
            return None

        # Sort by timestamp
        snapshots.sort(key=lambda x: x.timestamp)

        # Get metric values
        values = [s.metrics[metric] for s in snapshots]

        # Simple linear regression to determine trend
        n = len(values)
        x = list(range(n))
        y = values

        # Calculate slope
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator = sum((xi - mean_x) ** 2 for xi in x)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # Determine trend direction and strength
        max_change = max(values) - min(values)
        trend_strength = min(1.0, abs(slope) * 10) if max_change > 0 else 0

        if slope > 0.001:
            direction = 'improving'
        elif slope < -0.001:
            direction = 'declining'
        else:
            direction = 'stable'

        # Calculate confidence based on data consistency
        if len(values) >= 10:
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            mean_val = statistics.mean(values)
            coefficient_variation = std_dev / mean_val if mean_val > 0 else 1
            confidence = max(0.1, 1.0 - coefficient_variation)
        else:
            confidence = 0.5

        return PerformanceTrend(
            agent_id=agent_id,
            metric_name=metric,
            trend_direction=direction,
            trend_strength=trend_strength,
            confidence=confidence,
            time_period=f"{snapshots[0].timestamp} to {snapshots[-1].timestamp}",
            data_points=len(snapshots)
        )

    def get_agent_performance(self, agent_id: str) -> Dict:
        """Get comprehensive performance analysis for an agent"""
        if agent_id not in self.performance_history:
            return {'error': 'No performance data available'}

        snapshots = self.performance_history[agent_id]

        if not snapshots:
            return {'error': 'No performance snapshots available'}

        # Get latest performance
        latest = snapshots[-1]

        # Calculate averages over different time periods
        now = datetime.now()
        last_hour = [s for s in snapshots if (now - s.timestamp).total_seconds() < 3600]
        last_day = [s for s in snapshots if (now - s.timestamp).total_seconds() < 86400]
        last_week = [s for s in snapshots if (now - s.timestamp).total_seconds() < 604800]

        performance_data = {
            'agent_id': agent_id,
            'latest': latest.to_dict(),
            'summary': self._calculate_performance_summary(snapshots),
            'trends': [t.to_dict() for t in self.trends.get(agent_id, [])],
            'time_periods': {
                'last_hour': self._calculate_performance_summary(last_hour) if last_hour else {},
                'last_day': self._calculate_performance_summary(last_day) if last_day else {},
                'last_week': self._calculate_performance_summary(last_week) if last_week else {}
            }
        }

        return performance_data

    def _calculate_performance_summary(self, snapshots: List[PerformanceSnapshot]) -> Dict:
        """Calculate performance summary statistics"""
        if not snapshots:
            return {}

        # Extract metrics
        metrics = {}
        for metric in ['tes', 'stability', 'velocity', 'error_rate']:
            values = [s.metrics[metric] for s in snapshots if metric in s.metrics]
            if values:
                metrics[metric] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'count': len(values)
                }

        # Calculate composite scores
        composite_scores = self._calculate_composite_scores(metrics)

        return {
            'metrics': metrics,
            'composite_scores': composite_scores,
            'sample_size': len(snapshots),
            'time_span': {
                'start': snapshots[0].timestamp.isoformat(),
                'end': snapshots[-1].timestamp.isoformat()
            }
        }

    def _calculate_composite_scores(self, metrics: Dict) -> Dict[str, float]:
        """Calculate composite performance scores"""
        composite_scores = {}

        # Overall performance score
        weights = self.metric_weights
        overall_score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            if metric in metrics and metrics[metric]['count'] > 0:
                value = metrics[metric]['mean']
                if metric == 'error_rate':
                    # Invert error rate (lower is better)
                    value = 1.0 - min(1.0, value)
                overall_score += value * weight
                total_weight += weight

        if total_weight > 0:
            composite_scores['overall'] = overall_score / total_weight

        return composite_scores

    def establish_baseline(self, agent_id: str, objective: str,
                          metrics: Dict[str, float], sample_size: int = 10) -> bool:
        """
        Establish a performance baseline for an agent.

        Args:
            agent_id: Agent identifier
            objective: Learning objective
            metrics: Performance metrics for baseline
            sample_size: Number of samples used to establish baseline

        Returns:
            True if baseline established successfully
        """
        if sample_size < 5:
            self.logger.warning(f"Insufficient sample size ({sample_size}) for baseline")
            return False

        baseline = BaselineDefinition(
            agent_id=agent_id,
            objective=objective,
            metrics=metrics.copy(),
            established_date=datetime.now(),
            confidence=0.8,  # Could be calculated based on metric stability
            sample_size=sample_size,
            validity_period_days=self.config.get('baseline_validity_days', 30)
        )

        key = f"{agent_id}_{objective}"
        self.baselines[key] = baseline

        # Save to persistent storage
        self._save_baselines()

        self.logger.info(f"Established baseline for {agent_id} on {objective}: {metrics}")
        return True

    def _save_baselines(self):
        """Save baselines to persistent storage"""
        try:
            baseline_file = Path("outgoing/ai4all/baselines/baselines.json")
            baseline_file.parent.mkdir(parents=True, exist_ok=True)

            baseline_data = {}
            for key, baseline in self.baselines.items():
                baseline_data[key] = baseline.to_dict()

            with open(baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2, default=str)

        except Exception as e:
            self.logger.warning(f"Failed to save baselines: {e}")

    def get_baseline(self, agent_id: str, objective: str) -> Optional[Dict]:
        """Get baseline for an agent and objective"""
        key = f"{agent_id}_{objective}"
        if key in self.baselines:
            return self.baselines[key].to_dict()
        return None

    def compare_to_baseline(self, agent_id: str, objective: str,
                           current_metrics: Dict[str, float]) -> Dict[str, float]:
        """
        Compare current metrics to established baseline.

        Args:
            agent_id: Agent identifier
            objective: Learning objective
            current_metrics: Current performance metrics

        Returns:
            Dictionary with improvement ratios for each metric
        """
        baseline = self.get_baseline(agent_id, objective)
        if not baseline:
            return {'error': 'No baseline established'}

        baseline_metrics = baseline['metrics']
        improvements = {}

        for metric, current_value in current_metrics.items():
            if metric in baseline_metrics:
                baseline_value = baseline_metrics[metric]
                if baseline_value > 0:
                    if metric == 'error_rate':
                        # Lower error rate is better
                        improvements[metric] = (baseline_value - current_value) / baseline_value
                    else:
                        # Higher values are better
                        improvements[metric] = (current_value - baseline_value) / baseline_value
                else:
                    improvements[metric] = 0.0
            else:
                improvements[metric] = 0.0

        return improvements

    def predict_performance(self, agent_id: str, future_hours: int = 24) -> Dict[str, float]:
        """
        Predict future performance based on trends.

        Args:
            agent_id: Agent identifier
            future_hours: Hours into the future to predict

        Returns:
            Predicted performance metrics
        """
        if agent_id not in self.trends:
            return {'error': 'No trend data available'}

        predictions = {}
        current_time = datetime.now()

        for trend in self.trends[agent_id]:
            if trend.confidence > 0.6:  # Only use confident trends
                # Simple linear extrapolation
                if agent_id in self.performance_history and self.performance_history[agent_id]:
                    latest_metrics = self.performance_history[agent_id][-1].metrics
                    if trend.metric_name in latest_metrics:
                        current_value = latest_metrics[trend.metric_name]
                        predicted_change = trend.trend_strength * (future_hours / 24.0)

                        if trend.trend_direction == 'improving':
                            predictions[trend.metric_name] = current_value * (1 + predicted_change)
                        elif trend.trend_direction == 'declining':
                            predictions[trend.metric_name] = current_value * (1 - predicted_change)
                        else:
                            predictions[trend.metric_name] = current_value

        return predictions

    def get_performance_report(self, agent_id: str) -> str:
        """Generate a human-readable performance report"""
        performance = self.get_agent_performance(agent_id)

        if 'error' in performance:
            return f"No performance data available for {agent_id}"

        report = []
        report.append(f"Performance Report for {agent_id}")
        report.append("=" * 40)
        report.append(f"Generated: {datetime.now().isoformat()}")

        # Latest metrics
        latest = performance['latest']['metrics']
        report.append("\nLatest Metrics:")
        for metric, value in latest.items():
            value_formatted = f"{value:.3f}"
            report.append(f"  {metric}: {value_formatted}")

        # Trends
        if performance['trends']:
            report.append("\nTrends:")
            for trend in performance['trends']:
                confidence_pct = trend['confidence'] * 100
                strength_pct = trend['trend_strength'] * 100
                strength_formatted = f"{strength_pct:.1f}"
                confidence_formatted = f"{confidence_pct:.1f}"
                report.append(f"  {trend['metric_name']}: {trend['trend_direction']} "
                            f"(strength: {strength_formatted}%, confidence: {confidence_formatted}%)")

        return "\n".join(report)
