# Calyx Guardian

**Status:** Stub — governance plans reference these tools; full implementation pending.

Per `governance/plans/guardian_assessment_bundle.json` and `guardian_night_watch.json`.
BloomOS and Station Calyx use these for local owner confirmation and assessment flows.

## Scripts

| Script | Purpose |
|--------|---------|
| `local_owner_confirm.ps1` | Local owner confirmation flow; writes `approvals/<proposal_id>.local_owner.json` |
| `run_phase0_windows.ps1` | Phase 0 assessment (stub) |
| `guardian_watch_baseline.ps1` | Watch baseline (stub) |
| `guardian_watch_observer.ps1` | Watch observer (stub) |

## Render

| Script | Purpose |
|--------|---------|
| `render/guardian_manifest.py` | Generate manifest from evidence |
| `render/guardian_watch_analysis.py` | Watch analysis (stub) |
| `render/guardian_night_watch_brief.py` | Night watch brief (stub) |

## Tests

- `tests/test_smoke_phase0.py` — Smoke test (passes)

## Usage

```powershell
# Local owner confirmation (docs/local_owner_confirmation_quickstart.md)
pwsh -File tools\calyx_guardian\local_owner_confirm.ps1 -ProposalPath proposals\fw_context_preserving_enable_real.json
# Type: CONFIRM proposal_fw_context_preserve_enable_001_real ABCD1234
```
