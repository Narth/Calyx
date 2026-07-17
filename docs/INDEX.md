# Station Calyx Documentation

This index favors current human orientation over historical completeness. A document's presence does not grant runtime authority; status and classification remain explicit.

## Start here

1. [Project README](../README.md) — purpose, current status, safe first run, and repository map.
2. [AI-For-All Project](AI_FOR_ALL.md) — the human problem and public project orientation.
3. [Getting started](GETTING_STARTED.md) — validate a checkout and operate an intentionally configured Windows Station.
4. [Architecture](ARCHITECTURE.md) — current components, data flow, service topology, and limitations.
5. [Governance](../GOVERNANCE.md) — authority, decisions, and evidence language.
6. [Security policy](../SECURITY.md) — reporting, deployment boundary, and current limitations.

## Operate and inspect

- [Canonical operations index](operations/CANONICAL_OPS_INDEX.md)
- [Station operational doctrine](operations/STATION_CALYX_OPERATIONAL_DOCTRINE.md)
- [Station stack policy](STATION_STACK_POLICY.md)
- [Governed network gateway](gateway.md)
- [Local MCP server](canonical/CALYX_LOCAL_MCP_SERVER.md)
- [Interruption and recovery model](operations/STATION_INTERRUPTION_AND_RECOVERY_MODEL.md)

Runtime state and receipts are generated locally under `runtime/` and are not public documentation.

## Current authority and classification

- [Canonical System Map](canonical/CALYX_CANONICAL_SYSTEM_MAP.md)
- [Core Classification Registry](canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md)
- [Authority Resolution Registry](canonical/CALYX_AUTHORITY_RESOLUTION_REGISTRY.md)
- [Canonical Continuity Model](canonical/CALYX_CANONICAL_CONTINUITY_MODEL.md)
- [Source Authority Registry](canonical/CALYX_SOURCE_AUTHORITY_REGISTRY.json)
- [Decision Ledger](canonical/CALYX_DECISION_LEDGER.md)
- [Noncanonical Enforcement Registry](canonical/CALYX_NONCANONICAL_ENFORCEMENT_REGISTRY.md)

## Security and public-repository hygiene

- [Security policy](../SECURITY.md)
- [Security engineering notes](security.md)
- [Public repository denylist](public_repo_denylist.md)
- [Gateway boundary](gateway.md)
- [Disclosure Protocol](../governance/DP-1.md)
- [Privacy Boundary Schema](../governance/PBS-1.md)

## Development and contribution

- [Contributing](../CONTRIBUTING.md)
- [Support](../SUPPORT.md)
- [Code Factory deliverables](CODE_FACTORY_LOOP_DELIVERABLES.md)
- [Benchmark run operations](benchmarks/RUNOPS.md)
- [Project provenance](../PROVENANCE.md)

## Tracked source roots

These top-level directories remain part of the public source tree even when they are not part of the normal runtime path:

- `Scripts/` — Windows lifecycle, readiness, maintenance, and operator entry points.
- `cbo_hub/` — the current local HTTP service family.
- `calyx/` — governance-aware Python packages, service logic, contracts, and bounded tools.
- `tests/` and `tools/` — executable validation and repository utilities.
- `policy/` and `spec/` — active policy inputs and machine-readable protocol specifications.
- `rust/` — local-only advisory observers with no control or network authority.
- `ide_toolbox/` — developer editor configuration and installation helpers.
- `skills/` — integration wrappers whose presence does not make them canonical or authorized.
- `reports/` — dated findings and validation artifacts; consult each report's scope and date.
- `patches_out/` — historical or staged patch and runbook artifacts.
- `openclaw/` — quarantined external-integration material.
- `archive/` — non-operational historical code; active code must not import it.

## Design and research

The `docs/planning/`, `docs/governance/`, `proposals/`, `staging/`, and `bloomos/specs/` trees contain useful design and research material. Unless a current canonical document says otherwise:

- plans and proposals are not approvals;
- tests and fixtures are not running services;
- staged sources are not canonical components;
- BloomOS is specification-only;
- dated validation reports describe their own time and scope.

## Historical onboarding and narratives

Older onboarding guides, prompts, chronicles, and the compendium preserve project history and language. Many reference retired paths or conceptual roles. Begin with this index and the canonical maps before using an older command or capability claim.

## Foundational human declarations

The human-authored governance set is indexed at [governance/INDEX.md](../governance/INDEX.md). Those declarations retain their own wording, authority, and interpretation rules; this documentation index does not replace them.
