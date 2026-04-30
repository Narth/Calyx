# Calyx Local MCP Server

Status: canonical support

The Station Calyx MCP server is a local stdio support surface. It is not a control plane, not runtime continuity authority, and not a retroactive memory-ingestion authority by itself.

## Scope

Approved workstation roots:

- `C:\Calyx_Terminal`
- `C:\Calyx_Test_Temp`
- `C:\Calyx_Parking`
- `C:\Calyx_Federation_Inbox`
- `D:\Calyx_Data`

All path access must resolve inside one of those roots. Paths outside scope are denied.

## Mode

- Transport: stdio MCP JSON-RPC
- Authority: canonical support
- Default posture: read-only
- External network: none
- Writes: none
- Retroactive context ingestion: not enabled

## Launcher

Validation with operator-visible output:

```powershell
Scripts\start_calyx_mcp_stdio.ps1 -Validate
```

Client-style smoke test with operator-visible MCP response:

```powershell
Scripts\start_calyx_mcp_stdio.ps1 -SmokeTest
```

MCP stdio command. This is intentionally quiet when run directly because stdio MCP servers wait for a client to send JSON-RPC frames:

```powershell
Scripts\start_calyx_mcp_stdio.ps1
```

Direct Python command:

```powershell
.\.venv_cbohub311\Scripts\python.exe -m calyx.mcp_server.server --stdio
```

## Tools

- `calyx_scope`: reports authority posture, approved roots, and limits.
- `calyx_stat`: returns metadata for one scoped path.
- `calyx_list`: lists one scoped directory.
- `calyx_read_text`: reads approved text files with a bounded byte limit.
- `calyx_runtime_status`: reports existing Station runtime truth surfaces as advisory status.

## Sunrise

Station sunrise validates this support surface with:

```powershell
Scripts\start_calyx_mcp_stdio.ps1 -Validate
```

The stdio server remains client-launched. A detached resident stdio process is intentionally not started because it would have no client pipe and would not expose a useful MCP session.

## Receipts

Server start/stop, tool calls, resource reads, and errors emit receipts under:

`runtime\receipts\mcp`

These receipts make MCP usage observable without granting MCP independent authority.
