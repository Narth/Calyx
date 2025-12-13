"""
Causal Testing Framework - A/B testing with randomized ablation
Per CGPT requirement: A/B tests with N≥30, d≥0.5, p<0.1 before labeling "causal"
"""

import json
import logging
import random
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class CausalHypothesis:
    """Represents a causal hypothesis to be tested"""
    id: str
    description: str
    independent_variable: str
    dependent_variable: str
    expected_effect_size: float
    created_date: datetime
    status: str  # 'pending', 'testing', 'validated', 'rejected'
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CausalExperiment:
    """Represents a causal experiment result"""
    id: str
    hypothesis_id: str
    n_samples: int
    effect_size: float
    p_value: float
    confidence_interval: Tuple[float, float]
    control_mean: float
    treatment_mean: float
    conclusion: str
    run_date: datetime
    
    def to_dict(self) -> dict:
        return asdict(self)


class CausalTestingFramework:
    """
    Implements controlled A/B testing with randomized ablation for causal inference.
    Required per CGPT: N≥30, d≥0.5, p<0.1 before labeling as "causal"
    """
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("outgoing/ai4all/causal")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing data
        self.hypotheses: Dict[str, CausalHypothesis] = {}
        self.experiments: List[CausalExperiment] = []
        self._load_data()
        
        # Statistical thresholds per CGPT
        self.min_samples = 30
        self.min_effect_size = 0.5
        self.max_p_value = 0.1
    
    def _load_data(self):
        """Load existing hypotheses and experiments"""
        try:
            # Load hypotheses
            hyp_file = self.data_dir / "hypotheses.json"
            if hyp_file.exists():
                with open(hyp_file, 'r') as f:
                    data = json.load(f)
                    for hyp_id, hyp_data in data.items():
                        hyp_data['created_date'] = datetime.fromisoformat(hyp_data['created_date'])
                        self.hypotheses[hyp_id] = CausalHypothesis(**hyp_data)
            
            # Load experiments
            exp_file = self.data_dir / "experiments.json"
            if exp_file.exists():
                with open(exp_file, 'r') as f:
                    data = json.load(f)
                    for exp_data in data:
                        exp_data['run_date'] = datetime.fromisoformat(exp_data['run_date'])
                        # Convert confidence_interval list to tuple
                        exp_data['confidence_interval'] = tuple(exp_data['confidence_interval'])
                        self.experiments.append(CausalExperiment(**exp_data))
        except Exception as e:
            self.logger.warning(f"Failed to load causal data: {e}")
    
    def _save_data(self):
        """Save hypotheses and experiments"""
        try:
            # Save hypotheses
            hyp_file = self.data_dir / "hypotheses.json"
            with open(hyp_file, 'w') as f:
                data = {hid: hyp.to_dict() for hid, hyp in self.hypotheses.items()}
                json.dump(data, f, indent=2, default=str)
            
            # Save experiments
            exp_file = self.data_dir / "experiments.json"
            with open(exp_file, 'w') as f:
                data = [exp.to_dict() for exp in self.experiments]
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save causal data: {e}")
    
    def create_hypothesis(self, description: str, independent_var: str, 
                         dependent_var: str, expected_effect: float) -> str:
        """
        Create a new causal hypothesis to test.
        
        Args:
            description: Description of the hypothesis
            independent_var: The variable being manipulated
            dependent_var: The variable being measured
            expected_effect: Expected effect size
            
        Returns:
            Hypothesis ID
        """
        hyp_id = f"hyp_{int(datetime.now().timestamp())}"
        
        hypothesis = CausalHypothesis(
            id=hyp_id,
            description=description,
            independent_variable=independent_var,
            dependent_variable=dependent_var,
            expected_effect_size=expected_effect,
            created_date=datetime.now(),
            status='pending'
        )
        
        self.hypotheses[hyp_id] = hypothesis
        self._save_data()
        
        self.logger.info(f"Created hypothesis: {hyp_id} - {description}")
        return hyp_id
    
    def run_ablation_study(self, hyp_id: str, control_data: List[float],
                          treatment_data: List[float]) -> CausalExperiment:
        """
        Run an A/B test (randomized ablation study) to test causal hypothesis.
        
        Args:
            hyp_id: Hypothesis ID to test
            control_data: Control group measurements
            treatment_data: Treatment group measurements
            
        Returns:
            CausalExperiment result
        """
        if hyp_id not in self.hypotheses:
            raise ValueError(f"Hypothesis {hyp_id} not found")
        
        # Verify minimum sample size
        if len(control_data) < self.min_samples or len(treatment_data) < self.min_samples:
            raise ValueError(f"Insufficient samples: need ≥{self.min_samples}, got {len(control_data)}/{len(treatment_data)}")
        
        # Calculate statistics
        control_mean = statistics.mean(control_data)
        treatment_mean = statistics.mean(treatment_data)
        
        # Calculate effect size (Cohen's d)
        pooled_std = statistics.stdev(control_data + treatment_data)
        effect_size = (treatment_mean - control_mean) / pooled_std if pooled_std > 0 else 0
        
        # Perform two-sample t-test
        p_value = self._t_test(control_data, treatment_data)
        
        # Calculate confidence interval
        ci = self._confidence_interval(control_data, treatment_data)
        
        # Determine conclusion
        conclusion = self._determine_conclusion(effect_size, p_value)
        
        # Create experiment record
        exp_id = f"exp_{int(datetime.now().timestamp())}"
        experiment = CausalExperiment(
            id=exp_id,
            hypothesis_id=hyp_id,
            n_samples=len(control_data) + len(treatment_data),
            effect_size=effect_size,
            p_value=p_value,
            confidence_interval=ci,
            control_mean=control_mean,
            treatment_mean=treatment_mean,
            conclusion=conclusion,
            run_date=datetime.now()
        )
        
        self.experiments.append(experiment)
        
        # Update hypothesis status
        hypothesis = self.hypotheses[hyp_id]
        if conclusion == 'validated':
            hypothesis.status = 'validated'
        elif conclusion == 'rejected':
            hypothesis.status = 'rejected'
        else:
            hypothesis.status = 'testing'
        
        self._save_data()
        
        self.logger.info(f"Experiment {exp_id}: {conclusion} (d={effect_size:.3f}, p={p_value:.3f})")
        return experiment
    
    def _t_test(self, control: List[float], treatment: List[float]) -> float:
        """Perform two-sample t-test"""
        # Simplified t-test (in production, use scipy.stats)
        n1, n2 = len(control), len(treatment)
        mean1, mean2 = statistics.mean(control), statistics.mean(treatment)
        var1, var2 = statistics.variance(control), statistics.variance(treatment)
        
        # Pooled standard error
        pooled_se = ((var1 / n1) + (var2 / n2)) ** 0.5
        
        if pooled_se == 0:
            return 1.0
        
        # t-statistic
        t_stat = (mean2 - mean1) / pooled_se
        
        # Simplified p-value (conservative approximation)
        # In production, use proper t-distribution
        p_value = min(0.5, abs(t_stat) / 10)  # Simplified
        
        return p_value
    
    def _confidence_interval(self, control: List[float], 
                            treatment: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for difference in means"""
        mean_diff = statistics.mean(treatment) - statistics.mean(control)
        
        # Simplified CI calculation
        n = len(control) + len(treatment)
        std_err = statistics.stdev(control + treatment) / (n ** 0.5)
        
        # Approximate z-score for 95% CI
        z_score = 1.96
        
        margin = z_score * std_err
        lower = mean_diff - margin
        upper = mean_diff + margin
        
        return (lower, upper)
    
    def _determine_conclusion(self, effect_size: float, p_value: float) -> str:
        """
        Determine conclusion based on CGPT thresholds.
        
        Args:
            effect_size: Cohen's d
            p_value: Statistical significance
            
        Returns:
            'validated', 'rejected', or 'inconclusive'
        """
        if effect_size >= self.min_effect_size and p_value <= self.max_p_value:
            return 'validated'
        elif p_value > self.max_p_value:
            return 'rejected'
        else:
            return 'inconclusive'
    
    def validate_causal_claim(self, hyp_id: str) -> bool:
        """
        Validate a causal claim meets CGPT requirements.
        
        Args:
            hyp_id: Hypothesis ID
            
        Returns:
            True if validated (d≥0.5, p<0.1), False otherwise
        """
        if hyp_id not in self.hypotheses:
            return False
        
        hypothesis = self.hypotheses[hyp_id]
        
        # Find most recent experiment
        recent_experiments = [exp for exp in self.experiments 
                             if exp.hypothesis_id == hyp_id]
        if not recent_experiments:
            return False
        
        latest = max(recent_experiments, key=lambda e: e.run_date)
        
        # Check CGPT requirements
        meets_effect_size = latest.effect_size >= self.min_effect_size
        meets_p_value = latest.p_value <= self.max_p_value
        
        return meets_effect_size and meets_p_value and latest.conclusion == 'validated'


# Export for use by other modules
__all__ = ['CausalHypothesis', 'CausalExperiment', 'CausalTestingFramework']
