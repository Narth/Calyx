# Calyx–CBO Bridge Skill

OpenClaw skill that bridges to Station Calyx: read STATE and send messages to CBO Core. Use from Discord (or other OpenClaw channels) to keep continuity with the station.

## Tools

- **get_state** — Fetches Station Calyx STATE (STATE.md). Use when the user asks for station status, health, or services.
- **send_to_cbo** — Sends a message to CBO Core and returns the reply. Use when the user wants to run a command through the station or talk to CBO. Gateway runs refresh the home node's STATE.md so the hub always has current validation.
- **sponsorship** — Checks if CBO sponsorship is in effect (Architect-signed Calyx Sign).
- **execute** — Routes execution through spine (Mail → Intent → Work Envelope → Contract Gate). Use for spine-routed tasks when the user wants a specific task type executed via governance.

## Requirements

- CBO Core running at `http://127.0.0.1:7778` (or set `cboBaseUrl` in skill config).
- OpenClaw workspace set to the Calyx_Terminal repo (so SOUL.md, USER.md, memory/ are in context).

## Installation

This skill lives in the workspace at `skills/calyx-cbo-bridge/`. If your OpenClaw `agents.defaults.workspace` is set to the Calyx_Terminal path, OpenClaw will discover skills from `workspace/skills/`.

**Tools:** get_state, send_to_cbo, sponsorship, execute.

```json
{
  "skills": {
    "calyx-cbo-bridge": {
      "enabled": true,
      "config": {}
    }
  }
}
```

Optional config: `cboBaseUrl` (default `http://127.0.0.1:7778`).

## Pre-flight

Run before starting the gateway:

```powershell
.\Scripts\openclaw_preflight.ps1
```

This checks Node, workspace path, SOUL.md/USER.md/memory, Discord token, and CBO Core reachability.
