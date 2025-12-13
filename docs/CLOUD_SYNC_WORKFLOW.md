# Cloud Sync Workflow (Station Calyx)

Purpose: bounded-autonomy sync loop with human oversight, audit, and rollback for pushing to `origin/main`.

## Script entrypoint
- Script: `Automation/calyx_sync.ps1`
- Default config: `config/sync-config.example.json` (copy to `config/sync-config.json` and adjust)
- Run: `pwsh -File Automation/calyx_sync.ps1 -ConfigPath config/sync-config.json`

## Default guardrails
- Boundary check: if `allowedPaths` is set, only files matching those patterns sync.
- Critical gate: patterns in `criticalPatterns` stop automation until run with `-ForceAutoCommit` after human approval.
- Backup: changed files zipped to `local_backups/sync/pre-sync-<timestamp>.zip` before commit/push.
- Audit: append to `local_backups/audit/governance_audit.log` with timestamps.
- Push target: `origin/main` unless overridden.

## MCP / GitHub server integration hooks
- Use the GitHub MCP server in VS Code to:
  - Watch repo state (`git status`) and surface `governance_audit.log` in the MCP resource list.
  - Create PRs instead of direct pushes for critical changes (set `autoCommit:false` and `SkipPush`).
  - Open issues when boundary or critical blocks occur (message template in audit log).
  - Enforce branch protections on `main` and require reviews for `criticalPatterns`.
- Proposed MCP policy: run `calyx_sync.ps1` in dry-run mode hourly via MCP task runner; only allow `-ForceAutoCommit` after Narth approval recorded in MCP notes.

## Human oversight checkpoints
- Approval required when any file matches `criticalPatterns`.
- Review config changes with Narth before enabling scheduled runs.
- Periodically review `local_backups/audit/governance_audit.log` and clean old backups.

## Scheduling (Windows Task Scheduler)
1. Copy config example to `config/sync-config.json` and tune patterns/messages.
2. Create a basic task: trigger daily (default 02:00), action: `pwsh.exe -File "C:\Calyx_Terminal\Automation\calyx_sync.ps1" -ConfigPath "C:\Calyx_Terminal\config\sync-config.json"`.
3. Set “Stop the task if it runs longer than” 15 minutes; disallow “run on battery” for safety.
4. Keep `autoCommit:true` only for routine/non-critical paths; otherwise set `autoCommit:false` and rely on manual commit/PR.

## Failure modes & handling
- Boundary block: review file list, update `allowedPaths` if intentional, or move artifacts to `local_backups/`.
- Critical gate: obtain human approval, then re-run with `-ForceAutoCommit` or commit manually and open a PR.
- Push failure: rerun after network is restored; backups remain in `local_backups/sync`.

## Telemetry to monitor
- `local_backups/audit/governance_audit.log` for actions and reasons.
- Task Scheduler history for missed runs.
- Remote `origin/main` to confirm expected commits/PRs landed.
