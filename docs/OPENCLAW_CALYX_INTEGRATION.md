---
status: deprecated
owner: station
last_reviewed_utc: "2026-02-27"
superseded_by: docs/operations/CANONICAL_OPS_INDEX.md
doctrine_scope: historical
---

# OpenClaw + Station Calyx Integration

**Historical note:** OpenClaw helped bring the Station Calyx dream to fruition. This doc preserves that integration path. It is not erased — it is remembered.

> **⚠️ OpenClaw is deprecated and forbidden as an executor/sender.**
> **If OpenClaw is running, Calyx may enter fail-closed mode.** See docs/operations/OPENCLAW_DECOMMISSION_PLAYBOOK.md.

**DO NOT USE FOR CURRENT OPS.** This doc is deprecated. Canonical Discord executor is Calyx Discord Gateway. See docs/operations/CANONICAL_OPS_INDEX.md.

**Why deprecated:** Station Calyx canonical path is Calyx Discord Gateway (task-governed, governed ingress). OpenClaw integration is optional/alternative; current ops use Calyx Gateway only.

**Purpose:** Deliver OpenClaw-level assistant capabilities (multi-channel, voice, skills, tools) while preserving Station Calyx governance and spine.

**Reference:** [OpenClaw GitHub](https://github.com/openclaw/openclaw)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OpenClaw Gateway (port 18789)                         │
│  Discord | WhatsApp | Telegram | Slack | WebChat | Voice | Canvas | Skills   │
└─────────────────────────────────────────────┬───────────────────────────────┘
                                              │
                    agents.defaults.workspace = Calyx_Terminal
                    (AGENTS.md, SOUL.md, USER.md, TOOLS.md, memory/)
                                              │
┌─────────────────────────────────────────────▼───────────────────────────────┐
│                        Station Calyx (CBO + spine)                            │
│  Contract gate | Intent pipeline | Execution | Receipts | Bridge pulse       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Roles:**
- **OpenClaw:** Assistant surface — channels, voice, skills, conversational response.
- **Calyx workspace:** AGENTS.md, SOUL.md, USER.md, memory, skills — CBO identity and context.
- **Station Calyx:** Governance backend — contract validation, execution gate, receipts (optional bridge via tools).

---

## Phase 1: OpenClaw + Calyx Workspace (Immediate)

**Goal:** OpenClaw handles Discord (and other channels) using Calyx_Terminal as workspace. CBO identity and memory from Calyx.

**Steps:**
1. Install OpenClaw: `npm install -g openclaw@latest` (Node ≥22 required).
2. Configure workspace: set `agents.defaults.workspace` to Calyx_Terminal path.
3. Configure Discord: `DISCORD_BOT_TOKEN` (reuse existing).
4. **Model:** Use Ollama (local tool-capable model) or cloud API:
   - **Ollama (default):** `.\scripts\setup_openclaw_calyx.ps1 -UseOllama -OllamaModel qwen2.5-coder:7b -StartGateway`. Uses `qwen2.5-coder:7b` — **supports tool calling** (required for full CBO capabilities). Requires Ollama installed and running.
   - **NVIDIA-recommended (8–12GB GPU):** `qwen3:4b-thinking-2507-q4_K_M` — see [NVIDIA OpenClaw guide](https://www.nvidia.com/en-us/geforce/news/open-claw-rtx-gpu-dgx-spark-guide/). Use only after setting `OLLAMA_NUM_CTX=32768` and restarting Ollama; if you see "This operation was aborted" on every Discord reply, switch back to `qwen3:8b` (thinking models can time out or break tool streams).
   - **Default / most reliable:** `qwen3:8b` — tool-capable, stable with Discord.
   - **Tool-capable alternatives:** `llama3.1:8b`, `mistral:7b` — OpenClaw auto-discovery shows only models with tool support.
   - **Avoid:** `codellama:13b` — does not support tools; plain chat only.
   - **Cloud:** set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in `~/.openclaw/.env`.
5. Run: `openclaw onboard --install-daemon` then `openclaw gateway --port 18789`.
6. **Stop Station Calyx discord_intake** — same bot token cannot connect twice. OpenClaw becomes sole Discord handler.
7. **WO_HEARTBEAT_SENDER_UNIFICATION_V1:** If OpenClaw has a periodic heartbeat/status push feature, disable it. The canonical Discord heartbeat sender is the task-governed Calyx Discord Gateway. When OpenClaw is the Discord handler, it must not schedule or send heartbeats.

**Subagent spawning:** The setup script enables subagent spawning for CBO and adds CBO to the subagent allowlist: `agents.defaults.subagents.allowAgents` and `agents.list[].subagents.allowAgents` include `"cbo"`; `maxSpawnDepth: 2` allows one level of nesting. Add more agent ids to the allowlist in openclaw.json if you define additional agents.

**Config fragment** (merge into `~/.openclaw/openclaw.json`):

```json
{
  "agents": {
    "defaults": {
      "workspace": "<ABSOLUTE_PATH_TO_Calyx_Terminal>",
      "model": "anthropic/claude-sonnet-4-20250514"
    }
  },
  "channels": {
    "discord": {
      "token": "<from DISCORD_BOT_TOKEN env>"
    }
  }
}
```

---

## Phase 2: Calyx Governance Bridge (Implemented)

**Goal:** OpenClaw can query station state and send commands to CBO Core.

**Mechanism:** The **calyx-cbo-bridge** skill (`skills/calyx-cbo-bridge/`):
- **get_state** — Calls CBO Core GET /state; returns STATE.md for station status, health, services.
- **send_to_cbo** — Calls CBO Core POST /chat with a message and optional model_role; returns CBO reply and receipt.
- **sponsorship** — Calls CBO Core GET /sponsorship; returns sponsorship validity for stamping gates.
- **execute** — Calls CBO Core POST /execute for spine-routed execution (Mail → Intent → Work Envelope → Contract Gate → Execution).

Run pre-flight (`Scripts\openclaw_preflight.ps1`) and ensure CBO Core is running so the bridge can connect. See `docs/operations/GOVERNANCE_INTEGRATION_2026-02.md` for integrity gate, stamping, and spine integration details.

---

## Phase 3: Full Feature Parity (Roadmap)

| OpenClaw feature       | Calyx integration                          |
|------------------------|--------------------------------------------|
| Multi-channel          | OpenClaw native; Calyx receives via mail   |
| Voice Wake / Talk Mode | OpenClaw native                            |
| Skills platform        | OpenClaw skills + Calyx TOOLS.md           |
| Browser control        | OpenClaw tool; sandbox per Calyx policy    |
| Canvas                 | OpenClaw A2UI                              |
| Sessions / mesh        | OpenClaw native                            |

---

## Discord Channel Restriction (Station Health Only)

To restrict guild responses to **only** your station-health channel:

1. Get your **Discord Server ID**: Settings → Advanced → Enable Developer Mode; then right-click the server name in the left sidebar → Copy Server ID.
2. In `~/.openclaw/openclaw.json`, under `channels.discord.guilds`, replace `REPLACE_WITH_SERVER_ID` with your actual server ID.
3. Restart the gateway.

With this configured:
- **DMs** from approved users (see `allowFrom` / `approvers` below) are always delivered to the DM thread.
- **Guild channels:** only the configured station-health channel is allowed; other channels will not receive responses.

---

## Discord Bot Conflict

**One Discord bot = one connection.** You cannot run both:
- Station Calyx `discord_intake` (Python)
- OpenClaw Discord channel
- Calyx Discord Gateway (Python)

**Governed Discord (recommended):** Run `Scripts\start_station_governed.ps1`. Uses Calyx Discord Gateway — all Discord DM traffic routes to CBO Core. No OpenClaw for Discord. Full governance, ledger visibility.

**When using OpenClaw for Discord:** Stop Calyx Discord Gateway and discord_intake. OpenClaw handles Discord — but messages do NOT route to CBO by default (only when the model invokes calyx-cbo-bridge). For governance, use the harness instead.

**When using Calyx-only (Mail spine):** Run discord_intake. No OpenClaw Gateway or Calyx Discord Gateway on Discord.

---

## Platform Notes

**Windows:** OpenClaw recommends WSL2 for best experience. Native Windows may work; verify Node ≥22.

**Node:** `node --version` must be ≥22.

---

## Hardware Optimization (Slow Responses)

If responses take 10+ minutes on resource-constrained nodes:

1. **Increase timeout:** Set `agents.defaults.timeoutSeconds` in `~/.openclaw/openclaw.json` (e.g. `900` for 15 min). Restart gateway after changes.
2. **Smaller model:** Use `qwen2.5-coder:7b` or `qwen2.5:7b` instead of `qwen3:8b` for faster inference (fewer parameters).
3. **Ollama:** Ensure no other heavy Ollama workloads are running; consider `OLLAMA_NUM_PARALLEL=1` if memory is tight.

---

## CBO Permissions & Capabilities (Full Access)

CBO can be granted full read/write/exec permissions via OpenClaw, matching Cursor-level access:

**Enabled Permissions (example):**
- **Elevated tools:** `tools.elevated.enabled: true` with `allowFrom: ["<YOUR_DISCORD_USER_ID>"]` — restrict to your Discord user ID.
- **Tool profile:** `tools.profile: "full"` — all tools available (exec, process, read, write, edit, browser, etc.)
- **Exec approvals:** `channels.discord.execApprovals.enabled: true` with `approvers: ["<YOUR_DISCORD_USER_ID>"]` — approve/deny exec requests via Discord when prompted.
- **Commands:** `bash: true`, `config: true` — shell commands and config writes enabled.
- **Agent defaults:** `elevatedDefault: "on"` — elevated mode enabled by default.

*Store your real Discord user ID in a local, non-committed file (e.g. `private/DISCORD_IDS.md`).*

**What CBO Can Do:**
- Execute any system command (`nvidia-smi`, `ollama ps`, `git`, etc.) without approval prompts
- Read/write/edit files in workspace and system
- Run diagnostic commands, commit changes, manage processes
- Access GPU/system resources for troubleshooting
- Modify OpenClaw config via `/config` commands

**Restart Required:** After config changes, restart the OpenClaw gateway for permissions to take effect.

---

## NVIDIA guide alignment

Per the [NVIDIA OpenClaw + RTX guide](https://www.nvidia.com/en-us/geforce/news/open-claw-rtx-gpu-dgx-spark-guide/):

| Step | Our setup |
|------|-----------|
| 8–12GB GPU model | `qwen3:4b-thinking-2507-q4_K_M` (installed). If you get "This operation was aborted" on every reply, primary is set to `qwen3:8b` instead. |
| Context 32K+ | `OLLAMA_NUM_CTX=32768` in `~/.openclaw/.env`; restart Ollama so new loads use 32K context. |
| Ollama + OpenClaw | We use `openclaw gateway --port 18789` (no WSL); config in `~/.openclaw/openclaw.json`. |

**"Operation was aborted"** often comes from: request timeout during long thinking, or tool-calling/stream handling with the 4b-thinking model. Using `qwen3:8b` as primary avoids that; you can try 4b-thinking again after setting `OLLAMA_NUM_CTX=32768` and restarting Ollama.

---

## Verification: Hooks, Harnesses, and Continuity (Discord / Laptop)

When you work from your laptop via OpenClaw’s Discord integration, the following should be in place so **system STATE and CBO continuity** are retained.

### Checklist (verify after setup)

| Item | Where | Purpose |
|------|--------|---------|
| **Workspace path** | `~/.openclaw/openclaw.json` → `agents.defaults.workspace` | Must be the **absolute path** to `C:\Calyx_Terminal` (or your Calyx repo). OpenClaw loads AGENTS.md, SOUL.md, USER.md, memory/ from this workspace. |
| **Setup script** | `Scripts\setup_openclaw_calyx.ps1` | Writes workspace and Discord token into OpenClaw config. Re-run after moving the repo or changing token. |
| **Pre-flight** | `Scripts\openclaw_preflight.ps1` | Checks Node, workspace path, SOUL.md/USER.md/memory, Discord token, and optionally CBO Core. Run before starting the gateway. |
| **Bridge skill** | `skills/calyx-cbo-bridge/` | get_state and send_to_cbo tools. Register in openclaw.json if required; ensure workspace is Calyx_Terminal so the skill is discovered. |
| **Start script** | `Scripts\start_station_calyx.ps1 -UseOpenClaw` | Starts OpenClaw gateway (port 18789) with Calyx workspace; stops any legacy `discord_intake` so one bot only. |
| **AGENTS.md / SOUL.md / USER.md** | Repo root | OpenClaw uses the workspace as the agent’s “home” — these files define identity and session rules. Ensure they are present and up to date. |
| **memory/** | `memory/YYYY-MM-DD.md` | Daily context; OpenClaw can read these for recent continuity. |
| **MEMORY.md** | Repo root | Long-term curated memory. AGENTS.md says load only in “main session” (direct chat with human). For Discord DMs with you, if OpenClaw treats that as a main session, it may load MEMORY.md — confirm in OpenClaw docs or config if you want full continuity there. |
| **STATE.md** | Repo root | Used by **CBO Core** (Avatar Web, Telemetry Gateway) when injecting context into /chat. OpenClaw does **not** call CBO Core by default; it uses the workspace files. So STATE.md is for CBO API/Telemetry flows; OpenClaw continuity comes from workspace files above. |
| **One Discord bot** | Either OpenClaw **or** legacy discord_intake | Do not run both. For “Discord + OpenClaw,” use only OpenClaw; stop any `calyx.cbo.discord_intake` or similar. |

### Hooks and wrappers in this repo

- **Workspace hook:** OpenClaw’s `agents.defaults.workspace` points at Calyx_Terminal; no code change in OpenClaw itself — config only.
- **Harness:** `Scripts\setup_openclaw_calyx.ps1` configures OpenClaw; `Scripts\start_station_calyx.ps1 -UseOpenClaw` starts the gateway.
- **Pre-flight:** `Scripts\openclaw_preflight.ps1` verifies Node, workspace, identity files, Discord token, and optionally CBO Core before starting.
- **Bridge skill:** `skills/calyx-cbo-bridge/` — OpenClaw skill with tools **get_state** (CBO Core GET /state) and **send_to_cbo** (CBO Core POST /chat). Discord and other channels can read station STATE and send commands to CBO.
- **Profile template:** `openclaw/calyx-profile.json` is a reference; the live config is `~/.openclaw/openclaw.json` (written by setup script).
- **Phase 2 (future):** A custom OpenClaw skill or tool that calls CBO Core `/chat` or Calyx mail would be a “governance bridge” — not yet implemented. Today, Discord → OpenClaw → workspace (AGENTS, SOUL, USER, memory); CBO Core is used by Avatar Web and Telemetry Gateway separately.

### Continuity when continuing from the laptop

- **Identity:** SOUL.md and USER.md in the workspace give OpenClaw the same CBO/human context.
- **Recent context:** `memory/YYYY-MM-DD.md` (today and yesterday) and, if applicable, MEMORY.md.
- **State of the station:** Use the **calyx-cbo-bridge** skill: **get_state** returns STATE from CBO Core; **send_to_cbo** sends messages to CBO. STATE.md is also updated by heartbeats (`Scripts\update_state_checks.ps1`). Continuity: workspace files (SOUL, USER, memory) plus bridge for STATE and CBO replies.

### Subagents and allowlist

Subagent spawning is enabled via the setup script: `agents.defaults.subagents.allowAgents` and the **cbo** agent in `agents.list` have `allowAgents: ["cbo"]`, and `maxSpawnDepth: 2` so CBO can spawn subagents (and they can spawn one more level). To add more agents (e.g. explore, shell, or custom ids): add entries to `agents.list` in `~/.openclaw/openclaw.json` and include their `id` in `agents.defaults.subagents.allowAgents` and in each agent's `subagents.allowAgents`. Use `["*"]` to allow any defined agent. Restart the gateway after config changes.
