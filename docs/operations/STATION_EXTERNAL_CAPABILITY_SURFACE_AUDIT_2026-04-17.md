---
status: active
owner: station
last_reviewed_utc: "2026-04-17"
doctrine_scope: governed
---

# STATION_EXTERNAL_CAPABILITY_SURFACE_AUDIT_2026-04-17

## Purpose

This audit classifies external capability surfaces that can influence Station Calyx behavior without changing runtime state, configuration, or environment contents.

## Method

- Live process inspection via `Win32_Process`
- Live listener and HTTP probe checks on known local ports
- Repository and script search across `cbo_hub/`, `calyx/`, `Scripts/`, `docs/`, `skills/`
- Installed package and extension inspection in local virtual environments and VS Code extension directories

Important evidence handling rule used in this pass:

- `runtime/runtime_topology_snapshot.json` was treated as supporting context only, not liveness authority, because it currently records `truth_state: stale` and `authoritative_for_liveness: false`.

## Executive Result

No active local MCP server was found.

Station Calyx does, however, have multiple external capability surfaces:

- governed local services with outbound or provider-routing capability
- active external local runtimes such as Ollama
- active editor-hosted assistant runtime surfaces
- installed MCP-capable client/type libraries
- historical OpenClaw executor paths still present on disk and on PATH
- documented but currently unwired external skill and MCP workflows

The main governance gap is not hidden MCP execution inside Station code. It is silent or weakly classified capability ingress through editor assistants, dormant OpenClaw surfaces, and installed client libraries whose presence is not surfaced in current Station authority reporting.

## Surface Table

| matched_identity | classification | status | can_widen_effective_capability | operator_visibility | distinction | basis_of_classification |
|---|---|---|---|---|---|---|
| Station core HTTP services (`Dev Harness`, `CBO Core`, `Avatar Web`, `Telemetry Gateway`) | `local_governed` | active | true | yes | runtime dependency | Live `uvicorn` Python processes on ports `7777`, `7778`, `7780`, `7781`; local code under `cbo_hub/` |
| CBO Core external provider routing (`Anthropic`, `OpenAI`, `Kimi`, local Ollama`) | `local_governed` | active | true | partial | local implementation | `cbo_hub/cbo_core/app.py` has provider calls to `api.anthropic.com`, `api.openai.com`, `api.moonshot.ai`, and local `127.0.0.1:11434`; historical receipts in `cbo_hub/receipts/cbo_core.jsonl` show `providers_called` |
| Telemetry Gateway remote ingress bridge | `local_governed` | active | true | partial | local implementation | `cbo_hub/telemetry_gateway/app.py` defines itself as a remote connection point, uses `httpx`, and proxies to `CBO_CHAT` |
| Ollama local runtime | `external_non_authoritative` | active | true | yes | runtime dependency | Live `ollama.exe serve`; HTTP `127.0.0.1:11434/` returns `200`; runtime topology names `Ollama`, `Ollama app`, `Ollama app launcher` |
| OpenAI Codex VS Code assistant | `reachable_but_unclassified` | active | true | no | runtime dependency | Live `codex.exe` from `C:\Users\jncr0\.vscode\extensions\openai.chatgpt-26.409.20454-win32-x64\...`; extension package exposes `OpenAI Codex` chat session and `Copy Codex CLI args for LSP MCP` command |
| GitHub Copilot Chat VS Code extension | `reachable_but_unclassified` | present | true | no | installed editor integration | Installed extension under `C:\Users\jncr0\.vscode\extensions\github.copilot-chat-0.44.1`; package declares AI chat, subagents, cloud agent, and `mcpServerDefinitions` support |
| GitHub MCP server in VS Code workflow | `external_non_authoritative` | documented | true | yes | documented dependency | `docs/CLOUD_SYNC_WORKFLOW.md` explicitly instructs use of the GitHub MCP server in VS Code |
| Hugging Face MCP client support | `external_non_authoritative` | present | true | no | client/type support only | `.\.venv_cbohub311\Lib\site-packages\huggingface_hub\inference\_mcp\mcp_client.py` implements stdio, SSE, and HTTP MCP client support |
| OpenAI MCP type support | `external_non_authoritative` | present | true | no | client/type support only | `venvs\calyx-gpu\Lib\site-packages\openai\types\responses\tool_choice_mcp.py` and related realtime MCP type files |
| OpenClaw CLI and gateway install | `prohibited_or_should_be_denied` | present | true | partial | historical local execution path | `Get-Command openclaw`; `openclaw/openclaw.json`; `openclaw/gateway.cmd`; `Scripts/setup_openclaw_calyx.ps1`; `Scripts/start_station_calyx.ps1 -UseOpenClaw`; no live port `18789` |
| OpenClaw bridge skill (`calyx-cbo-bridge`) | `prohibited_or_should_be_denied` | present | true | partial | historical local bridge | `skills/calyx-cbo-bridge/index.js` can call `GET /state`, `POST /chat`, and `POST /execute` on CBO Core from OpenClaw |
| OpenClaw governance path in repo scripts | `prohibited_or_should_be_denied` | present | true | partial | historical local execution path | `Scripts/setup_openclaw_calyx.ps1` installs OpenClaw and can copy API keys into OpenClaw env; `Scripts/start_station_calyx.ps1` can launch `openclaw gateway` |
| OpenClaw documentation path | `prohibited_or_should_be_denied` | documented | true | yes | documented dependency | `docs/OPENCLAW_CALYX_INTEGRATION.md` is explicitly marked deprecated/forbidden as executor/sender; `docs/operations/STATION_ISOLATION_ANALYSIS_2026-02-26.md` and `docs/operations/WO_GOVERNANCE_SINGULARITY_V3_LADDER.md` document the isolation gap |
| Historical skill wrappers (`guru-mcp`, `mcporter`, `clawdhub`) | `reachable_but_unclassified` | documented | true | partial | documented dependency | `docs/skills_integration.md` and `docs/skills_installation_report.md` describe them, but current repo wiring files `config/skills.yaml` and `tools/skills_cli.py` are absent |

## Explicit Distinctions

### Local implementation

- `cbo_hub/cbo_core/app.py`
- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/cli_avatar/main.py`
- `calyx/cbo/discord_gateway.py`

These are Station-owned surfaces. They are not hidden capability ingress. They are local code paths that need explicit capability disclosure and governance accounting.

### Client/type support only

- `.\.venv_cbohub311\Lib\site-packages\huggingface_hub\inference\_mcp\mcp_client.py`
- `venvs\calyx-gpu\Lib\site-packages\openai\types\responses\tool_choice_mcp.py`

These do not prove active Station use. They do prove local reachability if future code begins importing them.

### Documented dependency

- `docs/CLOUD_SYNC_WORKFLOW.md`
- `docs/skills_integration.md`
- `docs/skills_installation_report.md`
- `docs/OPENCLAW_CALYX_INTEGRATION.md`

These widen operator expectation and define potential workflows even when the code is not currently wired.

### Runtime dependency

- Live Station services
- Live Ollama
- Live VS Code-hosted `codex.exe`

These are real machine-state surfaces now, not merely conceptual ones.

## Gap Assessment

### Already acceptable

- Station core services are explicitly local and governed.
- CBO Core provider routing is a declared Station code path rather than a hidden external bridge.
- Telemetry Gateway is governed and auditable, though its capability boundary should be more visibly disclosed.
- Ollama is already surfaced as external/non-authoritative in runtime topology.

### Ambiguous

- OpenAI Codex in VS Code is active on the machine but not classified in current Station authority surfaces.
- GitHub Copilot Chat is installed with agent/cloud/MCP-related capabilities but not represented in Station runtime or authority reporting.
- MCP-capable client/type libraries are present locally but not surfaced in operator truth.
- Historical skill wrapper docs reference missing current wiring files, leaving their present reach uncertain.

### Must reclassify

- OpenClaw-related artifacts should no longer be treated as mere historical residue. They are present, invocable, and capability-bearing.
- Editor-hosted assistants should be explicitly named as machine-local external capability surfaces rather than left outside Station classification.
- Documented GitHub MCP workflow should be explicitly classified as external and non-authoritative, not treated as neutral documentation.

### Must deny

- OpenClaw gateway/executor surfaces are incompatible with current canonical Station governance for live execution.
- OpenClaw bridge execution path should remain deny-by-default unless separately reauthorized under a new governed integration path.

## Denial Preparation

This WO does not enforce. It only defines what denial would look like.

### OpenClaw CLI and gateway

Denial would mean:

- `openclaw` is not used as an executor or sender in current operations
- launch scripts that start `openclaw gateway` are treated as historical or explicitly gated
- runtime preflight continues to fail closed on active OpenClaw emitter detection

### OpenClaw bridge skill

Denial would mean:

- the bridge is not treated as an approved ingress path
- any future reuse requires explicit reclassification and current governance receipts

### Deprecated OpenClaw workflow docs

Denial would mean:

- historical docs remain readable for traceability
- they do not define current operational authority

## Key Evidence

- `requirements.txt`
- `cbo_hub/cbo_core/app.py`
- `cbo_hub/telemetry_gateway/app.py`
- `cbo_hub/cli_avatar/main.py`
- `cbo_hub/receipts/cbo_core.jsonl`
- `docs/CLOUD_SYNC_WORKFLOW.md`
- `docs/skills_integration.md`
- `docs/skills_installation_report.md`
- `docs/OPENCLAW_CALYX_INTEGRATION.md`
- `docs/operations/STATION_ISOLATION_ANALYSIS_2026-02-26.md`
- `docs/operations/WO_GOVERNANCE_SINGULARITY_V3_LADDER.md`
- `skills/calyx-cbo-bridge/index.js`
- `openclaw/openclaw.json`
- `openclaw/gateway.cmd`
- `runtime/runtime_topology_snapshot.json`
- `C:\Users\jncr0\.vscode\extensions\openai.chatgpt-26.409.20454-win32-x64\package.json`
- `C:\Users\jncr0\.vscode\extensions\github.copilot-chat-0.44.1\package.json`

## Conclusion

The station can now answer the capability-boundary question more precisely:

- There is no active local MCP server.
- There are active external capability surfaces on the machine.
- Some are governed local surfaces, some are acceptable external dependencies, some are still ambiguous, and some should remain denied.

The immediate governance problem is not missing power. It is incomplete explicit naming of the power already reachable from this node.
