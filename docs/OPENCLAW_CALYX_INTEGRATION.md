# OpenClaw + Station Calyx Integration

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

## Phase 2: Calyx Governance Bridge (Future)

**Goal:** OpenClaw tools can request execution through Station Calyx contract gate.

**Mechanism:** Custom OpenClaw skill or tool that:
- Accepts execution requests (task_type, scope, constraints).
- Calls Calyx CBO API or writes to mail_inbox.
- Waits for intent pipeline / hub_runner to process.
- Returns receipt or status to OpenClaw.

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

To restrict guild responses to **only** `#station-health` (ID `1465903939659632807`):

1. Get your **Discord Server ID**: Settings → Advanced → Enable Developer Mode; then right-click the server name in the left sidebar → Copy Server ID.
2. In `~/.openclaw/openclaw.json`, under `channels.discord.guilds`, replace `REPLACE_WITH_SERVER_ID` with your actual server ID.
3. Restart the gateway.

With this configured:
- **DMs** from approved users are always delivered to the DM thread.
- **Guild channels:** only `#station-health` is allowed; responses to `#discord-updates` and other channels will not be sent.

---

## Discord Bot Conflict

**One Discord bot = one connection.** You cannot run both:
- Station Calyx `discord_intake` (Python)
- OpenClaw Discord channel

**When using OpenClaw:** Stop discord_intake. OpenClaw handles all Discord traffic.

**When using Calyx-only:** Run discord_intake. No OpenClaw Gateway on Discord.

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

CBO has been granted full read/write/exec permissions via OpenClaw, matching Cursor-level access:

**Enabled Permissions:**
- **Elevated tools:** `tools.elevated.enabled: true` with `allowFrom: ["315642751419023371"]` (Jorge's Discord ID)
- **Tool profile:** `tools.profile: "full"` — all tools available (exec, process, read, write, edit, browser, etc.)
- **Exec approvals:** `channels.discord.execApprovals.enabled: true` with `approvers: ["315642751419023371"]` — you can approve/deny exec requests via Discord when prompted
- **Commands:** `bash: true`, `config: true` — shell commands and config writes enabled
- **Agent defaults:** `elevatedDefault: "on"` — elevated mode enabled by default

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
