# HEARTBEAT.md

# Keep this file empty (or with only comments) to skip heartbeat API calls.
# Add tasks below when you want the agent to check something periodically.

## Calyx Core state refresh (do each heartbeat)
1. Run: `Scripts\update_state_checks.ps1` — updates STATE.md with live service checks (dev_harness, cbo_core, avatar_web, telemetry_gateway) and heartbeat_ts.
2. Read STATE.md (Status + checks only). If any check=fail or Status=unhealthy, note it in your response; otherwise HEARTBEAT_OK.
3. **After running start_calyx_core_services.ps1:** Wait ~10s for services to bind, then run `Scripts\update_state_checks.ps1` so STATE.md reflects live status (avoids false "all fail" until next heartbeat).

# Hardware: CPU spikes during GPU work — see docs/HARDWARE_OPTIMIZATION.md (Ollama = main lever when CBO runs).
