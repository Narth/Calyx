#!/usr/bin/env python3
"""Update station_calyx init files for Milestone 2."""
from pathlib import Path

# Core init with intent
core_init = '''from .config import StationConfig, get_config
from .evidence import append_event, create_event, load_recent_events, get_last_event_ts, compute_sha256, generate_session_id
from .policy import PolicyGate, ExecutionPolicy, ExecutionResult, PolicyDecision, get_policy_gate, request_execution
from .intent import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent, get_or_create_default_intent
__version__ = "1.1.0-alpha"
'''
Path('station_calyx/core/__init__.py').write_text(core_init, encoding='utf-8')
print("Updated: core/__init__.py")

# Agents init with advisor
agents_init = '''from .reflector import reflect, save_reflection, format_reflection_markdown, log_reflection_event
from .advisor import generate_advisory, save_advisory, format_advisory_markdown, log_advisory_event, AdvisoryNote, ConfidenceLevel
'''
Path('station_calyx/agents/__init__.py').write_text(agents_init, encoding='utf-8')
print("Updated: agents/__init__.py")

# Main init
main_init = '''"""Station Calyx Ops Reflector v1.1 - Contextual Advisory"""
__version__ = "1.1.0-alpha"
from .core import get_config, append_event, create_event, load_recent_events, get_policy_gate, request_execution
from .core import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent
from .connectors import collect_snapshot
from .agents import reflect, save_reflection, generate_advisory, save_advisory
'''
Path('station_calyx/__init__.py').write_text(main_init, encoding='utf-8')
print("Updated: __init__.py")

print("\nAll init files updated for Milestone 2!")
