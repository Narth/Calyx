# Discord + Calyx Mail Integration

## Overview

Discord acts as an extension of Calyx Mail, allowing you to speak to CBO via Discord (Station Health channel or DM). CBO processes your message, executes any required node actions on the home node, and responds conversationally. Tool calls are never shown in the response—only the outcome.

## Flow

1. **Message arrives** (Station Health channel or DM from authorized user)
2. **Envelope created** and stored in `telemetry/outbox/intents/`
3. **Phase 1: Tool extraction** — LLM determines if tools are needed (fs_read, fs_list, repo_grep)
4. **Phase 2: Tool execution** — Allowed tools are executed on the home node (Station Calyx)
5. **Phase 3: Conversational response** — LLM generates natural language response using tool results
6. **Response sent** — Only the conversational reply goes to Discord; no JSON or tool names

## Allowed Tools (Policy)

- `fs_read` — Read file contents (path relative to repo)
- `fs_list` — List directory contents
- `repo_grep` — Search for pattern in repo

All tool execution is gated by `benchmarks/harness/policy.py`. Only allowlisted tools run.

## System Context

CBO receives automatic context for each request:

- Current date and time (UTC)
- Node ID (from `runtime/node_id.txt`)
- Station health indicators (contract present, CBO present)

This enables answers like "What is today's date?" without tool calls.

## Response Format

- **Natural language only** — No JSON, no `tool_calls`, no code blocks
- **English** — Responses are in English
- **Concise** — Discord-friendly length

## Configuration

- `runtime/discord_config.json` — Channel allowlist, authorized user ID, station health channel
- `DISCORD_BOT_TOKEN` — Environment variable (never in repo)

## Restart Bot

After code changes:

```bash
# Stop existing bot (Ctrl+C or kill process)
python -m calyx.cbo.discord_intake --run --repo-root .
```
