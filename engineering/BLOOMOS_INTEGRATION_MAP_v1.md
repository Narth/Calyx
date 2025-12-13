# BloomOS Integration Map v1 (Descriptive, Non-Operational)

Components (conceptual):
- Kernel (reflection + boundary + safety)
- Seed/Seedbed pipeline (symbolic)
- Identity/Heartwood binder (threads + binder)
- Telemetry mirror (read-only)
- Safety harness (forbidden actions + sovereignty shield)
- Lifecycle controller (manual, seed→seedling only; conceptual)
- Vault/archive interface (append-only, seals)
- Read-only UI (status only)

Flows (descriptive):
- Identity/policy → safety harness → telemetry mirror → UI/vault.
- Advisory-only channels feed telemetry mirror; never trigger actions.
- Lifecycle controller gated by safety harness and manual approval.

All links are descriptive; no execution or runtime hooks; Safe Mode enforced; Architect primacy.***
