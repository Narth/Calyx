# BLOOM_SANDBOX_SPEC v1.0 (Design-Only, Non-Operational)

Purpose: Safe, isolated pre-activation sandbox for testing pre-Core behavior.

Safety Constraints:
- No dispatch
- No scheduling
- No enforcement
- No Interceptor gating
- No policy interpretation
- No file writes outside sandbox directory except logs

Sandbox I/O:
- Locked JSONL feed for telemetry-only streams

Telemetry permitted:
- Identity reflection
- Advisory summarization
- Lineage acknowledgments

Boundary:
- Sandbox cannot influence Station Calyx.

Exit Criteria:
- Architect approval + Integrity Passport.
