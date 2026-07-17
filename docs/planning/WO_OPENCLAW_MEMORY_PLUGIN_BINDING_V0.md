---
status: active
owner: station
last_reviewed_utc: "2026-03-23"
doctrine_scope: governed
---

# WO_OPENCLAW_MEMORY_PLUGIN_BINDING_V0

## Section I - Purpose and Scope

**Purpose**

- Establish governed binding rules for the OpenClaw memory plugin within Station Calyx.
- Ensure all memory indexing, retrieval, and reflection operations remain subordinate to Calyx memory authority.
- Prevent silent expansion of memory scope, implicit authority elevation, or indexing of unauthorized sources.

**Scope**

- Applies to all OpenClaw memory plugin configurations, indexing operations, and retrieval queries.
- Applies to all memory-source roots visible to OpenClaw agents.
- Applies regardless of whether memory access is local, cached, or externally derived.

This Work Order governs binding and authority only. It does not itself authorize indexing or execution.

## Section II - Core Rule

No OpenClaw memory operation may index, retrieve from, or reflect upon any source that is not explicitly defined, validated, and receipted as an approved Calyx memory-source root.

## Section III - Memory Authority Model

Memory authority remains exclusively under Station Calyx.

OpenClaw memory plugin is:

- a consumer of memory
- a reflector of memory
- not an authority over memory

OpenClaw must:

- treat all memory as read-only unless explicitly granted write authority
- not elevate derived or inferred memory into canonical memory
- not persist new memory without governed approval

Authority separation:

- Calyx Memory (canonical):
  - authoritative
  - receipted
  - governed

- OpenClaw Memory (derived):
  - non-authoritative
  - contextual
  - ephemeral unless promoted via governance

## Section IV - Approved Memory-Source Roots

All memory access must originate from explicitly declared roots.

Initial allowed root:

- `C:\Calyx_Terminal\memory`

Disallowed roots until explicitly approved:

- `C:\Users\*\.openclaw\workspace*\memory`
- inherited or legacy OpenClaw workspace paths
- any path not explicitly declared and receipted

Rules:

1. Missing roots must not be recreated implicitly.
2. Legacy paths must not be revived to satisfy plugin expectations.
3. Root expansion requires explicit operator declaration, receipt-backed approval, and reindex validation.

## Section V - Indexing Rules

Indexing must be:

- explicitly triggered
- bounded to approved roots
- receipted

Required indexing controls:

- index scope must be declared before execution
- index must not traverse outside approved roots
- index must not include hidden, system, or parent directories

Prohibited:

- recursive expansion beyond declared scope
- indexing of runtime, ledger, or system directories unless explicitly approved
- indexing of credential or secret-containing paths

## Section VI - Retrieval and Reflection Rules

OpenClaw may retrieve and reflect on memory only when:

- the source is within approved roots
- the query is traceable to indexed content
- the output clearly distinguishes retrieved facts from inferred conclusions

Reflection constraints:

- must not claim authority beyond source content
- must not fabricate memory continuity
- must not merge unrelated memory contexts into a single authoritative claim

## Section VII - Write and Promotion Rules

OpenClaw memory plugin must not:

- write to canonical memory
- modify existing memory files
- promote derived insights into memory

Allowed behavior:

- propose memory additions as suggestions
- output candidate memory artifacts for operator or governed approval

Promotion requires:

- explicit operator approval
- receipt creation
- validation of source and content integrity

## Section VIII - Failure and Drift Handling

The following conditions must result in hard deny:

- missing or invalid memory-source root
- attempt to access disallowed path
- attempt to index without declared scope
- attempt to write to canonical memory without authority

Required actions on violation:

- halt operation
- emit violation receipt
- record attempted path and action

Drift indicators:

- repeated access attempts to non-existent paths
- fallback to legacy OpenClaw directories
- silent reduction in indexed coverage

All drift must be surfaced, receipted, and not auto-corrected without governance.

## Section IX - Integration with Existing Work Orders

This Work Order extends and must remain consistent with:

- `WO_OPENCLAW_MEMORY_SOURCE_MAPPING_V0`
- Intent -> Mediation -> Execution enforcement
- Resource Authority enforcement
- Daily Lifecycle governance

Precedence rules:

- Memory authority must be validated during mediation before any memory-dependent action is allowed.
- Memory access is treated as a governed resource.

## Section X - Enforcement Language

1. OpenClaw memory plugin shall not access or index any path not explicitly approved as a memory-source root.
2. Memory authority remains with Station Calyx and shall not be delegated implicitly.
3. Derived memory shall not be treated as canonical memory.
4. All indexing operations shall be declared, bounded, and receipted.
5. Any attempt to access disallowed or missing memory paths shall result in hard deny and violation receipt.
6. Memory plugin behavior shall not expand scope to satisfy internal assumptions or missing dependencies.
7. Memory access shall remain traceable, auditable, and attributable to approved sources.

## Section XI - Operator Principle Statement

Memory is not what can be reached, but what is authorized.

Station Calyx governs what is remembered, how it is accessed, and what may become truth. OpenClaw may reflect on memory, but it may not define it. No system may expand memory authority to compensate for absence, assumption, or convenience.
