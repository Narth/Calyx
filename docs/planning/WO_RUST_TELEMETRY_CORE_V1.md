---
status: active
owner: station
last_reviewed_utc: "2026-04-30"
doctrine_scope: governed
---

# WO_RUST_TELEMETRY_CORE_V1

## Purpose

Introduce Rust as a second local observer for Station Calyx telemetry without rewriting the Python substrate.

The goal is not language expansion for its own sake. The goal is independent observation, lower drift risk, and a small durable runtime surface that can keep reporting basic facts when Python orchestration or virtual environments are unhealthy.

## Governance Boundary

This work order authorizes local-only Rust telemetry probes.

It does not authorize:

- outbound network behavior
- service control or process mutation
- replacement of Python orchestration
- credential access
- telemetry export
- autonomous remediation

Rust observers are advisory witnesses. They may report what they see, but they do not become authority by default.

## Initial Scope

`rust/station_probe` is the first Station-owned Rust crate.

The probe may emit JSON containing:

- probe schema and timestamp
- operating system and architecture
- current working directory
- host name when locally available
- process count from local OS commands
- selected listener ports for Station services
- Git branch, HEAD, and tracked-drift status

The probe must avoid third-party crates during the first pass. This keeps bootstrap small and avoids pulling a dependency graph into the baseline before the value is proven.

## Python And Rust Relationship

Python remains the orchestration, governance, and integration surface.

Rust becomes a bounded observer for:

- local system facts
- deterministic parsing or validation
- low-overhead telemetry collection
- future watchdog binaries

Python may call Rust probes as subprocesses and compare Rust observations against Python-derived truth. Disagreement should produce a signal, not silent authority transfer.

## First Validation

Run:

```powershell
.\Scripts\rust_probe_check.ps1
```

Expected behavior:

- if Cargo is installed, build and run `rust/station_probe`
- write the probe result to `runtime/rust/station_probe.json`
- write a check receipt to `runtime/rust/station_probe_check.json`
- if Cargo is missing, skip cleanly with an advisory result

Generated `runtime/` artifacts remain local node state and are not committed by default.

## Promotion Criteria

Before the Rust observer feeds runtime truth or signal scoring:

1. Probe output schema is stable.
2. Missing Cargo remains non-fatal on nodes without Rust.
3. The probe emits no secrets and performs no outbound network activity.
4. Python and Rust observations are compared in an advisory layer.
5. Any mismatch is surfaced with explicit source attribution.

## Future Candidates

Potential later Rust surfaces:

- receipt hash verifier
- policy/schema validator
- process topology sampler
- file integrity manifest checker
- watchdog that reports stale Python heartbeat without mutating services

These require separate work orders before implementation.
