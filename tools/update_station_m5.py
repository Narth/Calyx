#!/usr/bin/env python3
"""Update station_calyx init files for Milestone 5."""
from pathlib import Path

# Core init with service, doctor, onboarding
core_init = '''from .config import StationConfig, get_config
from .evidence import append_event, create_event, load_recent_events, get_last_event_ts, compute_sha256, generate_session_id
from .policy import PolicyGate, ExecutionPolicy, ExecutionResult, PolicyDecision, get_policy_gate, request_execution
from .intent import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent, get_or_create_default_intent
from .notifications import (
    Notification, NotificationPriority, NotificationEmitter,
    get_emitter, emit_notification, check_and_notify,
    get_recent_notifications, get_notifications_from_evidence,
)
from .service import start_service, stop_service, get_service_status
from .doctor import run_all_checks, format_doctor_report
from .onboarding import is_first_run, present_onboarding, load_onboarding
__version__ = "1.4.0-alpha"
'''
Path('station_calyx/core/__init__.py').write_text(core_init, encoding='utf-8')
print("Updated: core/__init__.py")

# Main init
main_init = '''"""Station Calyx Ops Reflector v1.4 - Service Packaging"""
__version__ = "1.4.0-alpha"
from .core import get_config, append_event, create_event, load_recent_events, get_policy_gate, request_execution
from .core import UserIntent, AdvisoryProfile, load_current_intent, save_intent, create_intent
from .core import emit_notification, check_and_notify, get_recent_notifications
from .core import start_service, stop_service, get_service_status
from .core import run_all_checks, is_first_run, present_onboarding
from .connectors import collect_snapshot
from .agents import reflect, save_reflection, generate_advisory, save_advisory
from .agents import run_temporal_analysis, save_temporal_analysis
from .ui import generate_status_surface, save_status_surface
'''
Path('station_calyx/__init__.py').write_text(main_init, encoding='utf-8')
print("Updated: __init__.py")

print("\nAll init files updated for Milestone 5!")
