"""
AI-for-All Integration Module

This module provides integration capabilities for the AI-for-All teaching system
with existing Calyx Terminal agents.
"""

from .production_agent_hooks import (
    AgentTeachingHook,
    ProductionIntegrationManager,
    create_integration_manager,
    create_production_integration,
    integrate_with_agent1,
    integrate_with_triage,
    integrate_with_copilot,
    integrate_agent1,
    integrate_triage
)

__version__ = "1.0.0"
__all__ = [
    "AgentTeachingHook",
    "ProductionIntegrationManager",
    "create_integration_manager",
    "create_production_integration",
    "integrate_with_agent1",
    "integrate_with_triage",
    "integrate_with_copilot",
    "integrate_agent1",
    "integrate_triage"
]
