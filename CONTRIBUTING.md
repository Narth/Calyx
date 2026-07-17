# Contributing to Station Calyx

Thank you for helping make Station Calyx clearer, safer, and more useful.

The project is an active research prototype with a broad historical tree. The best contributions are usually bounded: one documented problem, one reviewable change, and evidence proportional to its consequence.

## Good places to contribute

- onboarding and documentation clarity;
- privacy and public-repository hygiene;
- tests for existing contracts;
- Windows and Python portability;
- local-hardware efficiency;
- receipt, topology, and evidence tooling;
- corrections where public claims outrun current code;
- narrow security hardening with an explicit threat model.

Large autonomy, federation, network exposure, or control-plane changes require prior maintainer discussion and explicit authority review.

## Before opening a change

1. Read [README.md](README.md), [GOVERNANCE.md](GOVERNANCE.md), and [SECURITY.md](SECURITY.md).
2. Search existing [issues](https://github.com/Narth/Calyx/issues) and pull requests.
3. Open an issue first for changes that alter authority, external communication, data retention, identity, or the canonical lifecycle.
4. Never include secrets or sensitive vulnerability details in a public issue.

## Development setup

Station operation is Windows-first. The Python test suite uses Python 3.11 and can run in a clean checkout:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

See [Getting started](docs/GETTING_STARTED.md) for the configured Station lifecycle.

## Pull request expectations

A useful pull request explains:

- what changed and why;
- whether the change is code, documentation, proposal, or runtime evidence;
- any effect on human authority, network access, providers, identity, or retained data;
- tests and checks performed;
- rollback or reversal steps;
- known limitations and work left out of scope.

Keep generated runtime artifacts out of commits. Stage files explicitly when your worktree contains unrelated local changes.

## Evidence language

Use precise verbs:

- “implemented” means code exists;
- “tested” means a named test or check passed;
- “observed” means current runtime evidence was inspected;
- “approved” means a human authorized the bounded action;
- “executed” means the action occurred;
- “proposed” or “specification-only” means it has not been promoted to operation.

Avoid describing staged schemas, historical modules, or tests as a live autonomous capability.

## Safety and privacy checklist

Before pushing:

- inspect `git diff --cached`;
- run the relevant tests;
- confirm no `.env`, tokens, IDs, personal profiles, runtime receipts, or machine captures are staged;
- confirm examples use synthetic values;
- state any new external call or listening socket;
- keep core Station services on loopback;
- add a rollback path for consequential changes.

Automated secret scanning does not replace semantic privacy review.

## Documentation

Public documentation should help a new human answer:

1. What is this?
2. Why does it matter?
3. What works now?
4. What is experimental or historical?
5. What leaves the machine?
6. How can I stop or undo it?

Use relative links for repository files and check that every referenced path exists.

## Review and acceptance

Maintainers may ask for narrower scope, stronger evidence, clearer authority boundaries, or an explicit operator decision. A merged contribution becomes repository content; it does not automatically become canonical runtime authority.

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).
