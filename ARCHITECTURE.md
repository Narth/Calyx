# ARCHITECTURE.md
Audio (sounddevice 44.1k) → preprocess (gain cap, dynamic gate) → resample 16k →
faster-whisper (VAD on) → post-filter (short junk) → console/log/handlers

## Heartbeat protocol & Agent1 lifecycle

The Calyx Terminal operates a lightweight heartbeat to verify orchestration health and liveness of the console loop:

- Agent1 (Console Handler / Heartbeat Coordinator) owns the main console I/O loop and emits a periodic "alive" signal via stdout/stderr.
- The watcher daemon monitors the console pipes (quiet mode supported) and confirms each planning cycle completes without deadlock.
- A planning cycle targets ~3s by default and tracks the goal stack: Initialized → Scheduled → Executed → Resolved.
- On success, Agent1 reports a concise status frame (including version and goal snippet), which the watcher treats as the heartbeat.

First synchronized heartbeat (Genesis) was observed after executing the goal "Agent1 say hello", with confirmation lines:

- "Agent1 run complete."
- "Heartbeat shows planning → done, v0.04, goal provided including 'Say hello.'"

Artifacts:

- Log: `outgoing/genesis/LOG_2025-10-21_HEARTBEAT_GENESIS.txt`
- Stability snapshot: `outgoing/genesis/stability_report.json`

Operational notes:

- Heartbeat validates synchronization between the console loop and watcher, timed callbacks, and status rendering (including minimal emoji frames).
- Fail-safes: if timestamps or optional libs are absent, the system degrades gracefully and continues emitting heartbeat frames.
- Use `Scripts/agent_watcher.py --quiet` to run the watcher; `Scripts/agent_console.py` to drive Agent1 locally.
