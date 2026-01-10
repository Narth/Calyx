#!/usr/bin/env python3
"""Helper script to create __init__.py files with correct encoding."""
from pathlib import Path

# Core init
core_init = '''from .config import StationConfig, get_config
from .evidence import append_event, create_event, load_recent_events, get_last_event_ts, compute_sha256, generate_session_id
from .policy import PolicyGate, ExecutionPolicy, ExecutionResult, PolicyDecision, get_policy_gate, request_execution
__version__ = "1.0.0-alpha"
'''
Path('station_calyx/core/__init__.py').write_text(core_init, encoding='utf-8')
print("Created: station_calyx/core/__init__.py")

# Connectors init
conn_init = '''from .sys_telemetry import collect_snapshot, format_snapshot_summary, PSUTIL_AVAILABLE
'''
Path('station_calyx/connectors/__init__.py').write_text(conn_init, encoding='utf-8')
print("Created: station_calyx/connectors/__init__.py")

# Agents init
agents_init = '''from .reflector import reflect, save_reflection, format_reflection_markdown, log_reflection_event
'''
Path('station_calyx/agents/__init__.py').write_text(agents_init, encoding='utf-8')
print("Created: station_calyx/agents/__init__.py")

# API init
api_init = '''from .server import app, run_server
from .routes import router
'''
Path('station_calyx/api/__init__.py').write_text(api_init, encoding='utf-8')
print("Created: station_calyx/api/__init__.py")

# UI init
ui_init = '''from .cli import main as cli_main
'''
Path('station_calyx/ui/__init__.py').write_text(ui_init, encoding='utf-8')
print("Created: station_calyx/ui/__init__.py")

# Main init
main_init = '''"""Station Calyx Ops Reflector v1"""
__version__ = "1.0.0-alpha"
from .core import get_config, append_event, create_event, load_recent_events, get_policy_gate, request_execution
from .connectors import collect_snapshot
from .agents import reflect, save_reflection
'''
Path('station_calyx/__init__.py').write_text(main_init, encoding='utf-8')
print("Created: station_calyx/__init__.py")

print("\nAll __init__.py files created successfully!")
