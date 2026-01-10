#!/usr/bin/env python3
"""Update station_calyx init files for Milestone 4."""
from pathlib import Path

# Core init with notifications
core_init = '''from .config import StationConfig, get_config
from .evidence import append_event, create_event, load_recent_events, get_last_event_ts, compute_sha256, generate_session_id
from .policy import PolicyGate, ExecutionPolicy, ExecutionResult, PolicyDecision, get_policy_gate, request_execution
from .intent import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent, get_or_create_default_intent
from .notifications import (
    Notification, NotificationPriority, NotificationEmitter,
    get_emitter, emit_notification, check_and_notify,
    get_recent_notifications, get_notifications_from_evidence,
)
__version__ = "1.3.0-alpha"
'''
Path('station_calyx/core/__init__.py').write_text(core_init, encoding='utf-8')
print("Updated: core/__init__.py")

# UI init with status_surface
ui_init = '''from .cli import main as cli_main
from .status_surface import (
    generate_status_surface,
    format_status_markdown,
    save_status_surface,
    load_status_surface,
)
'''
Path('station_calyx/ui/__init__.py').write_text(ui_init, encoding='utf-8')
print("Updated: ui/__init__.py")

# Main init
main_init = '''"""Station Calyx Ops Reflector v1.3 - Trust Surface"""
__version__ = "1.3.0-alpha"
from .core import get_config, append_event, create_event, load_recent_events, get_policy_gate, request_execution
from .core import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent
from .core import emit_notification, check_and_notify, get_recent_notifications
from .connectors import collect_snapshot
from .agents import reflect, save_reflection, generate_advisory, save_advisory
from .agents import run_temporal_analysis, save_temporal_analysis
from .ui import generate_status_surface, save_status_surface
'''
Path('station_calyx/__init__.py').write_text(main_init, encoding='utf-8')
print("Updated: __init__.py")

print("\nAll init files updated for Milestone 4!")
