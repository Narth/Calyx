# Rollback Procedures (Calyx Sync)

## Quick revert (recent sync)
1. Locate most recent backup in `local_backups/sync/pre-sync-*.zip`.
2. Extract the archive to a temporary directory.
3. Copy restored files back into the repo, review with `git status`.
4. Commit with message `revert: restore from pre-sync backup <timestamp>` and push or open a PR.

## Git-based rollback
- To undo last sync commit locally: `git revert HEAD` (opens editor for message).
- To rewind multiple commits safely: create a branch, use `git revert <range>`, then open a PR for review.

## Remote safety
- Avoid `git reset --hard` on `main`; prefer revert plus PR to preserve auditability.
- If a bad push reached `main`, coordinate with Narth before force-pushing.

## Backup verification
- Periodically open a recent `pre-sync-*.zip` and confirm files are readable.
- Keep at least the last 5 archives; prune older ones to control disk usage.
