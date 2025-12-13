# Public Exposure Audit (Audio/Telemetry) — 2025-12-13

Scope: Manual, cloud-side audit of the Station Calyx repository workspace focusing on audio samples and telemetry/log artifacts for public-exposure risk (privacy and operational leakage). Criteria: human voice recordings and host telemetry/log traces stored in-repo.

## Flagged for deletion

| Path / Pattern | Issue | Risk | Recommendation | Priority |
| --- | --- | --- | --- | --- |
| `samples/wake_word/positive/*.wav` | Contains recorded wake-word utterances (human voice captures). | Personal audio data is public; potential privacy and consent concerns. | Remove from public repo; relocate to private storage or replace with synthetic samples. | High |
| `samples/wake_word/negative/*.wav` | Contains recorded negative/near-miss audio (human voice/background). | Personal audio data is public; potential privacy and consent concerns. | Remove from public repo; relocate to private storage or replace with synthetic samples. | High |
| `logs/investigative_log.md` | Operational timeline with system telemetry and governance notes. | Leaks host activity details and internal governance cadence. | Delete from repo and keep only in private operational logs. | Medium |
| `logs/canon_ingestion_log.jsonl` | Ingestion history with timestamps and classification notes. | Reveals internal document handling and timing metadata. | Delete from repo; regenerate privately if needed. | Medium |
| `logs/overseer_loop_trace.jsonl` | Daemon trace with timestamps and run/skip decisions. | Exposes internal loop behavior and timing signals. | Delete from repo; capture traces privately when debugging. | Medium |

Architect approval recommended before purging; verified via repository search that references are limited to evaluation tooling/docs, not production runtime code paths.
