# HEARTBEAT.md

# Keep this file empty (or with only comments) to skip heartbeat API calls.
# Add tasks below when you want the agent to check something periodically.

## Discord Gateway heartbeat (automatic)
When Calyx Discord Gateway runs with DISCORD_HEARTBEAT_USER_ID set, it sends STATE/HEALTH/checks to that user's DM every 30 min (DISCORD_HEARTBEAT_INTERVAL_MIN). No agent action required.

## Calyx Core state refresh (do each heartbeat)
1. Run: `Scripts\update_state_checks.ps1` — updates STATE.md with live service checks, heartbeat_ts, health, entropy_tier, navigator_interval, triage_status (from station_health_loop + navigator_triage_loop).
2. Run: `Scripts\carbon_intensity.ps1` — fetches Electricity Maps carbon intensity (gCO2eq/kWh); writes runtime/carbon_intensity.json. Requires ELECTRICITY_MAPS_API_KEY. Zone via CARBON_INTENSITY_ZONE (default US).
3. Run: `Scripts\navigator.ps1` — updates outgoing/navigator.lock (interval_status, carbon_intensity, power_window). Remote clients and Telemetry Gateway consumers read this for cadence control.
4. Read STATE.md (Status + checks + health only). If any check=fail, Status=unhealthy, or health=fail, note it in your response; otherwise HEARTBEAT_OK.
5. **After running start_calyx_core_services.ps1:** Wait ~10s for services to bind, then run `Scripts\update_state_checks.ps1` so STATE.md reflects live status (avoids false "all fail" until next heartbeat).

## Station health loop (1s schedule)
- Start: `Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','Scripts\station_health_loop.ps1' -WindowStyle Hidden` (or run in a separate terminal).
- Stop: create `runtime\station_health.stop`; loop exits and removes the file.
- Writes: `runtime\station_health.json` (health, health_ts, cpu_pct, ram_pct, top processes). update_state_checks reads this and merges health into STATE.md. Default 1s; use -IntervalSec N to override.
- **Discord CPU/RAM:** Both the scheduled heartbeat and CBO /chat (heartbeat intent) read CPU/RAM from station_health.json. Sunrise starts the loop; if stopped, restart manually or run sunrise again.

# Airflow: Throttle ingestion; direct energy to writing. Health/State on 1s; hardware ingestion committed to this node during maintenance.
# Hardware: CPU spikes during GPU work — see docs/HARDWARE_OPTIMIZATION.md (Ollama = main lever when CBO runs).
