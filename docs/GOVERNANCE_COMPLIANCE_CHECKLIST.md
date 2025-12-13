# Governance Compliance Checklist (Calyx Sync)

- Human primacy
  - Approval recorded for any `criticalPatterns` change.
  - Audit log updated for every automated action and block.
- Bounded autonomy
  - `allowedPaths` configured; automation stops on violations.
  - `autoCommit` disabled for sensitive paths unless explicitly approved.
- Transparency
  - Audit log location communicated (`local_backups/audit/governance_audit.log`).
  - Backups created before sync and retained per retention policy.
- Safety
  - Backups stored in `local_backups/sync`.
  - Push skipped on errors; no destructive commands run automatically.
- Oversight cadence
  - Daily review of audit log when automation is active.
  - Weekly verification of Task Scheduler job and backup integrity.
