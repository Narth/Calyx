# Security Policy

Station Calyx is an active research prototype. Security reports are welcome, but the project is not a production-certified security appliance and does not currently publish supported release branches.

## Supported versions

| Version | Security updates |
| --- | --- |
| Current `main` | Best-effort |
| Historical branches, tags, patches, and archived modules | Not supported |

No stable production release is currently offered.

## Report a vulnerability privately

Use [GitHub Private Vulnerability Reporting](https://github.com/Narth/Calyx/security/advisories/new).

Please include:

- the affected path, component, or commit;
- the impact you believe is possible;
- the smallest safe reproduction;
- whether credentials, personal data, or live infrastructure may be involved;
- any mitigation you have already applied.

Do not place secrets, live identifiers, exploit details, personal operator context, or raw runtime evidence in a public issue.

If a credential may have been exposed, revoke or rotate it immediately. Do not wait for repository cleanup or maintainer confirmation.

## Deployment boundary

The canonical local service topology is:

| Service | Default bind | Public exposure |
| --- | --- | --- |
| Dev Harness | `127.0.0.1:7777` | Never expose directly. |
| CBO Core | `127.0.0.1:7778` | Never expose directly. |
| Avatar Web | `127.0.0.1:7780` | Never expose directly. |
| Telemetry Gateway | `0.0.0.0:7781` | Remote-support boundary only; secure configuration and an outer trusted network boundary are required. |

Before allowing remote Telemetry Gateway access:

1. Set a non-empty `TELEMETRY_SECRET`.
2. Require a stable `X-Telemetry-Client-ID` for every client.
3. Use a trusted tunnel, VPN, host firewall, or equivalent network boundary.
4. Account for the current source-attestation gap: `CALYX_GOVERNANCE_REQUIRED=true` rejects Telemetry Gateway, Avatar Web, and CLI Avatar chat requests because those clients do not yet send the trusted-source headers CBO Core requires.
5. Do not use the compatibility-mode gateway path for consequential remote operations as if it were strict governance.
6. Confirm `CBO_CHAT_URL` points only to the intended trusted CBO Core; the default is loopback.
7. Confirm the local audit path is writable and the gateway reports a trusted audit state.
8. Account for the unauthenticated `/health` route and FastAPI's default `/docs`, `/redoc`, and `/openapi.json` routes at the outer boundary.
9. Understand which local or cloud model route receives the request.

Telemetry Gateway does not provide a built-in TLS-termination guarantee. Binding a port, adding a tunnel, or receiving a model response does not make the deployment secure.

The gateway audit log can contain a claimed client label, source/forwarding metadata, session labels or hashes, request hashes, status, and error details. Treat it as sensitive operational metadata. No automatic rotation for that JSONL file is currently claimed; apply an operator-controlled retention process or keep remote ingress disabled.

## Provider disclosure

CBO Core can be configured to call local Ollama or external model providers. When an external provider is selected, relevant request content and selected context may leave the workstation under that provider's terms and controls.

Never assume “local-first” means “offline-only” for every configuration. Review environment variables and routes before using sensitive data.

## Repository and privacy boundary

This repository is public. Treat every tracked file, branch, pull request, issue, artifact, and commit as publicly readable.

Do not commit:

- API keys, bot tokens, passwords, private keys, or `.env` files;
- live Discord, telemetry, account, or device identifiers;
- personal operator profiles or private continuity files;
- raw `runtime/`, logs, receipts, telemetry, or evidence exports;
- unredacted local paths, command lines, screenshots, or machine inventories;
- real vulnerability payloads.

Automated secret scanning detects patterns, not meaning. A personal name, stable identifier, local path, or sensitive narrative can pass a secret scan and still be inappropriate to publish.

The repository contains historical and experimental material from earlier project phases. This policy does not claim that all history has been semantically scrubbed. Report inappropriate public data privately.

## Current security controls

Current repository and runtime controls include:

- gitleaks checks in pull-request and `main` hygiene workflows, with non-shallow checkout history available to the scanner;
- forbidden tracked-path checks;
- lint, unit, schema, harness, and receipt validation in Code Factory CI;
- loopback defaults for core HTTP services;
- an external-emitter preflight gate in the governed sunrise path;
- client-ID-based session namespacing and pre-forward audit confirmation in Telemetry Gateway;
- Discord caller/channel allowlists;
- proposal, approval, execution, and receipt models for governed operations.

These controls are scoped mechanisms, not a blanket security guarantee. Some settings preserve backward compatibility and require deliberate strict configuration.

## Explicit limitations

- No independent third-party security audit is claimed.
- No production hardening or availability guarantee is claimed.
- Full Station operation is Windows-first and workstation-specific.
- Historical, staged, archived, or specification-only modules may not follow the current normal path.
- Telemetry Gateway currently has no gateway-level rate limit, request-body size limit, or explicit field allowlist beyond requiring a JSON object.
- On Windows, every successful gateway forward launches `Scripts/update_state_checks.ps1`, which can update `STATE.md` and runtime evidence even when the chat body requests observe mode and disables tools.
- A passing test proves the tested condition, not the absence of every vulnerability.
- A receipt proves that a defined record was emitted; it does not make arbitrary claims inside a record true.
- Cloud-provider, Discord, tunnel, operating-system, and dependency security remain shared external dependencies when used.

## History rewrite notice

Repository history was rewritten on February 12, 2026 after exposed credentials were found in an earlier configuration file. If you cloned before that rewrite, re-clone rather than merging unrelated pre-rewrite history.

That incident is documented in [security engineering notes](docs/security.md). History rewriting cannot recall existing clones, forks, caches, or copied credentials; rotation remains mandatory after exposure.

## Security design documents

- [Security engineering notes](docs/security.md)
- [Gateway boundary](docs/gateway.md)
- [Station stack policy](docs/STATION_STACK_POLICY.md)
- [Public repository denylist](docs/public_repo_denylist.md)
- [Governance index](governance/INDEX.md)
