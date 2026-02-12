# Station Calyx

**Station Calyx** is a local-first governance and coordination stack for AI agents.  
This repository contains the **architecture, code, and documentation** for Station Calyx and BloomOS: a private coordination layer (CBO, agents, sensors) with **gateway-isolated** public interaction.

> **Public clients do not call Station Calyx directly.**  
> If anything is exposed beyond localhost, it should be the **Gateway** — not Station.

---

## What this is

Station Calyx runs on a single machine (or private LAN) and provides:

- **Calyx Bridge Overseer (CBO)**: planning, task dispatch, policy enforcement, and status reporting.
- **Registry + policy as source of truth**: agent capabilities and constraints are defined in config/registry and enforced by governance gates.
- **Telemetry-grounded operation**: the system treats observations, receipts, and state transitions as first-class artifacts.
- **Gateway edge (optional public)**: a hardened “post office” that brokers access to Station over a private path.

**BloomOS** refers to the broader operational substrate used alongside Station Calyx — boot guards, integrity checks, and epistemic/telemetry concepts (e.g., reality atoms). This repo is **architecture-only**: code, schemas, and docs. Runtime state is kept outside git.

---

## Core principles

- **Local-first by default**  
  Station services bind to loopback unless you explicitly override that behavior.

- **Gateway-isolated interaction**  
  If a user or external system talks to Calyx, it should talk to the **Gateway**. The Gateway can authenticate, rate-limit, validate schemas, and forward only allowlisted routes.

- **Deny-by-default governance**  
  Side effects must be explicitly authorized. “Convenience” never outranks safety.

- **Architecture-only repository**  
  Runtime artifacts (telemetry, exports, logs, task queues, evidence stores) must not be committed. CI enforces this.

---

## Repository map (high signal)

- `calyx/cbo/` — **CBO core** (bridge overseer, planning/dispatch, sensors, governance plumbing)  
  Runtime state is written under `runtime/cbo/` (or `{CALYX_RUNTIME_DIR}/cbo/`) and is ignored by git.

- `calyx/core/` — shared primitives (policy, registry, config)

- `station_calyx/` — Station API layer (loopback-only by default)

- `deploy/gateway/` — Gateway scaffolding + contract (the only component intended to be public)

- `docs/` — architecture, doctrine, onboarding, triage, workflows

- `tools/` — utilities and maintenance scripts

---

## Security model (the short version)

- **Station Calyx** binds to loopback by default. Non-loopback binding requires an explicit opt-in (e.g., `CALYX_ALLOW_NON_LOOPBACK=true`). Station is not intended for direct internet exposure.

- **Gateway** is the only component that should be exposed publicly. See `docs/gateway.md` for the contract and controls (HMAC, rate limiting, schema validation, allowlisted forwarding).

- **Repo hygiene is enforced.** CI runs:
  - `tools/check_forbidden_tracked_paths.sh`
  - a Python `py_compile` sanity set

If you’re reviewing this repo for safety: the “public-ready” verification receipt lives in  
`reports/security/public_release_readiness_verification_2026-02-11.md` (when present).

**⚠️ History Rewrite Notice (2026-02-12):**  
This repository underwent a Git history rewrite to remove exposed secrets. All commit SHAs have changed. If you cloned before 2026-02-12, please re-clone or reset your local branches: `git fetch origin --prune && git reset --hard origin/main`

---

## What this is not

- **Not a wake-word-first product.**  
  Speech/wake-word experiments may exist in this repo, but they are not the primary entry point or the project’s purpose.

- **Not “Outcome Density” as the product.**  
  Outcome Density runs and benchmarks are one tool for evaluation, not the headline.

- **Not direct public Station API access.**  
  The supported model is Gateway → Station over a private path.

---

## Quickstart (dev)

> This project is still evolving. Expect moving parts.

**Prereqs:** Python 3.10+, virtualenv recommended.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

### Running Tests

Tests are configured to run in clean environments without manual `PYTHONPATH` tweaks:

```powershell
# Run all mail tests
pytest tests/ -k "test_mail" -v

# Run specific test file
pytest tests/test_mail_roundtrip.py -v

# Run with clean environment (no PYTHONPATH)
$env:PYTHONPATH = $null; pytest tests/ -k "test_mail" -v
```

**Configuration:** `pytest.ini` sets `pythonpath = .` to ensure the `calyx` package is importable.
