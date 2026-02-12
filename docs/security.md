# Security Scanning

This repository runs `gitleaks` in CI via `.github/workflows/public-repo-hygiene.yml` on:

- Pushes to `main`
- Pull requests targeting `main`

The workflow is configured to fail if any secret findings are detected.

## Local usage

### Option 1: Docker

```bash
docker run --rm -v "$(pwd):/repo" zricethezav/gitleaks:latest \
  detect --source /repo --config /repo/.gitleaks.toml --redact --verbose
```

### Option 2: Local binary

```bash
gitleaks detect --source . --config .gitleaks.toml --redact --verbose
```

Exit codes:

- `0`: no leaks found
- non-zero: leak(s) detected or scan error
