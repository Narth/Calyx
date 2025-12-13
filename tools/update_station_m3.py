#!/usr/bin/env python3
"""Update station_calyx init files for Milestone 3."""
from pathlib import Path

# Agents init with temporal
agents_init = '''from .reflector import reflect, save_reflection, format_reflection_markdown, log_reflection_event
from .advisor import generate_advisory, save_advisory, format_advisory_markdown, log_advisory_event, AdvisoryNote, ConfidenceLevel
from .temporal import run_temporal_analysis, save_temporal_analysis, format_temporal_markdown, log_temporal_event, log_finding_events, TrendDirection, FindingType
'''
Path('station_calyx/agents/__init__.py').write_text(agents_init, encoding='utf-8')
print("Updated: agents/__init__.py")

# Main init
main_init = '''"""Station Calyx Ops Reflector v1.2 - Temporal Awareness"""
__version__ = "1.2.0-alpha"
from .core import get_config, append_event, create_event, load_recent_events, get_policy_gate, request_execution
from .core import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent
from .connectors import collect_snapshot
from .agents import reflect, save_reflection, generate_advisory, save_advisory
from .agents import run_temporal_analysis, save_temporal_analysis
'''
Path('station_calyx/__init__.py').write_text(main_init, encoding='utf-8')
print("Updated: __init__.py")

print("\nAll init files updated for Milestone 3!")
