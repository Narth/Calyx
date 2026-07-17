# Security Engineering Notes

The repository-wide reporting policy is [SECURITY.md](../SECURITY.md). This document explains the public-repository checks and their limitations.

## CI controls

### Public Repo Hygiene

`.github/workflows/public-repo-hygiene.yml` runs on pull requests to `main` and pushes to `main`.

It currently:

- checks out full Git history;
- runs `tools/check_forbidden_tracked_paths.sh`;
- checks canonical spine invariants;
- runs gitleaks with repository configuration;
- compiles selected Python modules.

### Code Factory Gates

`.github/workflows/code_factory_gates.yml` classifies pull-request risk and selects a validation lane. Depending on the lane, checks include:

- Flake8 and Pylint;
- Python tests;
- schema validation;
- benchmark harness variants;
- PR-specific Hub Runner receipt generation and presence checks;
- CI receipt generation and validation.

The workflow is evidence for the named checks. It is not evidence that every tracked document is current, every privacy-sensitive value was recognized, or every runtime configuration is safe.

## Secret scanning is not privacy review

Gitleaks is designed to recognize secret patterns. It may not recognize:

- stable account or channel identifiers;
- names and biographical details;
- local usernames and filesystem paths;
- sensitive screenshots or logs;
- operational details embedded in prose;
- synthetic-looking values that are actually live.

Before publishing, review both the staged diff and the full set of newly tracked files for semantic sensitivity.

## Local pre-publish checks

Useful checks include:

```powershell
# Review exactly what will be committed.
git diff --cached --stat
git diff --cached

# List files that ignore policy considers unusual.
git status --short --ignored

# Run the public path gate in Git Bash or CI-compatible shell.
bash tools/check_forbidden_tracked_paths.sh

# Run the test suite.
python -m pytest -q
```

Also search staged material for project-specific identifiers and local path fragments. Do not print live secrets merely to prove they exist.

## Runtime artifacts

Generated state belongs under ignored local runtime paths. Source code for receipt, evidence, or validation systems belongs in normal source directories such as `calyx/evidence_ledger/`; generated ledgers and receipts remain under `runtime/`.

Stable synthetic fixtures may be tracked when they are necessary for deterministic tests and are explicitly reviewed. A fixture must not be copied from a live machine without redaction and provenance review.

## Network review

Any change that adds an outbound provider, inbound listener, wider bind address, or new forwarding route should document:

- the data sent or accepted;
- authentication and authorization behavior;
- default-deny behavior;
- audit and failure behavior;
- configuration required for strict operation;
- how the operator disables or revokes the path.

See [Gateway Contract](gateway.md) for the current remote-support boundary.

## February 2026 history rewrite

On February 12, 2026, repository history was rewritten after credentials were found in a tracked configuration file. Commit identifiers changed. Anyone holding a pre-rewrite clone should re-clone or explicitly reset to the current remote history.

Credential rotation was and remains more important than history removal. Git history rewriting reduces ordinary discovery but cannot recall prior clones, forks, caches, or copies.

## Ongoing public-hygiene work

The project has a long experimental history. Dated operations documents, archived code, staged fixtures, and identity-oriented files require continuing classification and semantic privacy review. This documentation refresh does not claim a complete history purge.

Use private vulnerability reporting for a specific sensitive finding rather than opening a public issue.
