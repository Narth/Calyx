"""Station Calyx Ops Reflector v1.4 - Service Packaging"""
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
