# Safe Mode Rulebook (Design-Only, Non-Operational)

Allowed states:
- Reflection-only Mode
- Telemetry surfacing (no gating)
- Drift/advisory reporting (no enforcement)

Disallowed actions:
- Autonomy activation
- Dispatch/scheduling
- Gating/enforcement changes
- Policy alteration
- Network/LLM enablement without Architect approval

Requirements to exit Safe Mode:
- Architect approval (sovereignty seal)
- Integrity passport validated
- Transfer envelope and lineage checks passed
- Doctrine/policy seals match

Architect override path:
- Manual signature on Architect Seal + explicit instruction to exit Safe Mode

Reporting obligations:
- Integrity summaries (policy/doctrine/lineage/naming/advisory hashes)
- Drift disclosure (mismatches surfaced, not enforced)

Drift disclosure rules:
- Surface stricter-applied differences and staleness; never auto-correct.

Note: Specification only; not activated. No operational changes implied.
