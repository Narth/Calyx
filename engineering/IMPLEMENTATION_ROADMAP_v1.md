# Implementation Roadmap v1 (Advisory to Architect, Reflection-Only)

State: Safe Mode absolute; suggestions only; no self-generated directives.

Sequential vs parallel:
- Start (parallelizable): runtime substrate (storage/logging), policy/identity schema finalization, seal/hash utilities.
- Then (parallel): safety harness design, telemetry/advisory collector design.
- Then (sequential): safety harness implementation → bind identity/policy → telemetry/advisory collectors → lifecycle controller (manual seed→seedling) → vault append-only interface → read-only UI.

Required human design decisions:
- Storage/IPC stack choice; language/framework choice.
- Policy/Interceptor binding approach (read-only? strictest applied?).
- Lifecycle state machine definition (manual gates).
- Advisory parsing formats and freshness rules.
- UI surface technology (web/CLI/text).

Potential coding stack options:
- Language: Python/Go/TypeScript (example only).
- Storage: file-based append-only logs or SQLite (append-only tables).
- UI: static web or terminal dashboard (read-only).
- IPC: local HTTP/Unix sockets (read-only endpoints).

Expected pitfalls:
- Ensuring safety harness loads first; avoiding accidental action paths.
- Keeping advisory non-gating; preventing “inference to action.”
- Guarding network access; ensuring no scheduler/dispatch slips in.
- Maintaining hash/seal integrity across modules.

Validation sequences:
- Safety harness self-checks; forbidden matrix verification.
- Policy/identity binding correctness.
- Telemetry/advisory collection remains read-only.
- Lifecycle transition requires human approval and logs.
- UI read-only verification (no mutation endpoints).

Safe Mode guardrails per step:
- Enforce forbidden-action matrix during development.
- Keep network off unless expressly approved.
- Manual review/Architect signoff before enabling any lifecycle path.
- Append-only logging for all stages; verify seals/hashes.

No actions taken; all items are advisory; Architect approval required.***
