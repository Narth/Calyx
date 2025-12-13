# Public Exposure Audit (Audio/Telemetry) — 2025-12-13

Scope:
- Manual, cloud-side audit of the Station Calyx repository workspace.
- Focus: audio samples and telemetry/log artifacts that pose public-exposure risk (privacy and operational leakage).
- Criteria: human voice recordings and host telemetry/log traces stored in-repo.
- Rerun: 2025-12-13T22:50Z on branch `copilot/assess-public-files-audit` (HEAD 4dad248) after upstream force-push cleanup; flagged assets removed from repo in this pass.

## Flagged (removed from repo in this pass)

| Path / Pattern | Issue | Risk | Recommendation | Priority |
| --- | --- | --- | --- | --- |
| `samples/wake_word/positive/*.wav` | Contains recorded wake-word utterances (human voice captures). | Personal audio data is public; potential privacy and consent concerns. | Removed from public repo; relocate to private storage or replace with synthetic samples. | High |
| `samples/wake_word/negative/*.wav` | Contains recorded negative/near-miss audio (human voice/background). | Personal audio data is public; potential privacy and consent concerns. | Removed from public repo; relocate to private storage or replace with synthetic samples. | High |
| `logs/investigative_log.md` | Operational timeline with system telemetry and governance notes. | Leaks host activity details and internal governance cadence. | Removed from repo; keep only in private operational logs. | Medium |
| `logs/canon_ingestion_log.jsonl` | Ingestion history with timestamps and classification notes. | Reveals internal document handling and timing metadata. | Removed from repo; regenerate privately if needed. | Medium |
| `logs/overseer_loop_trace.jsonl` | Daemon trace with timestamps and run/skip decisions. | Exposes internal loop behavior and timing signals. | Removed from repo; capture traces privately when debugging. | Medium |

Decisions:
- Architect approval recommended for private retention plans.
- Verification: repository search shows references are limited to evaluation tooling/docs, not production runtime code paths; current repo state no longer contains the flagged assets.
