---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# OpenClaw Decommission Playbook

**WO_OPENCLAW_DECOMMISSION_GATING_V2** — Canonical disable steps. Goal: **provably inert**.

**Historical note:** OpenClaw helped bring Station Calyx to fruition. It is remembered. This playbook gates it; we do not erase it. Significant work remains before testing can be considered again.

---

## Prerequisites

- Run as Administrator for services/tasks
- Stop Calyx CBO and Discord gateway first (optional; gate will fail-closed if OpenClaw detected)

---

## Step 1 — Stop Services

```powershell
Get-Service | Where-Object { $_.Name -like '*openclaw*' } | Stop-Service -Force
```

---

## Step 2 — Disable Services

```powershell
Get-Service | Where-Object { $_.Name -like '*openclaw*' } | Set-Service -StartupType Disabled
```

---

## Step 3 — Disable Scheduled Tasks

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like '*openclaw*' } | Disable-ScheduledTask
```

*Disabled tasks are inert; the gate does not flag them.*

---

## Step 4 — Stop Processes

```powershell
Get-Process | Where-Object { $_.Path -like '*openclaw*' -or $_.ProcessName -like '*openclaw*' } | Stop-Process -Force
```

---

## Step 5 — Confirm No Processes Remain

```powershell
Get-Process | Where-Object { $_.Path -like '*openclaw*' -or $_.ProcessName -like '*openclaw*' }
# Expected: no output
```

---

## Step 6 — Confirm No Port 18789

```powershell
netstat -ano | findstr 18789
# Expected: no output (or only TIME_WAIT)
```

---

## Step 7 — Verify Gate Passes

```powershell
python -m calyx.kernel.external_emitter_gate
# Expected: "No OpenClaw detected." exit 0
```

---

## Step 8 — Start Calyx

```powershell
.\Scripts\start_calyx_core_services.ps1
# CBO preflight will pass; no fail-closed
```

---

## Quarantine Option (if full removal not immediate)

1. Move `C:\Calyx_Terminal\.openclaw` to a path **outside** the workspace (e.g. `C:\quarantine\openclaw_backup`)
2. Ensure no OpenClaw processes/services/tasks run
3. Calyx runtime refuses to run if OpenClaw detected (preflight gate)

---

## Config Override (Migration Only)

**Temporary** — use only during migration; remove after decommission:

```powershell
$env:ALLOW_OPENCLAW_FOR_MIGRATION = "true"
# Bypasses gate; NOT for production
```
