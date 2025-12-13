"""
GPU Accelerator - GPU-accelerated training support for AI-for-All teaching system
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np


class GPUAccelerator:
    """
    GPU acceleration layer for AI-for-All teaching system.
    Provides GPU-accelerated computations for pattern recognition, 
    adaptation calculations, and performance analysis.
    """

    def __init__(self, config: dict = None):
        """
        Initialize GPU accelerator.

        Args:
            config: Configuration dictionary with GPU settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Try to import PyTorch for GPU acceleration
        self.device = None
        self.use_gpu = False
        self.torch_available = False
        
        try:
            import torch
            self.torch_available = True
            
            # Check for CUDA availability
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
                self.use_gpu = True
                self.logger.info(f"GPU acceleration enabled on device: {torch.cuda.get_device_name(0)}")
            else:
                self.device = torch.device('cpu')
                self.use_gpu = False
                self.logger.info("CUDA not available, using CPU")
                
        except ImportError:
            self.logger.warning("PyTorch not available, GPU acceleration disabled")
            self.torch_available = False
            self.use_gpu = False

    def accelerate_pattern_recognition(self, patterns: List[Dict], 
                                     similarity_matrix: np.ndarray) -> Dict:
        """
        Accelerate pattern recognition using GPU computation.

        Args:
            patterns: List of pattern dictionaries
            similarity_matrix: Pattern similarity matrix

        Returns:
            Accelerated pattern analysis results
        """
        if not self.torch_available or not self.use_gpu:
            # Fallback to CPU computation
            return self._cpu_pattern_recognition(patterns, similarity_matrix)

        try:
            import torch
            
            # Convert similarity matrix to GPU tensor
            sim_tensor = torch.from_numpy(similarity_matrix).float().to(self.device)
            
            # GPU-accelerated analysis
            # Find strong patterns (similarity > threshold)
            threshold = self.config.get('pattern_threshold', 0.7)
            strong_matches = (sim_tensor > threshold).sum().item()
            
            # Compute pattern clustering (simplified)
            pattern_scores = sim_tensor.mean(dim=1).cpu().numpy()
            
            return {
                'pattern_count': len(patterns),
                'strong_matches': strong_matches,
                'pattern_scores': pattern_scores.tolist(),
                'acceleration': 'gpu',
                'device': str(self.device)
            }
            
        except Exception as e:
            self.logger.error(f"GPU pattern recognition failed: {e}")
            return self._cpu_pattern_recognition(patterns, similarity_matrix)

    def accelerate_adaptation_calculation(self, performance_history: List[Dict],
                                          baseline_metrics: Dict[str, float]) -> Dict:
        """
        Accelerate adaptation parameter calculations using GPU.

        Args:
            performance_history: Historical performance data
            baseline_metrics: Baseline performance metrics

        Returns:
            Optimized adaptation parameters
        """
        if not self.torch_available or not self.use_gpu:
            return self._cpu_adaptation_calculation(performance_history, baseline_metrics)

        try:
            import torch
            
            # Convert performance history to tensors
            metrics = []
            for entry in performance_history[-10:]:  # Last 10 entries
                metric_vector = [
                    entry['metrics'].get('tes', 0),
                    entry['metrics'].get('stability', 0),
                    entry['metrics'].get('velocity', 0),
                    entry['metrics'].get('error_rate', 0)
                ]
                metrics.append(metric_vector)
            
            if not metrics:
                return self._cpu_adaptation_calculation(performance_history, baseline_metrics)
            
            metrics_tensor = torch.tensor(metrics).float().to(self.device)
            
            # GPU-accelerated trend analysis
            # Compute moving average
            window_size = min(5, len(metrics_tensor))
            kernel = torch.ones(1, 1, window_size) / window_size
            kernel = kernel.to(self.device)
            
            # Reshape for convolution
            trend_input = metrics_tensor.unsqueeze(0).unsqueeze(0)
            trends = torch.nn.functional.conv1d(trend_input, kernel).squeeze()
            
            # Calculate improvement rates
            recent_avg = trends[:, -1] if len(trends.shape) > 1 else trends[-1]
            baseline_tensor = torch.tensor([
                baseline_metrics.get('tes', 0),
                baseline_metrics.get('stability', 0),
                baseline_metrics.get('velocity', 0),
                baseline_metrics.get('error_rate', 0)
            ]).float().to(self.device)
            
            improvement = (recent_avg - baseline_tensor) / (baseline_tensor + 1e-6)
            improvement_rate = improvement.mean().item()
            
            # Compute adaptive parameters
            learning_rate = max(0.05, min(0.3, 0.1 * (1 + improvement_rate)))
            momentum = max(0.7, min(0.99, 0.9 + 0.05 * improvement_rate))
            
            return {
                'learning_rate': learning_rate,
                'momentum': momentum,
                'improvement_rate': improvement_rate,
                'acceleration': 'gpu',
                'device': str(self.device)
            }
            
        except Exception as e:
            self.logger.error(f"GPU adaptation calculation failed: {e}")
            return self._cpu_adaptation_calculation(performance_history, baseline_metrics)

    def accelerate_performance_analysis(self, metrics_data: Dict) -> Dict:
        """
        Accelerate performance analysis using GPU tensor operations.

        Args:
            metrics_data: Dictionary of performance metrics

        Returns:
            Analyzed performance statistics
        """
        if not self.torch_available or not self.use_gpu:
            return self._cpu_performance_analysis(metrics_data)

        try:
            import torch
            
            # Convert metrics to tensor
            metric_values = []
            for key in ['tes', 'stability', 'velocity', 'error_rate']:
                metric_values.append(metrics_data.get(key, 0))
            
            metrics_tensor = torch.tensor(metric_values).float().to(self.device)
            
            # GPU-accelerated statistics
            mean_val = metrics_tensor.mean().item()
            std_val = metrics_tensor.std().item()
            max_val = metrics_tensor.max().item()
            min_val = metrics_tensor.min().item()
            
            # Composite score calculation
            weights = torch.tensor([0.4, 0.3, 0.2, 0.1]).to(self.device)
            composite_score = (metrics_tensor * weights).sum().item()
            
            return {
                'mean': mean_val,
                'std': std_val,
                'max': max_val,
                'min': min_val,
                'composite_score': composite_score,
                'acceleration': 'gpu',
                'device': str(self.device)
            }
            
        except Exception as e:
            self.logger.error(f"GPU performance analysis failed: {e}")
            return self._cpu_performance_analysis(metrics_data)

    def _cpu_pattern_recognition(self, patterns: List[Dict], 
                                similarity_matrix: np.ndarray) -> Dict:
        """CPU fallback for pattern recognition"""
        pattern_scores = similarity_matrix.mean(axis=1)
        threshold = self.config.get('pattern_threshold', 0.7)
        strong_matches = (similarity_matrix > threshold).sum()
        
        return {
            'pattern_count': len(patterns),
            'strong_matches': strong_matches,
            'pattern_scores': pattern_scores.tolist(),
            'acceleration': 'cpu'
        }

    def _cpu_adaptation_calculation(self, performance_history: List[Dict],
                                   baseline_metrics: Dict[str, float]) -> Dict:
        """CPU fallback for adaptation calculation"""
        if not performance_history:
            return {'learning_rate': 0.1, 'momentum': 0.9, 'acceleration': 'cpu'}
        
        recent = performance_history[-5:]
        recent_avg = {
            'tes': sum(e['metrics'].get('tes', 0) for e in recent) / len(recent),
            'stability': sum(e['metrics'].get('stability', 0) for e in recent) / len(recent),
            'velocity': sum(e['metrics'].get('velocity', 0) for e in recent) / len(recent),
            'error_rate': sum(e['metrics'].get('error_rate', 0) for e in recent) / len(recent)
        }
        
        improvement_rate = sum(
            (recent_avg[k] - baseline_metrics.get(k, 0)) / (baseline_metrics.get(k, 1) + 1e-6)
            for k in ['tes', 'stability', 'velocity']
        ) / 3
        
        learning_rate = max(0.05, min(0.3, 0.1 * (1 + improvement_rate)))
        momentum = max(0.7, min(0.99, 0.9 + 0.05 * improvement_rate))
        
        return {
            'learning_rate': learning_rate,
            'momentum': momentum,
            'improvement_rate': improvement_rate,
            'acceleration': 'cpu'
        }

    def _cpu_performance_analysis(self, metrics_data: Dict) -> Dict:
        """CPU fallback for performance analysis"""
        values = [metrics_data.get(k, 0) for k in ['tes', 'stability', 'velocity', 'error_rate']]
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        max_val = max(values)
        min_val = min(values)
        
        weights = [0.4, 0.3, 0.2, 0.1]
        composite_score = sum(v * w for v, w in zip(values, weights))
        
        return {
            'mean': mean_val,
            'std': std_val,
            'max': max_val,
            'min': min_val,
            'composite_score': composite_score,
            'acceleration': 'cpu'
        }

    def get_status(self) -> Dict:
        """Get GPU accelerator status"""
        return {
            'gpu_available': self.use_gpu,
            'torch_available': self.torch_available,
            'device': str(self.device) if self.device else 'cpu',
            'config': self.config
        }

