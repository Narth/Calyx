"""
AI-for-All Benchmark Module

This module provides comprehensive benchmarking capabilities for the AI-for-All teaching system,
including performance testing, historical comparison, and optimization validation.
"""

from .learning_benchmark import LearningBenchmarkSuite, run_learning_benchmark

__version__ = "1.0.0"
__all__ = [
    "LearningBenchmarkSuite",
    "run_learning_benchmark"
]
