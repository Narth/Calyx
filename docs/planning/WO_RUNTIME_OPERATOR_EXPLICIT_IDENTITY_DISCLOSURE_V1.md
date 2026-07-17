---
status: active
owner: station
last_reviewed_utc: "2026-04-15"
doctrine_scope: governed
---

# WO_RUNTIME_OPERATOR_EXPLICIT_IDENTITY_DISCLOSURE_V1

## Section I - Purpose And Scope

### Purpose

Upgrade Station runtime truth from classification-only disclosure to operator-explicit runtime identity disclosure.

This work order exists so the operator can distinguish, in plain terms:

- what is running on the machine
- what exact OS process evidence supports that conclusion
- how Station governance interprets that process
- whether the process is canonical, auxiliary, external, or uncertain

The goal is not to promote every observed runtime into Station authority.

The goal is to prevent operator-facing truth surfaces from hiding behind broad labels when exact identity is available from observable machine facts.

### Scope

This work order governs:

- operator-facing runtime identity disclosure
- separation of machine facts from governance interpretation
- identity matching based on executable path, command line, parentage, ports, config linkage, and launch provenance
- explicit naming of known external or station-adjacent runtimes when evidence supports that naming
- receipt-backed runtime identity snapshots

This work order applies to:

- governed Station services
- Station wrappers and helpers
- station-adjacent dependencies
- external runtimes visible on the same machine where evidence materially intersects Station operation

This work order does not:

- grant authority to external runtimes
- authorize process termination
- authorize restart or launch mutation
- authorize silent inference beyond observable evidence
- collapse uncertain identity into confident naming

## Section II - Problem Statement

Current runtime topology work improved classification and multiplicity visibility, but classification labels alone are not sufficient operator truth.

Labels such as:

- `auxiliary_family`
- `launcher_wrapper`
- `runtime_supervisor`
- `effective_service_runtime`

may help governance reasoning, but they do not fully answer the operator question:

`what exact thing is running on this machine right now?`

When machine evidence supports explicit identification, the Station must disclose that identity plainly.

Examples of acceptable plain disclosure:

- `OpenClaw is running`
- `this node.exe process appears to belong to OpenClaw`
- `this process is station-governed`
- `this process is external and non-authoritative`
- `this dependency is present but outside canonical control`

Examples of unacceptable operator truth:

- broad family labels when a concrete identity is available
- implicit certainty where evidence is weak
- treating external but known processes as unnamed background noise

## Section III - Core Principle

Operator truth surfaces must separate three layers without collapsing them:

### A. Observed Machine Facts

What the operating system directly reveals.

### B. Governance Interpretation

How Station classifies and governs the observed process.

### C. Identity Disclosure

What the process most likely is, named plainly when evidence supports that naming.

These layers must be shown together, but they must not be conflated.

Machine facts are not governance.
Governance is not identity.
Identity is not authority.

## Section IV - Required Disclosure Model

Every operator-facing runtime disclosure surface must distinguish:

### 1. Observed Machine Facts

Required fields where available:

- `pid`
- `ppid`
- `process_name`
- `executable_path`
- `command_line`
- `parent_process_name`
- `parent_executable_path`
- `start_time`
- `ports`

These fields are direct evidence, not interpretation.

### 2. Governance Interpretation

Required fields:

- `service_family`
- `runtime_class`
- `authority_posture`
- `declared_status`
- `authoritative_runtime`
- `canonical_status`
- `multiplicity_state`
- `risk_level`

These fields describe how Station interprets the process under governance rules.

### 3. Identity Disclosure

Required fields:

- `matched_identity`
- `identity_type`
- `identity_basis`
- `identity_confidence`
- `station_relationship`

Allowed `identity_type` examples:

- `station_service`
- `station_wrapper`
- `station_auxiliary`
- `station_dependency`
- `external_known_system`
- `external_unknown`
- `uncertain`

Allowed `station_relationship` examples:

- `station_governed`
- `station_adjacent_non_authoritative`
- `external_non_authoritative`
- `unknown_relationship`

## Section V - Plain-Naming Rule

If a runtime can be explicitly identified from observable evidence, the Station must name it plainly.

Permitted evidence bases include:

- executable path
- command line
- parent-child lineage
- owned ports
- config linkage
- known launch provenance
- governed receipt linkage

Hard rules:

- if identity is supported, announce it plainly
- if identity is uncertain, say `uncertain`
- if a process is external but known, still name it
- if a process is non-authoritative, disclose that separately rather than omitting identity

Forbidden shortcuts:

- substituting a family label for a known identity
- presenting inferred identity as certain without basis
- suppressing explicit identity because the process is external

## Section VI - Identity Matching Requirements

The runtime identity engine must attempt explicit matching using deterministic evidence in priority order.

### Priority 1 - Exact Governed Provenance

Match from:

- known Station launch scripts
- governed service registry
- runtime receipts
- launch notice or topology receipts

### Priority 2 - Exact Executable Or Script Linkage

Match from:

- script path
- module path
- executable path
- command-line token signatures

### Priority 3 - Port And Transport Linkage

Match from:

- canonical service ports
- known transport ownership
- listener or active connection signatures

### Priority 4 - Config And Dependency Linkage

Match from:

- known config files
- environment linkage
- working directory
- declared dependency ownership

### Priority 5 - Heuristic But Evidence-Bounded Matching

Allowed only when stronger evidence is absent.

Heuristic matching must:

- record exact basis
- mark confidence conservatively
- avoid canonical claims without sufficient support

## Section VII - Confidence And Disclosure Rules

Every explicit identity decision must carry confidence and basis.

Required confidence values:

- `high`
- `medium`
- `low`

Meaning:

### `high`

Identity is supported by direct script, executable, receipt, or port ownership evidence with little ambiguity.

### `medium`

Identity is supported by multiple consistent signals, but there is still some ambiguity.

### `low`

Identity is a bounded inference from partial evidence and must be shown as tentative.

Hard rule:

No process may be disclosed as a canonical known identity without either:

- high confidence, or
- explicit wording that it only `appears to belong to` the matched system

## Section VIII - Required Operator Surfaces

### A. Structured Runtime Identity Surface

The runtime topology snapshot must gain an operator-explicit process table or equivalent structure.

Required columns:

- `pid`
- `process_name`
- `executable_path`
- `command_line`
- `parent_pid`
- `ports`
- `matched_identity`
- `identity_confidence`
- `family`
- `authority_posture`
- `declared_status`
- `risk_level`

Recommended additional fields:

- `ppid`
- `parent_process_name`
- `identity_basis`
- `runtime_class`
- `canonical_status`
- `station_relationship`

### B. Human-Readable Operator Summary

`STATE.md` or a linked operator-facing surface must summarize:

- named active Station services
- named external or station-adjacent systems relevant to Station operation
- explicit unknown or uncertain runtimes
- authoritative versus non-authoritative process count
- high-risk ambiguous identities

### C. Full Snapshot Artifact

The full disclosure artifact should preserve all direct machine facts, not only summarized labels.

## Section IX - Required Output Artifacts

This work order authorizes planning and staging for artifacts such as:

- `runtime/runtime_topology_snapshot.json`
- `runtime/runtime_identity_snapshot.json`
- `runtime/receipts/audit/runtime_identity_snapshot__YYYYMMDD_HHMMSS.json`

If the implementation keeps a single canonical snapshot instead of a second file, that is acceptable only if the single file preserves:

- machine facts
- governance interpretation
- identity disclosure

without collapsing those categories together.

## Section X - Classification And Authority Posture Separation

Identity disclosure must not weaken governance boundaries.

Required distinction examples:

- `matched_identity = OpenClaw`
- `station_relationship = external_non_authoritative`
- `authority_posture = non_canonical`

or:

- `matched_identity = Discord Gateway`
- `station_relationship = station_governed`
- `authority_posture = authoritative`

or:

- `matched_identity = uncertain`
- `station_relationship = unknown_relationship`
- `authority_posture = indeterminate`

Hard rule:

Naming a process is not the same as legitimizing it.

## Section XI - Risk Signaling

Identity disclosure must strengthen risk signaling, not dilute it.

Required risk escalation examples:

### `LOW`

- identity known
- authority posture clear
- declared status compliant

### `ELEVATED`

- identity known but role boundary is non-canonical, auxiliary, or borderline

### `RISK`

- identity uncertain for a station-adjacent runtime
- declared status missing
- authority posture ambiguous

### `CRITICAL`

- multiple authoritative candidates
- duplicate listener conflict
- explicit identity evidence conflicts with governance interpretation

## Section XII - Staging Plan

### Phase 0 - Schema Definition

Define the machine-fact, governance, and identity-disclosure field model.

### Phase 1 - Observed Fact Expansion

Ensure process snapshots preserve:

- executable path
- command line
- parent process facts
- ports

### Phase 2 - Identity Matcher

Implement bounded explicit matching against:

- Station services
- wrappers
- helpers
- known dependencies
- known external systems relevant to Station operation

### Phase 3 - Operator Surface Upgrade

Expose an operator-facing runtime table and summary that plainly names matched identities where supported.

### Phase 4 - Receipt Integration

Emit receipt-backed identity snapshots, including confidence and basis.

### Phase 5 - Validation

Add tests covering:

- exact Station service identification
- external known-system identification
- uncertain identity handling
- non-authoritative external disclosure
- disagreement between machine facts and governance interpretation

## Section XIII - Success Criteria

This work order is successful when the operator can answer, without euphemism:

- what exact processes are running
- what each process appears to be
- which processes are Station-governed
- which are external but relevant
- which are canonical versus non-authoritative
- which identities remain uncertain

This work order is not successful if operator truth still depends on broad family labels where exact evidence exists.

## Section XIV - Non-Goals

This work order does not authorize:

- process killing
- automatic cleanup
- authority expansion for named external runtimes
- hiding uncertainty behind overconfident naming
- treating external dependencies as canonical merely because they are recognized

## Section XV - Follow-On Relationship

This work order is complementary to:

- `WO_RUNTIME_TOPOLOGY_LABELING_V1`
- `WO_RUNTIME_MULTIPLICITY_DECLARATION_AND_LAUNCH_NOTICE_V1`
- `WO_RUNTIME_MULTIPLICITY_ENFORCEMENT_AND_VALIDATION_V1`
- `WO_RUNTIME_SINGLETON_AND_RECONCILIATION_ENFORCEMENT_V1`

Those work orders establish topology, multiplicity, and reconciliation posture.

This work order adds:

- explicit runtime naming
- direct machine-fact disclosure
- separation of identity from authority
- operator-readable truth that does not hide behind abstraction

## Section XVI - Intent Confirmation

Station Calyx should be able to say what is running on the machine in plain language when the evidence supports it.

It should also be able to say:

- this is known
- this is external
- this is non-authoritative
- this is uncertain

That is stronger operator truth than broad classification alone.
