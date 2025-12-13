"""
Teaching Framework - Core orchestration for AI-for-All teaching methods
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import sys
import os

# Add current directory to path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from adaptive_learner import AdaptiveLearner
from performance_tracker import PerformanceTracker
from knowledge_integrator import KnowledgeIntegrator
from pattern_recognition import PatternRecognition


@dataclass
class LearningSession:
    """Represents a learning session for an agent"""
    id: str
    agent_id: str
    learning_objective: str
    baseline_metrics: Dict[str, float]
    start_time: datetime
    current_phase: str = "initialization"
    progress_score: float = 0.0
    adaptation_count: int = 0
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TeachingMetrics:
    """Comprehensive teaching effectiveness metrics"""
    session_id: str
    teaching_method: str
    efficiency_improvement: float
    stability_score: float
    adaptation_rate: float
    knowledge_retention: float
    timestamp: datetime

    def to_dict(self) -> dict:
        return asdict(self)


class TeachingFramework:
    """
    Core framework for implementing baseline teaching methods across agents.

    This framework provides standardized approaches for:
    - Adaptive learning parameter adjustment
    - Performance tracking and analysis
    - Knowledge integration and pattern recognition
    - Cross-agent learning coordination
    """

    def __init__(self, config_path: str = None):
        """
        Initialize the teaching framework.

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or "config/teaching_config.yaml"

        # Setup logging first
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._setup_logging()

        self.config = self._load_config()

        # Initialize core components
        self.adaptive_learner = AdaptiveLearner(self.config.get('adaptive_learning', {}))
        self.performance_tracker = PerformanceTracker(self.config.get('performance_tracking', {}))
        self.knowledge_integrator = KnowledgeIntegrator(self.config.get('knowledge_integration', {}))
        self.pattern_recognition = PatternRecognition(self.config.get('pattern_recognition', {}))

        # Learning sessions and metrics
        self.active_sessions: Dict[str, LearningSession] = {}
        self.teaching_history: List[TeachingMetrics] = []
        self.agents_baseline: Dict[str, Dict[str, float]] = {}

        # Create necessary directories
        self._ensure_directories()

        self.logger.info("Teaching Framework initialized successfully")

    def load_existing_sessions(self) -> None:
        """Hydrate active sessions from persisted session files."""
        sessions_dir = Path("outgoing/ai4all/sessions")
        if not sessions_dir.exists():
            return

        loaded = 0
        for session_file in sessions_dir.glob("*.json"):
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                start = data.get("start_time")
                if isinstance(start, str):
                    try:
                        data["start_time"] = datetime.fromisoformat(start)
                    except ValueError:
                        data["start_time"] = datetime.strptime(start, "%Y-%m-%d %H:%M:%S.%f")
                session = LearningSession(**data)
                self.active_sessions[session.id] = session
                if session.agent_id not in self.agents_baseline:
                    self.agents_baseline[session.agent_id] = session.baseline_metrics.copy()
                loaded += 1
            except Exception as exc:
                self.logger.warning(f"Failed to load teaching session from {session_file}: {exc}")

        if loaded:
            self.logger.info(f"Loaded {loaded} teaching sessions from disk")

    def _load_config(self) -> dict:
        """Load configuration from file or use defaults"""
        try:
            # Try loading as YAML first
            if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                try:
                    import yaml
                    with open(self.config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        if config:
                            return config
                except ImportError:
                    self.logger.warning("PyYAML not available, install with: pip install pyyaml")
                    self.logger.info("Attempting to read as JSON...")
            
            # Fallback to JSON
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Config file {self.config_path} not found or invalid: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Default configuration for the teaching framework"""
        return {
            'adaptive_learning': {
                'learning_rate': 0.1,
                'momentum': 0.9,
                'decay_rate': 0.95,
                'min_improvement_threshold': 0.05,
                'max_adaptation_attempts': 10,
                'gpu_acceleration': {
                    'enabled': True,
                    'pattern_threshold': 0.7,
                    'force_cpu': False
                }
            },
            'performance_tracking': {
                'metrics_retention_days': 30,
                'baseline_update_interval': 3600,  # 1 hour
                'improvement_threshold': 0.1,
                'stability_weight': 0.4,
                'efficiency_weight': 0.4,
                'velocity_weight': 0.2
            },
            'knowledge_integration': {
                'pattern_similarity_threshold': 0.8,
                'knowledge_retention_period': 7,
                'cross_agent_sharing_enabled': True,
                'validation_required': True
            },
            'pattern_recognition': {
                'min_pattern_occurrences': 3,
                'pattern_strength_threshold': 0.7,
                'max_patterns_per_agent': 50,
                'pattern_decay_rate': 0.9
            },
            'system_integration': {
                'heartbeat_interval': 60,
                'metrics_output_path': 'outgoing/ai4all/',
                'log_level': 'INFO',
                'enable_safety_gates': True
            }
        }

    def _setup_logging(self):
        """Setup logging for the teaching framework"""
        # Use default log level if config not loaded yet
        log_level_str = 'INFO'
        if hasattr(self, 'config') and self.config and 'system_integration' in self.config:
            log_level_str = self.config['system_integration'].get('log_level', 'INFO')

        log_level = getattr(logging, log_level_str)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _ensure_directories(self):
        """Ensure required directories exist"""
        base_path = Path("outgoing/ai4all")
        directories = [
            base_path / "sessions",
            base_path / "metrics",
            base_path / "progress",
            base_path / "knowledge",
            base_path / "patterns",
            base_path / "baselines"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def create_learning_session(self, agent_id: str, learning_objective: str,
                              baseline_metrics: Dict[str, float]) -> LearningSession:
        """
        Create a new learning session for an agent.

        Args:
            agent_id: Identifier of the agent to teach
            learning_objective: What the agent should learn (e.g., "task_efficiency", "stability")
            baseline_metrics: Current performance baseline

        Returns:
            LearningSession object representing the new session
        """
        session_id = f"{agent_id}_{learning_objective}_{int(time.time())}"

        session = LearningSession(
            id=session_id,
            agent_id=agent_id,
            learning_objective=learning_objective,
            baseline_metrics=baseline_metrics.copy(),
            start_time=datetime.now()
        )

        self.active_sessions[session_id] = session

        # Save session to file
        session_file = Path(f"outgoing/ai4all/sessions/{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2, default=str)

        # Update agent's baseline
        if agent_id not in self.agents_baseline:
            self.agents_baseline[agent_id] = {}
        self.agents_baseline[agent_id][learning_objective] = baseline_metrics

        self.logger.info(f"Created learning session {session_id} for agent {agent_id}")
        return session

    def update_learning_progress(self, session_id: str, current_metrics: Dict[str, float],
                               adaptation_applied: Optional[str] = None) -> float:
        """
        Update learning progress for a session and adapt teaching methods if needed.

        Args:
            session_id: ID of the learning session
            current_metrics: Current performance metrics
            adaptation_applied: Description of any adaptation applied

        Returns:
            Progress score (0.0 to 1.0)
        """
        if session_id not in self.active_sessions:
            self.logger.warning(f"Session {session_id} not found")
            return 0.0

        session = self.active_sessions[session_id]

        # Calculate progress score
        progress = self._calculate_progress_score(session, current_metrics)

        # Update session
        session.progress_score = progress
        session.adaptation_count += 1 if adaptation_applied else 0

        # Apply adaptive learning if progress is insufficient
        if progress < self.config['adaptive_learning']['min_improvement_threshold']:
            adaptation = self.adaptive_learner.suggest_adaptation(
                session.agent_id,
                session.learning_objective,
                current_metrics,
                session.baseline_metrics
            )

            if adaptation:
                session.current_phase = "adaptation"
                self.logger.info(f"Applied adaptation for session {session_id}: {adaptation}")

        # Save updated session
        self._save_session(session)

        return progress

    def _calculate_progress_score(self, session: LearningSession,
                                current_metrics: Dict[str, float]) -> float:
        """
        Calculate learning progress score based on improvement from baseline.

        Returns score between 0.0 (no improvement) and 1.0 (excellent improvement)
        """
        baseline = session.baseline_metrics
        progress_score = 0.0

        # Weight different metrics based on learning objective
        weights = self._get_metric_weights(session.learning_objective)

        for metric, weight in weights.items():
            if metric in current_metrics and metric in baseline:
                current = current_metrics[metric]
                base = baseline[metric]

                # Calculate improvement (positive change for "higher is better" metrics)
                if metric in ['tes', 'stability', 'efficiency', 'velocity']:
                    improvement = (current - base) / base if base > 0 else 0
                else:  # For "lower is better" metrics like latency, error_rate
                    improvement = (base - current) / base if base > 0 else 0

                progress_score += max(0, min(1, improvement)) * weight

        return min(1.0, progress_score)

    def _get_metric_weights(self, learning_objective: str) -> Dict[str, float]:
        """Get metric weights based on learning objective"""
        weights_map = {
            'task_efficiency': {
                'tes': 0.4,
                'velocity': 0.3,
                'stability': 0.2,
                'error_rate': 0.1
            },
            'stability': {
                'stability': 0.5,
                'tes': 0.3,
                'error_rate': 0.2
            },
            'latency_optimization': {
                'velocity': 0.4,
                'tes': 0.3,
                'stability': 0.2,
                'latency': 0.1
            }
        }

        return weights_map.get(learning_objective, {
            'tes': 0.4,
            'stability': 0.3,
            'velocity': 0.2,
            'error_rate': 0.1
        })

    def _save_session(self, session: LearningSession):
        """Save session to file"""
        session_file = Path(f"outgoing/ai4all/sessions/{session.id}.json")
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2, default=str)

    def record_teaching_metrics(self, session_id: str, teaching_method: str,
                              efficiency_improvement: float, stability_score: float,
                              adaptation_rate: float, knowledge_retention: float):
        """
        Record comprehensive teaching effectiveness metrics.

        Args:
            session_id: Learning session identifier
            teaching_method: Method used for teaching
            efficiency_improvement: Measured efficiency improvement (0.0 to 1.0)
            stability_score: System stability during learning (0.0 to 1.0)
            adaptation_rate: Rate of adaptation applied (0.0 to 1.0)
            knowledge_retention: Knowledge retention score (0.0 to 1.0)
        """
        metrics = TeachingMetrics(
            session_id=session_id,
            teaching_method=teaching_method,
            efficiency_improvement=efficiency_improvement,
            stability_score=stability_score,
            adaptation_rate=adaptation_rate,
            knowledge_retention=knowledge_retention,
            timestamp=datetime.now()
        )

        self.teaching_history.append(metrics)

        # Save to file
        metrics_file = Path(f"outgoing/ai4all/metrics/{session_id}_{teaching_method}.json")
        with open(metrics_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2, default=str)

        self.logger.info(f"Recorded teaching metrics for {session_id}: efficiency={efficiency_improvement:.3f}")

    def get_learning_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive learning progress for a session"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]

        # Get performance tracking data
        performance_data = self.performance_tracker.get_agent_performance(session.agent_id)

        # Get pattern recognition insights
        patterns = self.pattern_recognition.get_agent_patterns(session.agent_id)

        # Get knowledge integration status
        knowledge_status = self.knowledge_integrator.get_integration_status(session.agent_id)

        return {
            'session': session.to_dict(),
            'performance': performance_data,
            'patterns': patterns,
            'knowledge': knowledge_status,
            'teaching_history': [m.to_dict() for m in self.teaching_history if m.session_id == session_id]
        }

    def end_learning_session(self, session_id: str, final_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        End a learning session and generate final report.

        Args:
            session_id: ID of session to end
            final_metrics: Final performance metrics

        Returns:
            Final session report
        """
        if session_id not in self.active_sessions:
            self.logger.warning(f"Session {session_id} not found")
            return {}

        session = self.active_sessions[session_id]
        session.status = "completed"

        # Calculate final progress
        final_progress = self._calculate_progress_score(session, final_metrics)

        # Update baseline if improvement is significant
        improvement_threshold = self.config['performance_tracking']['improvement_threshold']
        if final_progress > improvement_threshold:
            self.agents_baseline[session.agent_id][session.learning_objective] = final_metrics.copy()
            self.logger.info(f"Updated baseline for {session.agent_id}: {final_metrics}")

        # Save final session state
        self._save_session(session)

        # Remove from active sessions
        del self.active_sessions[session_id]

        # Generate final report
        report = {
            'session_id': session_id,
            'agent_id': session.agent_id,
            'learning_objective': session.learning_objective,
            'start_time': session.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'initial_baseline': session.baseline_metrics,
            'final_metrics': final_metrics,
            'progress_score': final_progress,
            'adaptations_applied': session.adaptation_count,
            'success': final_progress > improvement_threshold
        }

        # Save final report
        report_file = Path(f"outgoing/ai4all/progress/{session_id}_final.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Completed learning session {session_id} with progress score {final_progress:.3f}")
        return report

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall teaching framework status"""
        return {
            'active_sessions': len(self.active_sessions),
            'total_sessions_completed': len([s for s in self.active_sessions.values() if s.status == "completed"]),
            'agents_with_baselines': len(self.agents_baseline),
            'teaching_methods_used': len(set([m.teaching_method for m in self.teaching_history])),
            'framework_version': "1.0.0",
            'config_summary': {
                'adaptive_learning_enabled': True,
                'performance_tracking_enabled': True,
                'knowledge_integration_enabled': True,
                'pattern_recognition_enabled': True
            }
        }

    def emit_heartbeat(self):
        """Emit framework heartbeat for system monitoring"""
        heartbeat = {
            'name': 'ai4all_teaching_framework',
            'status': 'running',
            'active_sessions': len(self.active_sessions),
            'system_status': self.get_system_status(),
            'timestamp': datetime.now().isoformat()
        }

        heartbeat_file = Path("outgoing/ai4all/framework_heartbeat.json")
        with open(heartbeat_file, 'w') as f:
            json.dump(heartbeat, f, indent=2, default=str)
