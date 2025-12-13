"""
Frozen Benchmark Suite - Reproducible evaluation harness for AI-for-All teaching system
Per CGPT recommendation: Maintain /bench/frozen_* with seeds + fixed inputs
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import random


@dataclass
class FrozenBenchmark:
    """Represents a frozen benchmark test case"""
    id: str
    name: str
    description: str
    seed: int
    inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]
    metrics: Dict[str, float]
    created_date: datetime
    data_hash: str
    
    def to_dict(self) -> dict:
        return asdict(self)


class FrozenBenchmarkSuite:
    """
    Maintains frozen benchmarks with fixed seeds and inputs for reproducible evaluation.
    Required before any teaching claim can be promoted per CGPT guardrails.
    """
    
    def __init__(self, bench_dir: Path = None):
        self.bench_dir = bench_dir or Path("outgoing/ai4all/bench")
        self.bench_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load existing benchmarks
        self.benchmarks: Dict[str, FrozenBenchmark] = {}
        self._load_benchmarks()
    
    def _load_benchmarks(self):
        """Load existing frozen benchmarks"""
        bench_file = self.bench_dir / "frozen_benchmarks.json"
        if bench_file.exists():
            try:
                with open(bench_file, 'r') as f:
                    data = json.load(f)
                    for bench_id, bench_data in data.items():
                        bench_data['created_date'] = datetime.fromisoformat(bench_data['created_date'])
                        self.benchmarks[bench_id] = FrozenBenchmark(**bench_data)
                self.logger.info(f"Loaded {len(self.benchmarks)} frozen benchmarks")
            except Exception as e:
                self.logger.warning(f"Failed to load benchmarks: {e}")
    
    def _save_benchmarks(self):
        """Save benchmarks to persistent storage"""
        bench_file = self.bench_dir / "frozen_benchmarks.json"
        try:
            data = {bid: bench.to_dict() for bid, bench in self.benchmarks.items()}
            with open(bench_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to save benchmarks: {e}")
    
    def create_benchmark(self, name: str, description: str, 
                        inputs: Dict[str, Any], expected_outputs: Dict[str, Any],
                        seed: int = None) -> str:
        """
        Create a new frozen benchmark test case.
        
        Args:
            name: Name of the benchmark
            description: Description of what it tests
            inputs: Fixed input data
            expected_outputs: Expected outputs for validation
            seed: Random seed (generated if not provided)
            
        Returns:
            Benchmark ID
        """
        seed = seed or random.randint(1000, 9999)
        
        # Hash the inputs for verification
        input_str = json.dumps(inputs, sort_keys=True)
        data_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        
        bench_id = f"bench_{int(datetime.now().timestamp())}"
        
        benchmark = FrozenBenchmark(
            id=bench_id,
            name=name,
            description=description,
            seed=seed,
            inputs=inputs,
            expected_outputs=expected_outputs,
            metrics={},
            created_date=datetime.now(),
            data_hash=data_hash
        )
        
        self.benchmarks[bench_id] = benchmark
        self._save_benchmarks()
        
        self.logger.info(f"Created frozen benchmark: {bench_id} - {name}")
        return bench_id
    
    def run_benchmark(self, bench_id: str, test_function) -> Dict[str, Any]:
        """
        Run a frozen benchmark test case.
        
        Args:
            bench_id: ID of benchmark to run
            test_function: Function to test (must take inputs dict)
            
        Returns:
            Results dictionary with metrics and validation
        """
        if bench_id not in self.benchmarks:
            raise ValueError(f"Benchmark {bench_id} not found")
        
        benchmark = self.benchmarks[bench_id]
        
        # Set seed for reproducibility
        random.seed(benchmark.seed)
        
        # Run test
        try:
            outputs = test_function(benchmark.inputs)
            
            # Calculate metrics
            metrics = self._calculate_metrics(outputs, benchmark.expected_outputs)
            
            # Update benchmark with results
            benchmark.metrics = metrics
            
            # Validate outputs
            validation = self._validate_outputs(outputs, benchmark.expected_outputs)
            
            self._save_benchmarks()
            
            return {
                'benchmark_id': bench_id,
                'outputs': outputs,
                'metrics': metrics,
                'validation': validation,
                'passed': validation['is_valid']
            }
            
        except Exception as e:
            self.logger.error(f"Benchmark {bench_id} failed: {e}")
            return {
                'benchmark_id': bench_id,
                'error': str(e),
                'passed': False
            }
    
    def _calculate_metrics(self, outputs: Dict[str, Any], 
                          expected: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance metrics from outputs"""
        metrics = {}
        
        # Compare outputs to expected
        for key, expected_value in expected.items():
            if key in outputs:
                actual_value = outputs[key]
                
                # Numeric metrics
                if isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                    difference = abs(actual_value - expected_value)
                    metrics[f"{key}_error"] = difference
                    
                    if expected_value != 0:
                        metrics[f"{key}_percent_error"] = (difference / abs(expected_value)) * 100
        
        return metrics
    
    def _validate_outputs(self, outputs: Dict[str, Any], 
                         expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate outputs against expected values"""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required keys
        missing_keys = set(expected.keys()) - set(outputs.keys())
        if missing_keys:
            validation['is_valid'] = False
            validation['errors'].append(f"Missing keys: {missing_keys}")
        
        # Check values (within tolerance for floats)
        for key, expected_value in expected.items():
            if key in outputs:
                actual_value = outputs[key]
                
                if isinstance(expected_value, float) and isinstance(actual_value, float):
                    tolerance = abs(expected_value) * 0.05  # 5% tolerance
                    if abs(actual_value - expected_value) > tolerance:
                        validation['warnings'].append(
                            f"{key}: expected {expected_value}, got {actual_value}"
                        )
                elif actual_value != expected_value:
                    validation['errors'].append(
                        f"{key}: expected {expected_value}, got {actual_value}"
                    )
                    validation['is_valid'] = False
        
        return validation
    
    def verify_benchmark_integrity(self, bench_id: str) -> bool:
        """Verify benchmark hasn't been modified"""
        if bench_id not in self.benchmarks:
            return False
        
        benchmark = self.benchmarks[bench_id]
        
        # Recalculate hash
        input_str = json.dumps(benchmark.inputs, sort_keys=True)
        current_hash = hashlib.sha256(input_str.encode()).hexdigest()[:16]
        
        return current_hash == benchmark.data_hash
    
    def get_benchmark(self, bench_id: str) -> Optional[FrozenBenchmark]:
        """Get a benchmark by ID"""
        return self.benchmarks.get(bench_id)
    
    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """List all benchmarks"""
        return [bench.to_dict() for bench in self.benchmarks.values()]
    
    def run_all_benchmarks(self, test_function) -> Dict[str, Any]:
        """Run all benchmarks in the suite"""
        results = {}
        
        for bench_id in self.benchmarks.keys():
            results[bench_id] = self.run_benchmark(bench_id, test_function)
        
        # Calculate suite summary
        total = len(results)
        passed = sum(1 for r in results.values() if r.get('passed', False))
        
        return {
            'suite_summary': {
                'total': total,
                'passed': passed,
                'failed': total - passed,
                'pass_rate': passed / total if total > 0 else 0
            },
            'results': results
        }


# Export for use by other modules
__all__ = ['FrozenBenchmark', 'FrozenBenchmarkSuite']
