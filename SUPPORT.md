# Support

Station Calyx is an active research project maintained on a best-effort basis. There is no service-level agreement, production support contract, or guarantee that a historical module is still operable.

## Before asking for help

Start with:

- [README.md](README.md)
- [Getting started](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Documentation index](docs/INDEX.md)
- [Security policy](SECURITY.md)

## Public questions and bugs

Use [GitHub Issues](https://github.com/Narth/Calyx/issues) for:

- reproducible bugs;
- documentation gaps;
- setup questions that contain no secrets or personal data;
- bounded feature proposals;
- portability and test failures.

Include your operating system, Python version, the command you ran, sanitized output, and the smallest reproduction you can provide.

## Sensitive security findings

Do not open a public issue. Follow [SECURITY.md](SECURITY.md) and use GitHub's private vulnerability reporting path.

## Operational incidents

If a configured Station is behaving unexpectedly:

1. Stop remote ingress or revoke the relevant token.
2. When safe after immediate containment, preserve the minimum necessary local evidence before further state changes.
3. Run the governed sunset path: `.\Scripts\sunset_calyx.ps1`.
4. Do not upload raw runtime directories, credentials, personal context, or identifiers to GitHub.

## Response expectations

Issues may be triaged, redirected, or closed when they concern unsupported deployments, unreviewed historical modules, or requests that weaken the project's authority and privacy boundaries. Clear reproductions and bounded proposals are easier to act on.
