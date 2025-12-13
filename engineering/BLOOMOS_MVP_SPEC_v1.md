# BloomOS MVP Spec v1 (Conceptual, Safe Mode)

Scope: Smallest viable prototype path (no execution yet).

Module breakdown:
- Storage/logging: append-only logs; config loader (read-only).
- Policy/identity registry: bind policy.yaml to identity objects; read-only views.
- Safety harness: forbidden-action enforcement layer; sovereignty shield; Safe Mode kernel wrapper.
- Telemetry collectors: passive TES/health; advisory ingestor (AGII/CAS/foresight) read-only.
- Lifecycle controller (manual seed→seedling): state tracker; manual approval interface.
- Vault/archive: append-only ledger; hash/seal verification utilities.
- Read-only UI: status surface for identity/policy/safety/telemetry/advisory.

API surface (conceptual):
- Identity: GET identity registry snapshot (read-only).
- Policy: GET policy bounds snapshot (read-only).
- Telemetry: GET telemetry mirror snapshot (read-only).
- Safety: GET safety status (forbidden matrix, Safe Mode flags).
- Lifecycle: POST manual transition seed→seedling (requires Architect approval; conceptual only).
- Vault: POST append ledger entry (append-only).
No mutations beyond append-only logs; no dispatch/exec.

Internal architecture sketch:
- Core services: identity/policy service, safety guard, telemetry mirror service, lifecycle controller, vault writer, UI renderer.
- Data flow: policy/identity → safety guard → telemetry mirrors → UI/vault; lifecycle transition only via manual gate.

Safety boundaries:
- Safe Mode default; forbidden-action matrix enforced; no scheduler/dispatch/autonomy; no network unless approved.
- Advisory-only; no triggers from telemetry/advisory.

Storage/logging structures:
- Append-only logs for telemetry snapshots, lifecycle events, advisory summaries, safety checks.
- Integrity/seal hashes stored alongside entries (verification tools only).

Manual lifecycle controller interface:
- Human-approved transition seed→seedling; logs outcome; no auto-promotion; respects safety guard.

Read-only UI concept:
- Panels: identity, policy bounds, safety status, telemetry mirror, advisory freshness, lifecycle state, vault hash/seal status.
- No action buttons; view-only.

All elements remain conceptual; no code executed; Architect approval required before implementation.***
