"""
Meta-Learning System - Learning how to learn more effectively
Per CGPT: Bandit-style exploration (ε=0.1), ≤10% updates per pulse, 3 consecutive wins required
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .cbo_guardrails import CBOGuardrails


@dataclass
class TeachingParameter:
    """Represents a teaching parameter being optimized"""
    name: str
    current_value: float
    baseline_value: float
    min_value: float
    max_value: float
    update_history: List[Dict[str, Any]]
    consecutive_wins: int
    last_change_pulse: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetaLearningExperiment:
    """Represents a meta-learning experiment"""
    id: str
    parameter_name: str
    old_value: float
    new_value: float
    pulse_id: int
    tes_before: float
    tes_after: float
    improvement: float
    validated: bool
    created_date: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


class MetaLearningSystem:
    """
    Meta-learning system for optimizing teaching parameters.
    Per CGPT: Bandit exploration, bounded updates, consecutive wins required
    """
    
    def __init__(self, guardrails: CBOGuardrails):
        self.guardrails = guardrails
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing parameters and experiments
        self.parameters: Dict[str, TeachingParameter] = {}
        self.experiments: List[MetaLearningExperiment] = []
        self.data_dir = Path("outgoing/ai4all/meta_learning")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_data()
        
        # Constraints per CGPT
        self.epsilon = 0.1  # Exploration rate
        self.max_update_percent = 0.10  # 10% max update per pulse
        self.required_consecutive_wins = 3
        self.min_samples_for_personalization = 50
    
    def _load_data(self):
        """Load existing parameters and experiments"""
        try:
            # Load parameters
            param_file = self.data_dir / "parameters.json"
            if param_file.exists():
                with open(param_file, 'r') as f:
                    data = json.load(f)
                    for param_name, param_data in data.items():
                        param_data['update_history'] = param_data.get('update_history', [])
                        self.parameters[param_name] = TeachingParameter(**param_data)
            
            # Load experiments
            exp_file = self.data_dir / "experiments.json"
            if exp_file.exists():
                with open(exp_file, 'r') as f:
                    data = json.load(f)
                    for exp_data in data:
                        exp_data['created_date'] = datetime.fromisoformat(exp_data['created_date'])
                        self.experiments.append(MetaLearningExperiment(**exp_data))
        except Exception as e:
            self.logger.warning(f"Failed to load meta-learning data: {e}")
    
    def _save_data(self):
        """Save parameters and experiments"""
        try:
            # Save parameters
            param_file = self.data_dir / "parameters.json"
            with open(param_file, 'w') as f:
                data = {name: param.to_dict() for name, param in self.parameters.items()}
                json.dump(data, f, indent=2, default=str)
            
            # Save experiments
            exp_file = self.data_dir / "experiments.json"
            with open(exp_file, 'w') as f:
                data = [exp.to_dict() for exp in self.experiments]
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save meta-learning data: {e}")
    
    def register_parameter(self, name: str, current_value: float,
                          min_value: float, max_value: float) -> None:
        """
        Register a teaching parameter for optimization.
        
        Args:
            name: Parameter name
            current_value: Current parameter value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        if name in self.parameters:
            self.logger.warning(f"Parameter {name} already registered")
            return
        
        parameter = TeachingParameter(
            name=name,
            current_value=current_value,
            baseline_value=current_value,
            min_value=min_value,
            max_value=max_value,
            update_history=[],
            consecutive_wins=0,
            last_change_pulse=0
        )
        
        self.parameters[name] = parameter
        self._save_data()
        
        self.logger.info(f"Registered parameter: {name} = {current_value}")
    
    def should_explore(self) -> bool:
        """
        Decide whether to explore or exploit using epsilon-greedy strategy.
        
        Returns:
            True if should explore, False if should exploit
        """
        return random.random() < self.epsilon
    
    def update_parameter(self, name: str, new_value: float, pulse_id: int,
                        tes_before: float, tes_after: float) -> bool:
        """
        Update a parameter with bounded change and validation.
        Per CGPT: ≤10% update per pulse, 3 consecutive wins required
        
        Args:
            name: Parameter name
            new_value: Proposed new value
            pulse_id: Current pulse ID
            tes_before: TES before change
            tes_after: TES after change
            
        Returns:
            True if update applied, False if rejected
        """
        if name not in self.parameters:
            self.logger.warning(f"Parameter {name} not being actively monitored")
            return False
        
        parameter = self.parameters[name]
        
        # Safety check: Bounded update per CGPT
        change_percent = abs(new_value - parameter.current_value) / abs(parameter.current_value) if parameter.current_value != 0 else 0
        
        if change_percent > self.max_update_percent:
            self.logger.warning(f"Update rejected: {change_percent*100:.1f}% > {self.max_update_percent*100:.1f}% limit")
            return False
        
        # Safety check: Ensure new value within bounds
        if new_value < parameter.min_value or new_value > parameter.max_value:
            self.logger.warning(f"Update rejected: value {new_value} outside bounds [{parameter.min_value}, {parameter.max_value}]")
            return False
        
        # Check if consecutive wins requirement met
        if parameter.consecutive_wins < self.required_consecutive_wins:
            self.logger.warning(f"Update rejected: only {parameter.consecutive_wins} consecutive wins, need {self.required_consecutive_wins}")
            return False
        
        # Validate improvement
        improvement = tes_after - tes_before
        is_improvement = improvement > 0
        
        # Create experiment record
        exp_id = f"exp_{int(datetime.now().timestamp())}"
        experiment = MetaLearningExperiment(
            id=exp_id,
            parameter_name=name,
            old_value=parameter.current_value,
            new_value=new_value,
            pulse_id=pulse_id,
            tes_before=tes_before,
            tes_after=tes_after,
            improvement=improvement,
            validated=is_improvement,
            created_date=datetime.now()
        )
        
        self.experiments.append(experiment)
        
        # Update parameter if improvement
        if is_improvement:
            parameter.current_value = new_value
            parameter.consecutive_wins += 1
            parameter.last_change_pulse = pulse_id
            
            self.logger.info(f"Parameter {name} updated: {parameter.current_value:.3f} → {new_value:.3f}")
        else:
            # Reset consecutive wins on failure
            parameter.consecutive_wins = 0
            self.logger.warning(f"Parameter {name} update failed: TES decreased")
        
        # Record update history
        parameter.update_history.append({
            'pulse_id': pulse_id,
            'old_value': experiment.old_value,
            'new_value': new_value,
            'improvement': improvement,
            'validated': is_improvement
        })
        
        self._save_data()
        return is_improvement
    
    def evaluate_exploration(self, name: str, test_value: float,
                            pulse_id: int, tes_before: float, tes_after: float) -> Dict[str, Any]:
        """
        Evaluate an exploration attempt (epsilon-ε% of time).
        
        Args:
            name: Parameter name
            test_value: Value being tested
            pulse_id: Current pulse ID
            tes_before: TES before exploration
            tes_after: TES after exploration
            
        Returns:
            Evaluation result
        """
        if name not in self.parameters:
            return {'error': 'Parameter not registered'}
        
        parameter = self.parameters[name]
        
        # Check bounds
        if test_value < parameter.min_value or test_value > parameter.max_value:
            return {'error': 'Value outside bounds'}
        
        # Calculate improvement
        improvement = tes_after - tes_before
        
        # Record as experiment
        exp_id = f"exp_{int(datetime.now().timestamp())}"
        experiment = MetaLearningExperiment(
            id=exp_id,
            parameter_name=name,
            old_value=parameter.current_value,
            new_value=test_value,
            pulse_id=pulse_id,
            tes_before=tes_before,
            tes_after=tes_after,
            improvement=improvement,
            validated=improvement > 0,
            created_date=datetime.now()
        )
        
        self.experiments.append(experiment)
        self._save_data()
        
        return {
            'experiment_id': exp_id,
            'improvement': improvement,
            'is_improvement': improvement > 0,
            'consecutive_wins_now': parameter.consecutive_wins + (1 if improvement > 0 else 0)
        }
    
    def increment_consecutive_wins(self, name: str):
        """Increment consecutive wins counter for a parameter"""
        if name in self.parameters:
            parameter = self.parameters[name]
            parameter.consecutive_wins += 1
            self._save_data()
            self.logger.info(f"Parameter {name} consecutive wins: {parameter.consecutive_wins}")
    
    def reset_consecutive_wins(self, name: str):
        """Reset consecutive wins counter"""
        if name in self.parameters:
            parameter = self.parameters[name]
            parameter.consecutive_wins = 0
            self._save_data()
            self.logger.info(f"Parameter {name} consecutive wins reset")
    
    def get_parameter(self, name: str) -> Optional[TeachingParameter]:
        """Get a parameter by name"""
        return self.parameters.get(name)
    
    def get_parameter_status(self, name: str) -> Dict[str, Any]:
        """Get parameter status"""
        if name not in self.parameters:
            return {'error': 'Parameter not found'}
        
        parameter = self.parameters[name]
        
        return {
            'name': name,
            'current_value': parameter.current_value,
            'baseline_value': parameter.baseline_value,
            'consecutive_wins': parameter.consecutive_wins,
            'required_wins': self.required_consecutive_wins,
            'can_update': parameter.consecutive_wins >= self.required_consecutive_wins,
            'update_count': len(parameter.update_history)
        }
    
    def list_parameters(self) -> List[Dict[str, Any]]:
        """List all registered parameters"""
        return [param.to_dict() for param in self.parameters.values()]


# Export for use by other modules
__all__ = ['TeachingParameter', 'MetaLearningExperiment', 'MetaLearningSystem']
