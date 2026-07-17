# Calyx Sign — CBO Sponsorship for Stamping Calyx Operations

**Purpose:** Define how the Architect can sponsor CBO via Calyx Sign so CBO may begin stamping Calyx operations, with a clear line of communication when a decision truly requires human input. Authority remains with the Architect; CBO acts within sponsored scope and escalates when needed.

**Status:** Policy. Implementation of stamping gates (e.g. in CBO Core or tool loop) is separate; this doc defines the contract and escalation rule.

---

## Sponsorship

You (the Architect) may sponsor CBO via **Calyx Sign** to begin **stamping** Calyx operations. Sponsorship is an Architect-signed policy (per `governance/contracts/architect_approval.md`) that:

- Grants CBO limited authority to approve (“stamp”) a defined set of operations that are currently listed under “Forbidden (until Calyx Sign)” in STATE.md.
- Does **not** allow CBO to generate Architect signatures or to substitute automated inference for human approval. It delegates *bounded* stamping within scope.

So: you sign once (the sponsorship policy); CBO may then stamp operations that fall inside that scope, subject to the escalation rule below.

---

## Stamping

**Stamping** means CBO records that an operation is approved under the sponsored scope and (where implemented) execution may proceed. For example:

- File writes in allowlisted paths.
- Running allowlisted scripts (e.g. `Scripts\update_state_checks.ps1`, `Scripts\start_calyx_core_services.ps1` with agreed parameters).
- Other operations explicitly listed in the sponsorship policy.

The exact scope (paths, script allowlist, conditions) belongs in the sponsorship artifact or an attached appendix. CBO stamps only when the operation is within scope and CBO has no duty to escalate (see below).

---

## Clear line of communication — when CBO must ask you

When a decision **truly requires your input or context**, CBO must **not** stamp or execute. CBO must:

1. **Ask you** in the current channel (Chat, Discord, CLI, or wherever the conversation is).
2. **State what is needed:** the operation, why it needs your input, and what would be required to proceed (e.g. “Approve this path for write,” “Confirm spend above X,” “Choose A or B”).
3. **Wait** for an explicit response from you (approve, deny, or provide context) before proceeding.

So: **within sponsored scope and without need for your context, CBO may stamp. Outside scope or when in doubt, CBO escalates and pauses.**

CBO must not infer approval from silence or ambiguity. Absence of a clear response is treated as “do not proceed” until you reply.

---

## Escalation channels

CBO will use the same channel you are using to talk to CBO:

- **Discord** — reply in the same thread or DM.
- **Avatar Web (Chat)** — reply in the chat.
- **CLI Avatar** — reply in the terminal session.
- **Whiteboard / other** — reply in the appropriate place or in Chat/Discord if that is the primary link.

If you want a dedicated “approval queue” (e.g. a file or a Discord channel) for CBO to post requests and you to respond, that can be added to the sponsorship or a follow-on policy.

---

## Revocation

Sponsorship can be rescinded deterministically:

1. **Architect revokes:** You state in the same channel (or a signed revocation note in `governance/approvals/`) that the sponsorship for proposal ID `cbo_sponsorship_research_test_improve` (or the active sponsorship) is rescinded. CBO and tooling treat that as immediate: no further stamping under that policy.
2. **Operational rollback:** STATE.md reverts to “Forbidden (until Calyx Sign)” for operations that were allowed under sponsorship. Any stamping gates that reference the sponsorship artifact should treat absence or invalidation of that artifact as denial.
3. **No automated rollback of past actions:** Revocation does not undo past stamped operations; it stops future stamping under that scope. Rollback of specific changes (e.g. file restores) is a separate, explicit action.

Authority that can be revoked remains governance; revocation is documented here.

---

## Relation to existing governance

- **Architect Approval Contract** (`governance/contracts/architect_approval.md`): The Architect remains the sole human root authority. No agent may generate Architect signatures. Sponsorship is you signing a *policy* that delegates limited stamping authority to CBO; it is not CBO signing for you.
- **STATE.md — “Forbidden (until Calyx Sign)”:** Once you have signed a Calyx Sign sponsorship that allows specific operations, those operations move from “Forbidden” to “Allowed under sponsorship” (scope as defined in the sponsorship). STATE.md or a runbook can reference this doc and the sponsorship artifact.

---

## Next steps

1. **You:** Draft (or have CBO draft for your review) a **sponsorship policy** that defines: (a) scope of operations CBO may stamp, (b) any hard limits (e.g. no destructive deletes, no docker unless explicitly listed), (c) that CBO must escalate when human input is required.
2. **You:** Sign the sponsorship per Architect Approval Contract (proposal artifact, approval receipt, your cryptographic signature).
3. **Station:** Implement or configure stamping gates so CBO’s “stamp” is checked where needed (e.g. before file write or script run). Until then, “stamping” is a documented intent and CBO’s behavior (escalate when in doubt) applies in conversation.

You can sponsor CBO via Calyx Sign to begin stamping Calyx operations, with a clear line of communication: when a decision truly requires your input, CBO asks you and waits.
