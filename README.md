# Station Calyx

Local-first AI governance and coordination system. This repository contains the architecture, code, and documentation for Station Calyx and BloomOS: a private coordination layer (CBO, agents, sensors) with gateway-isolated public interaction.

---

## What Is This?

Station Calyx is a **local-first** multi-agent governance stack that runs on a single machine or private network. It provides:

- **Central Bridge Overseer (CBO):** Planning, task dispatch, metrics, and policy enforcement.
- **Agent registry and scheduling:** Registered agents consume tasks from a queue and report status.
- **Sensors and governance:** Policy files, registry, TES-style metrics, and resource checks.
- **Gateway (public edge):** The only public-facing path. All external access goes through the Gateway; Station Calyx itself is loopback-only.

BloomOS refers to the broader operational and telemetry layer (boot guard, sun-cycle, energy/reality atoms) used in conjunction with Station Calyx. The repo is **architecture-only**: code, schemas, and docs. Runtime state (telemetry, exports, CBO queue, logs) lives outside the repo or under ignored directories.

---

## Core Principles

1. **Local-first:** Station and CBO run on localhost or a private network. No direct public exposure of Station endpoints.
2. **Gateway-isolated public interaction:** Public clients talk only to the Gateway (auth, rate limit, schema validation). The Gateway forwards to Station over a private path.
3. **Architecture-only repo:** No runtime artifacts, telemetry, or sensitive data in git. State lives under `runtime/`, `logs/`, etc., and is gitignored.
4. **Policy and registry as source of truth:** Agent capabilities and policy constraints are defined in config and registry; CBO enforces them.

---

## Architecture Overview

- **`calyx/cbo/`** — CBO core: bridge overseer, plan engine, task store, dispatch, sensors, API. Runtime state (e.g. task queue, objectives) is written under `runtime/cbo/` (or `{CALYX_RUNTIME_DIR}/cbo/`).
- **`calyx/core/`** — Registry, policy, shared config.
- **`station_calyx/`** — Station API and routes (loopback-only by default).
- **`deploy/gateway/`** — Gateway scaffolding and contract. Public traffic terminates here; Gateway forwards to Station.
- **`tools/`** — Scripts for agents, dashboard, maintenance, sys-integrator, CBO CLI.
- **`docs/`** — Architecture, gateway contract, onboarding, triage, workflows.

Public users **must not** call Station Calyx directly. They use the Gateway; the Gateway calls Station on `http://127.0.0.1:8420` (or configured private URL).

---

## Security Model

- **Station Calyx:** Binds to loopback by default. Non-loopback bind requires an explicit override (e.g. `CALYX_ALLOW_NON_LOOPBACK=true`). Not intended for direct internet exposure.
- **Gateway:** Only component that should be public. Contract and controls (HMAC, rate limit, schema validation, allowlisted forwarding) are in `docs/gateway.md`.
- **Repo hygiene:** Forbidden paths (telemetry, exports, station_calyx/data, runtime, logs, keys, etc.) must not be tracked. CI runs `tools/check_forbidden_tracked_paths.sh` and Python compile checks.

---

## What This Is Not

- **Wake-word-first:** Speech/wake-word pipelines (e.g. listener scripts, KWS) may exist in the repo for experimentation but are not the primary or required entry point. This README does not position the project as a wake-word-first product.
- **Outcome Density as primary product:** Outcome Density runs and benchmarks are one use case, not the main positioning of the repo. The repo is a governance and coordination stack.
- **Direct public Station API:** There is no supported model where external clients call Station Calyx directly. Use the Gateway.

---

## Current Status

- **Repository:** Architecture-only; history rewritten to remove runtime artifacts; CBO runtime state relocated to `runtime/cbo/`.
- **Hygiene:** Forbidden-path check and `py_compile` sanity run in CI (`.github/workflows/public-repo-hygiene.yml`).
- **Gateway:** MVP contract and scaffolding in place; see `docs/gateway.md`.
- **Public readiness:** Verification report in `reports/security/public_release_readiness_verification_2026-02-11.md` (when present).

---

## Quickstart

**Prerequisites:** Python 3.10+; use a virtualenv.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Run tests:**

```powershell
pytest -q
```

**Useful entry points:**

- CBO and agents: see `calyx/cbo/README.md` and `docs/AGENT_ONBOARDING.md`.
- Triage loop: `docs/TRIAGE.md`.
- Station CLI: `docs/CALYX_CLI_GUIDE.md`.
- Gateway contract: `docs/gateway.md`.

**Key paths:**

- `calyx/cbo/` — CBO logic and API.
- `station_calyx/` — Station API server.
- `tools/` — Scripts and utilities.
- `docs/` — Architecture and operational docs.

---

## Contributing

- Keep changes config-driven; add tests for new behavior.
- Update `requirements.txt` when adding dependencies.
- Do not track runtime artifacts; respect `.gitignore` and the hygiene denylist.

---

## Troubleshooting

- **ExecutionPolicy (PowerShell):** If script execution is blocked, see `OPERATIONS.md` for `-ExecutionPolicy Bypass` usage for venv activation or one-off runs.
- **Audio/speech (optional):** If you use listener or wake-word scripts and hit SciPy/soundfile issues on Windows, install wheels with `pip install soundfile scipy` or use the debug listener that avoids those deps.
