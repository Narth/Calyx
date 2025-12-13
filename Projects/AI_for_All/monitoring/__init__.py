"""
AI-for-All Monitoring Module

This module provides monitoring and alerting capabilities for the AI-for-All teaching system.
"""

from .production_monitor import ProductionMonitor

__version__ = "1.0.0"
__all__ = [
    "ProductionMonitor"
]
