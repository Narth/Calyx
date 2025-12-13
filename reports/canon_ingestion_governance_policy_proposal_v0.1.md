# Canon Ingestion Governance Policy Proposal v0.1

## Current State (logs/canon_ingestion_log.jsonl)
- Entries: 1
- Source: outgoing/cbo/cbo_addendum_v0.1_operationalizing_the_garden.md
- Classification: CBO governance translation
- Mode: Quiet Maintain reflection only
- Observed frequency/volume: ad hoc, single recorded ingestion

## Goals
- Every Canon ingestion is logged with provenance, intent, author, and mode.
- Distinguish Architect-authored Canon from agent-authored suggestions.
- Maintain append-only Canon history with traceable causality (Law 9), no hidden channels (Law 5), bounded autonomy (Law 2), and human primacy (Law 10).

## Proposed Canonical Ingestion Path & Ritual
1) Submission
   - Architect or agent submits Canon artifact to outgoing/user1/ (Architect) or outgoing/cbo/ (agent suggestion).
2) Classification & Intent
   - Required metadata: intent (append/update/annotate), uthor_role (architect|agent), mode (Quiet Maintain|Proposal), provenance (path, hash), 	rigger (manual|scheduled).
3) Logging
   - Use a single tool (e.g., 	ools/canon_ingestion_logger.py) to append an entry to logs/canon_ingestion_log.jsonl with the metadata above plus UTC timestamp.
4) Review & Deference
   - Agent-authored suggestions are marked mode=Proposal, uthor_role=agent; they are non-binding until Architect explicitly promotes them.
   - Architect promotions are logged as separate entries referencing the suggestion hash/path to preserve traceability.
5) Publication
   - Canon becomes “active” only when an Architect-authored (or cosigned) entry exists for that document/version. No autonomous activation.
6) Audit Hooks
   - Periodic (e.g., daily) report enumerates Canon ingestions, with counts by author_role and mode, flagging any unpromoted proposals older than a threshold.

## Alignment to Laws
- Law 2 (Bounded Autonomy): Agents cannot activate Canon; proposals require Architect promotion.
- Law 5 (No Hidden Channels): All ingestions go through the logger; no side-door edits.
- Law 9 (Traceable Causality): Entries include hashes/paths, intent, author_role, and trigger for auditability.
- Law 10 (Human Primacy): Architect promotion step is mandatory for activation.

## Open Questions
- Do we require cryptographic signatures for Architect promotions? (If yes, define signing key storage.)
- Should we enforce hash checking (SHA256) in the logger to detect post-log edits? (Recommended.)
- Retention policy for log: append-only with periodic archival? (Recommend retain+rotate.)
