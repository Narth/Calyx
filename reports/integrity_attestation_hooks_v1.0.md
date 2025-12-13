# 🛡️ Integrity Attestation Hooks v1.0

Internal System Integrity Guidance — Draft under Architect Authority  
This document does not modify governance or introduce new capabilities.

## 0. Purpose
Integrity Attestation Hooks provide evidence-only, read-only mechanisms for confirming:
- the environment has not drifted
- critical packages and modules remain unchanged
- system state at runtime matches governance expectations

Hooks are reports, not processes: no autonomous scans, no modifications, no added agent capabilities. All hooks are human-triggered.

Supports: compliance pulses, lab parity mapping, change-window validation, adversarial suite runs, governance audits.

## 1. Scope of Integrity Attestation
Covers: environment configuration; installed package versions; hash fingerprints of critical files; interpreter/venv state; optional TPM/Secure Boot data (manual). Excludes: autonomous detection, real-time monitoring, system modification, sandbox escape, external calls.

## 2. Required Attestation Components

### 2.1 Package & Dependency Hashing
- `pip freeze > logs/pip_freeze.txt`
- SHA-256 hashes for site-packages entries (optional if requested)
- Hash of Python interpreter binary
- Hash of requirements.txt (if used)
- Hash of venv activation scripts
- Evidence recorded in `reports/integrity_attestation_<timestamp>.md`

### 2.2 Core Module Hashes
Hash critical files: `bloomos/*.py`, `agents/*.py`, `tools/*.py`, governance docs, TES scoring scripts (e.g., recalculator). Purpose: detect drift/tampering.

### 2.3 System Snapshot Hash
SHA-256 checksum of latest `logs/system_snapshots.jsonl` entry to anchor to runtime state.

### 2.4 Governance Hash Confirmation
Include hashes for: Governance Charter, Responsibilities doc, Lab Parity Mapping, Control Mapping Matrix, Adversarial Suite. Confirms compliance context at pulse time.

### 2.5 Optional TPM/Secure Boot Evidence
If available (manual only): Platform attestation UUID, Secure Boot state, TPM version. No automation introduced.

## 3. Execution Rules
- Manually triggered
- Generate read-only evidence
- No environment changes
- No network calls
- No dependency/scanner modification
- No silent/background processes
- Agents only reference attestations; they do not compute them.

## 4. Integration With Governance Artifacts
Supports: Compliance Pulse Specification, Lab Parity Mapping, Control Mapping Matrix, Scale Probe Plan, Burst/pulse windows, Adversarial suite validation.

## 5. Status
- Version: 1.0
- Tier: Internal Integrity Guidance
- Authority: Architect
- Safety Risk: None
- Next Review: At Architect discretion
