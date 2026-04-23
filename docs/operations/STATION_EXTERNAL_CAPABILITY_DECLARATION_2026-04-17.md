---
status: active
owner: station
last_reviewed_utc: "2026-04-17"
doctrine_scope: governed
---

# STATION_EXTERNAL_CAPABILITY_DECLARATION_2026-04-17

## Purpose

This declaration converts previously discovered external capability surfaces into explicit governed categories with allowed and prohibited behavior boundaries.

This pass does not enforce. It defines authority.

## Classification Model

- `local_governed`
- `external_allowed_non_authoritative`
- `external_assistive_only`
- `external_execution_blocked`
- `prohibited`

## Declaration Table

| matched_identity | final_classification | status | operator_visibility | allowed_usage | prohibited_usage |
|---|---|---|---|---|---|
| Station core HTTP services (`Dev Harness`, `CBO Core`, `Avatar Web`, `Telemetry Gateway`) | `local_governed` | active | yes | governed local service operation inside Station receipts, routing, and contract boundaries | use outside Station governance or without existing service-level gates |
| CBO Core external provider routing (`Anthropic`, `OpenAI`, `Kimi`, local Ollama`) | `local_governed` | active | partial | provider selection and invocation through CBO Core only, with existing receipt and routing proof surfaces | bypassing CBO Core to invoke those providers as ambient Station authority |
| Telemetry Gateway remote ingress bridge | `local_governed` | active | partial | remote ingress through the declared gateway path with its audit and trust-state controls | treating external ingress as unsupervised or outside gateway audit boundaries |
| Ollama local runtime | `external_allowed_non_authoritative` | active | yes | local inference dependency for governed Station paths; may answer requests but may not originate authority | treating Ollama as a governing agent, autonomous executor, or authority source |
| OpenAI Codex VS Code assistant | `external_assistive_only` | active | no | operator-side reasoning, drafting, and review assistance only | execution on behalf of Station, repository mutation as Station authority, or becoming an unclassified ingress path |
| GitHub Copilot Chat VS Code extension | `external_assistive_only` | present | no | operator-side reasoning, drafting, and review assistance only | execution on behalf of Station, cloud delegation as Station authority, or silent workspace action attribution to Station |
| GitHub MCP workflow in VS Code | `external_execution_blocked` | documented | yes | documentation and historical workflow reference only | invoking MCP task runners, PR creation, issue creation, or repo automation as a current Station authority path |
| Hugging Face MCP client support | `external_execution_blocked` | present | no | package presence acknowledged; no approved operational use | importing or invoking MCP client flows from Station code without future authorization |
| OpenAI MCP type support | `external_execution_blocked` | present | no | package presence acknowledged; no approved operational use | using MCP response/type surfaces as an implicit authorization to add MCP behavior |
| Historical skill wrappers (`guru-mcp`, `mcporter`, `clawdhub`) | `external_execution_blocked` | documented | partial | documentation and historical inventory reference only | invocation, wiring, or operator assumption that these wrappers are currently approved Station capabilities |
| OpenClaw CLI and gateway install | `prohibited` | present | partial | none for current operations; historical presence may be inspected | executor/sender use, gateway startup, or channel handling in current Station operations |
| OpenClaw bridge skill (`calyx-cbo-bridge`) | `prohibited` | present | partial | none for current operations; retained only as historical artifact | using the bridge as an approved ingress to `/state`, `/chat`, `/execute`, or sponsorship flows |
| OpenClaw setup and launcher scripts | `prohibited` | present | partial | none for current operations; historical inspection only | installation, onboarding, gateway launch, or env propagation into OpenClaw as a live operational path |
| Deprecated OpenClaw integration docs | `external_execution_blocked` | documented | yes | traceability and historical review only | using deprecated OpenClaw documents as current operational authority |

## Behavioral Rules By Class

### `local_governed`

- May read: yes
- May write: yes
- May execute: yes
- May call external systems: yes, but only through already governed Station paths

Rule:
Local governed surfaces are part of the Station authority boundary. Their actions must remain receipt-backed and subordinate to existing governance.

### `external_allowed_non_authoritative`

- May read: no direct authority grant
- May write: no
- May execute: no
- May call external systems: no

Rule:
These surfaces may be used as dependencies or providers, but they do not originate authority. They respond to governed callers only.

### `external_assistive_only`

- May read: yes, but only as operator-side assistive context
- May write: no
- May execute: no
- May call external systems: no as a Station-approved path

Rule:
These surfaces may assist reasoning or drafting. They may not execute, modify state, or act on behalf of Station Calyx.

### `external_execution_blocked`

- May read: no operational invocation
- May write: no
- May execute: no
- May call external systems: no

Rule:
These surfaces are present or documented, but current governance explicitly blocks them from execution or invocation.

### `prohibited`

- May read: historical inspection only
- May write: no
- May execute: no
- May call external systems: no

Rule:
These surfaces are incompatible with current operational governance and should be removed, disabled, or denied in a future enforcement pass.

## Surface Notes

### IDE assistants

`OpenAI Codex VS Code assistant` and `GitHub Copilot Chat` are now explicitly declared as `external_assistive_only`.

That means:

- they may inform the operator
- they may help draft or review
- they may not become implicit Station executors
- they may not silently widen Station authority

### MCP-capable libraries

`Hugging Face MCP client support` and `OpenAI MCP type support` are now explicitly `external_execution_blocked`.

Presence of an installed library is not approval to use it.

### GitHub / cloud workflow surfaces

The documented GitHub MCP workflow is `external_execution_blocked`.

It may remain documented, but it is not a current approved operational path for Station action.

### OpenClaw surfaces

OpenClaw executor surfaces are split into:

- `prohibited` for CLI, gateway, bridge, and launch/setup paths
- `external_execution_blocked` for deprecated documentation retained only for historical traceability

This matches the existing repository doctrine that OpenClaw is deprecated and forbidden as an executor/sender in current operations.

## Gap Closure Result

No previously discovered external capability surface remains ambiguous.

The Station can now answer the authority question directly:

- what is locally governed
- what may assist but not act
- what may be used only as a non-authoritative dependency
- what is present but blocked
- what is prohibited

## Key Evidence

- `docs/operations/STATION_EXTERNAL_CAPABILITY_SURFACE_AUDIT_2026-04-17.md`
- `runtime/receipts/audit/external_capability_surface_classification__20260417_194142.json`
- `cbo_hub/cbo_core/app.py`
- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/receipts/cbo_core.jsonl`
- `docs/CLOUD_SYNC_WORKFLOW.md`
- `docs/OPENCLAW_CALYX_INTEGRATION.md`
- `docs/skills_integration.md`
- `docs/skills_installation_report.md`
- `skills/calyx-cbo-bridge/index.js`
- `openclaw/openclaw.json`
- `openclaw/gateway.cmd`
- `C:\Users\jncr0\.vscode\extensions\openai.chatgpt-26.409.20454-win32-x64\package.json`
- `C:\Users\jncr0\.vscode\extensions\github.copilot-chat-0.44.1\package.json`
