"""
AI-for-All Teaching Framework

This module provides baseline teaching methods for improving learning and training
efficiency across the Calyx Terminal ecosystem.
"""

from .framework import TeachingFramework
from .adaptive_learner import AdaptiveLearner
from .performance_tracker import PerformanceTracker
from .knowledge_integrator import KnowledgeIntegrator
from .pattern_recognition import PatternRecognition

__version__ = "1.0.0"
__all__ = [
    "TeachingFramework",
    "AdaptiveLearner",
    "PerformanceTracker",
    "KnowledgeIntegrator",
    "PatternRecognition"
]
