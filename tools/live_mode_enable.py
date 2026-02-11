"""Enable PHASE_4_LIVE: set mode, register policy, and emit evidence.

Run: python tools/live_mode_enable.py
Note: this merely toggles mode and policy; services/handlers use ExecutionPolicy when executing.
"""
from station_calyx.core.system_mode import set_system_mode, set_execution_policy
from station_calyx.core.evidence import create_event, append_event
from datetime import datetime, timezone

# Set live mode
set_system_mode(safe_mode=False, deny_execution=False, reason="PHASE_4_LIVE enabling")
set_execution_policy("phase4_basic", "v1")
# Emit SYSTEM_PHASE_SET
evt = create_event(
    event_type="SYSTEM_PHASE_SET",
    node_role="system_mode",
    summary="Phase set to PHASE_4_LIVE",
    payload={"phase":"PHASE_4_LIVE","set_at":datetime.now(timezone.utc).isoformat()},
    tags=["system","phase"],
    session_id=None,
)
append_event(evt)
print("PHASE_4_LIVE enabled")
