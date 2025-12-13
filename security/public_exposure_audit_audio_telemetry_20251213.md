# Public Exposure Audit (Audio/Telemetry) — 2025-12-13

Scope: Cloud-based auditory review of Station Calyx to surface assets that should not remain on a public platform.

## Flagged for deletion

| Path / Pattern | Issue | Risk | Recommendation |
| --- | --- | --- | --- |
| `samples/wake_word/positive/*.wav` | Contains recorded wake-word utterances (human voice captures). | Personal audio data is public; potential privacy and consent concerns. | Remove from public repo; relocate to private storage or replace with synthetic samples. |
| `samples/wake_word/negative/*.wav` | Contains recorded negative/near-miss audio (human voice/background). | Personal audio data is public; potential privacy and consent concerns. | Remove from public repo; relocate to private storage or replace with synthetic samples. |
| `logs/investigative_log.md` | Operational timeline with system telemetry and governance notes. | Leaks host activity details and internal governance cadence. | Delete from repo and keep only in private operational logs. |
| `logs/canon_ingestion_log.jsonl` | Ingestion history with timestamps and classification notes. | Reveals internal document handling and timing metadata. | Delete from repo; regenerate privately if needed. |
| `logs/overseer_loop_trace.jsonl` | Daemon trace with timestamps and run/skip decisions. | Exposes internal loop behavior and timing signals. | Delete from repo; capture traces privately when debugging. |

Architect approval recommended before purging; no production code paths depend on these artifacts.
