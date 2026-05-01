---
status: active
owner: station
last_reviewed_utc: "2026-04-29"
doctrine_scope: governed
---

# Station Baseline Manifest

## Purpose

This manifest separates Station Calyx rebuildable baseline state from local node state.

The Git baseline is the origin of truth for rebuilding the Station body across local, remote, and cloud nodes. Runtime telemetry is local lived experience. Curated memory and receipts preserve continuity and evidence without silently becoming universal Station truth.

## Sync Classes

### Canonical Baseline

Commit and synchronize these intentionally:

- source code under `calyx/`, `cbo_hub/`, `Scripts/`, `tools/`, `rust/`, `benchmarks/`, and `tests/`
- doctrine and operator-readable governance files such as `AGENTS.md`, `SOUL.md`, `USER.md`, `IDENTITY.md`, `README.md`, `HEARTBEAT.md`, `CALYX_CONTRACT.yaml`, and `COMPENDIUM.md`
- canonical docs under `docs/canonical/`, `docs/doctrine/`, selected `docs/operations/`, and selected `docs/planning/`
- policy and governance definitions under `policy/` and `governance/`
- templates, examples, fixtures, and schemas required to rebuild or validate the Station
- `docs/canonical/STATE_TEMPLATE.md` as the canonical shape for the live generated `STATE.md` digest
- local-only Rust observers under `rust/` when they emit bounded telemetry and do not perform outbound network behavior

Canonical baseline material must be reviewable, portable, and free of workstation-specific secrets or telemetry.

### Local Node State

Do not commit by default:

- `runtime/`
- `logs/`
- `outgoing/`
- `incoming/`
- `responses/`
- `staging/`
- `memory/`
- `state/`
- local telemetry, process snapshots, health histories, node manifests, generated receipts, and temporary ledgers
- `.env*`, `DISCORD_IDS.md`, keys, certificates, private credentials, and per-machine OpenClaw identity or device files
- root `STATE.md`, unless the operator explicitly freezes a copy as evidence

Local node state may be summarized into curated docs or exported evidence only through explicit operator intent.

### Auxiliary OpenClaw Functionality

OpenClaw is publicly available auxiliary software. OpenClaw functionality files may remain on disk for auxiliary execution or testing, but they are not Station baseline material.

Default posture:

- do not commit Calyx-specific OpenClaw configs into the Station baseline
- replace token-like config values with environment placeholders
- pull relevant secrets from environment variables
- keep OpenClaw Discord Gateway authority disabled; Station Calyx owns the governed Discord Gateway path

### Curated Continuity

Treat these as deliberate continuity surfaces:

- `MEMORY.md` when operator-approved for a session lineage
- `memory/YYYY-MM-DD.md` when daily logs are intentionally preserved
- doctrine updates that explain current authority, consent, identity boundaries, and operational posture
- migration notes that enable a new node to resume without importing uncontrolled telemetry

Curated continuity is not raw telemetry. It is operator-readable context with scoped authority.

### Audit Evidence

Receipts and ledgers prove what happened, but they do not automatically become baseline source.

Default posture:

- local receipts stay node-local under `runtime/receipts/`
- ledgers stay node-local under `runtime/ledger/` or `runtime/evidence_ledger/`
- evidence may be promoted into `docs/operations/` only when intentionally summarized, redacted, and reviewed

### Operator Decision Surfaces

These require explicit treatment during baseline curation:

- historical OpenClaw source-bearing files under `openclaw/`
- bridge/plugin surfaces under `skills/`
- root continuity surfaces such as `MEMORY.md` and `HEALTH.md`
- any config capable of external communication, model routing, credentials, or device identity

If evidence is ambiguous, classify as `operator_decision` or `local_node_state`, not canonical.

## Baseline Rule

Git restores the Station structure. Curated memory restores continuity. Receipts prove events. Telemetry describes this node. No class may silently impersonate another.

## Required Check

Run before baseline commits and before cloud/remote sync comparisons:

```powershell
.\Scripts\baseline_parity_check.ps1
```

Expected generated artifacts:

- `runtime/baseline_parity_report.json`
- `runtime/node_manifest.json`

These runtime artifacts are local generated state and are not committed by default.
