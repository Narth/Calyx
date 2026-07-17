# Governance

This is a public orientation to how Station Calyx decisions are made. It does not replace the human-authored declarations in [`governance/`](governance/) or the operational charter in [`AGENTS.md`](AGENTS.md).

## Authority

Authority originates with the human operator.

- Maintainers decide what enters the public repository and what becomes part of the canonical Station path.
- CBO and other AI collaborators may analyze, propose, implement within delegated scope, test, and dissent.
- AI collaborators do not grant themselves permission, expand their own authority, or convert a proposal into governance.
- Contributors grant no runtime authority merely by adding code or documentation.

## The project distinguishes kinds of claims

Station work should keep these categories separate:

- **Observation:** directly seen in code, runtime state, or external evidence.
- **Inference:** a conclusion drawn from observations.
- **Proposal:** a suggested future change.
- **Approval:** explicit human authorization for a bounded action.
- **Execution:** an action that actually occurred.
- **Receipt:** evidence that a defined process recorded a result.
- **Canonical claim:** a status supported by the current authority and classification maps.

Good intent, polished prose, a passing test, and a running process are useful evidence for different questions. None is a universal substitute for the others.

## Change posture

The default engineering posture is:

1. Make the smallest useful change.
2. Keep it observable and reversible.
3. Increase friction with consequence.
4. Deny when required evidence is missing or malformed.
5. Record exceptions rather than silently weakening policy.
6. Restart affected services so runtime code matches source code.

Public pull requests should explain scope, authority/network effects, validation, privacy impact, and rollback. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Canonical sources

For current system status, prefer:

1. [Canonical System Map](docs/canonical/CALYX_CANONICAL_SYSTEM_MAP.md)
2. [Core Classification Registry](docs/canonical/CALYX_CORE_CLASSIFICATION_REGISTRY.md)
3. Current code and tests
4. Fresh runtime observations and receipts on an operating Station

Dated plans, archived modules, staged fixtures, lore, and old reports remain useful context but do not become current authority by presence alone.

## Foundational declarations

The human-authored governance index includes the project's foundational value, privacy, retention, disclosure, and exit documents:

- [Governance index](governance/INDEX.md)
- [Human Value Declaration](governance/HVD-1.md)
- [Privacy Boundary Schema](governance/PBS-1.md)
- [Data Retention Policy](governance/DRP-1.md)
- [Disclosure Protocol](governance/DP-1.md)
- [Exit Guarantee](governance/EG-1.md)

Those texts keep their own authority and interpretation constraints. This public guide intentionally links rather than rewriting them.

## Security and privacy

Security reports should follow [SECURITY.md](SECURITY.md). Never place credentials, private identifiers, unredacted runtime evidence, or personal operator context in a public issue or pull request.

## Maintainer model

Station Calyx is currently maintainer-led rather than governed by a foundation or elected committee. Contributions are welcome, but acceptance and canonical promotion remain maintainer decisions. That model may evolve; changes should be stated explicitly rather than implied.
