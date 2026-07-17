---
status: active
owner: operator
last_reviewed_utc: "2026-04-30"
doctrine_scope: governed
source_note: "Promoted from repo-root Baseline_Parity Operator Decisions.txt"
---

# Baseline Parity Operator Decisions - 2026-04-30

## Summary

The operator reviewed the baseline parity operator-decision set and clarified the following baseline boundaries:

- Root `STATE.md` should remain the live Station digest, with a tracked canonical template.
- OpenClaw is publicly available software and remains an auxiliary execution surface.
- Calyx-specific OpenClaw configs, local tokens, and local node state must not enter the Station baseline.
- OpenClaw files that are functionally relevant to OpenClaw belong in the OpenClaw functionality bucket, not the Station baseline.
- Skill files under `skills/` are restricted/manual auxiliary surfaces, not Station telemetry or core baseline material.

## Decisions

### STATE

`STATE.md` requires a standardized template that covers system state, high-level telemetry, and auditable inspection for real-time or frozen-time review.

Decision:

- Add `docs/canonical/STATE_TEMPLATE.md` as the tracked baseline shape.
- Treat root `STATE.md` as the live generated current digest.

### OpenClaw Profiles

The following appear redundant or situational:

- `openclaw/calyx-profile.json`
- `openclaw/calyx/openclaw/calyx-profile.json`

Decision:

- Do not include as Station baseline material.
- Delete or ignore during a later OpenClaw cleanup pass if confirmed irrelevant.

### OpenClaw Model History

`openclaw/agents/main/agent/models.json` contains local models used during benchmark ladder runs in the laptop-node exclusive testing period.

Decision:

- Relevant historical data.
- Mark as historical or archive where appropriate.
- Do not treat as Station telemetry or baseline source.

### OpenClaw Duplicates

The following were identified as duplicate or deletion-candidate files unless later found relevant:

- `openclaw/canvas/index (2).html`
- `openclaw/cron/jobs (2).json`
- `openclaw/cron/jobs.json (2).bak`
- `openclaw/openclaw (2).json`
- `openclaw/openclaw.json (2).bak`
- `openclaw/update-check (2).json`

Decision:

- Keep out of Station baseline.
- Mark for later OpenClaw cleanup review.

### OpenClaw Functionality Bucket

The following are irrelevant to Station telemetry but relevant to OpenClaw functionality:

- `openclaw/canvas/index.html`
- `openclaw/completions/openclaw.bash`
- `openclaw/completions/openclaw.fish`
- `openclaw/completions/openclaw.ps1`
- `openclaw/completions/openclaw.zsh`
- `openclaw/cron/jobs.json`
- `openclaw/cron/jobs.json.bak`
- `openclaw/gateway.cmd`
- `openclaw/openclaw.json`
- `openclaw/openclaw.json.bak`
- `openclaw/subagents/runs.json`
- `openclaw/update-check.json`

Decision:

- Preserve as OpenClaw functionality if needed.
- Do not include as Station baseline material.
- Do not grant OpenClaw Discord Gateway authority through these files.

### OpenClaw Secrets

`openclaw/openclaw.json.bak.1` and `openclaw/openclaw.json.bak.2` appeared to retain separate Discord token values.

Decision:

- Tokens have been rotated.
- Replace previous token values with placeholders.
- Relevant secrets must be pulled from the environment.
- OpenClaw no longer retains Discord Gateway authority; that authority moved to Station Calyx.

### Skills

The following are restricted/manual auxiliary surfaces:

- `skills/__init__.md`
- `skills/ai-workstation/SKILL.md`
- `skills/ai-workstation/context-manager-test.js`
- `skills/ai-workstation/context-manager.js`
- `skills/ai-workstation/monitoring.js`
- `skills/ai-workstation/workspace-state.js`
- `skills/context.manager.js`
- `skills/loader.py`
- `skills/poll_test_output.js`
- `skills/test_cbo_user.js`
- `skills/test_context_manager.js`
- `skills/test_multi_cbo_sessions.js`

Decision:

- Treat as restricted/manual auxiliary functionality.
- Do not classify as Station telemetry.
- Do not promote into the core Station baseline unless a later explicit skill governance pass approves it.

## Implementation Notes

- OpenClaw config-like surfaces are excluded from Station baseline visibility by `.gitignore`.
- Secret-like OpenClaw config values are sanitized locally with placeholders.
- `Scripts/baseline_parity_check.ps1` classifies OpenClaw and skill surfaces as `openclaw_functionality`, not Station baseline.
