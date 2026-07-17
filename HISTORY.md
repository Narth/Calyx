# HISTORY.md — Station Calyx Lifecycle & Development Timeline

Chronological recap of development, integrations, doctrines, and Station Calyx lifecycle. Built from **C:\\Calyx_Terminal** git history and dated doctrines/specs in the repo. Timestamps and context are drawn from commits and from document headers (Date:, Effective Date:, etc.); no unattributed inference is used.

---

## Key Actors — Station Calyx, CBO, BloomOS, Calyx Agents

- **Station Calyx** — The home. The workspace; the governed runtime; the flag we fly. AI-assisted workspace with Calyx spine, contract gate, intent pipeline, Discord Gateway.
- **CBO (Calyx Bridge Overseer)** — Steward of Station Calyx. Primary interface between humans and Calyx operations. Monitors core services, station health loop, build path, Discord Gateway. Integrity, clarification, assurance.
- **BloomOS** — Conceptual layer; agents consume STATUS, heartbeat_ts, checks, health from STATE.md. No reverse dependency; Calyx produces, BloomOS consumes.
- **Calyx Agents** — Agents that operate within Station Calyx (CBO, CP6–CP12, Triage, Navigator, etc.). See `COMPENDIUM.md`.

---

## Historical Note: OpenClaw

OpenClaw helped bring the Station Calyx dream to fruition. Multi-channel assistant, voice, skills, tools — it contributed to the architecture and governance we have today. It is now **gated** (decommission playbook; external emitter gate); significant work remains before testing can be considered again. See `docs/operations/OPENCLAW_DECOMMISSION_PLAYBOOK.md`, `docs/OPENCLAW_CALYX_INTEGRATION.md`. OpenClaw is remembered, not erased.

---

## Scope of This Recap

- **C:\\Calyx_Terminal:** Primary source. Timeline below is derived from this repo’s `git log` and from dated docs under `docs/`, `docs/governance/`, and root.
- **C:\\Calyx_Parking:** Folder exists; it is **not a git repository**. No chronological development history could be extracted; not included in this timeline.
- **C:\\Calyx_Federation_Inbox:** Folder exists (path corrected from earlier “Calyx_Federated_Inbox”). It is **not a git repository**. It functions as an artifact store / shared inbox for federated runs: laptop determinism proofs, ladder summaries, and beacons. See “Calyx_Federation_Inbox (artifact timeline)” below for dates inferred from contents.

---

## Timeline (oldest to newest)

### 2025-10-20 — Baseline

- **Git:** `baseline before Cursor` (single commit in history).
- Establishes pre–Cursor baseline for Station Calyx.

---

### 2025-10-22 — 2025-10-26 — CBO Genesis & Agent Onboarding

- **Docs (dated):** Bridge Overseer Genesis, Station Wings autonomy, AI4All teaching system, Multi-agent coordination (2025-10-22 to 2025-10-23); Smart Computing optimization (2025-10-23); CBO onboarding prompt (2025-10-24); CBO_AGENT_ONBOARDING, CBO_CONTRACT, DOCUMENTATION_AUDIT_2025-10-24 (2025-10-24); DOCUMENTATION_AUDIT_2025-10-25_CBO, DATA_RETENTION (2025-10-25); AGENT_ONBOARDING_SVF_v2, TRUTH_AND_QUALITY_STANDARD, FORESIGHT_GUIDE (2025-10-26).
- **Doctrine:** CBO becomes first point of contact for new agents; onboarding flow (registration → verification → registry), `docs/CBO_AGENT_ONBOARDING.md`. CBO contract and documentation audits establish early governance and retention policy.

---

### 2025-12-04 — CBO Governance Hardening

- **Git:** `Harden CBO governance to align with Calyx Physics`; `Add overseer loop observability and bounded test mode`.
- Tightening of CBO governance and observability in line with Calyx “physics” and bounded testing.

---

### 2025-12-13 — Public Governance & Sync Substrate

- **Git:** Initial commit; `Public view of Calyx Theory and Station Calyx governance framework. Current operation structure in place for Outcome Density research and Calyx agent framework governance simulations`; merge from origin/main; `Resolve README merge markers and ignore local archives`; `Add bounded sync helper and governance docs`; `Quarantine audio samples and telemetry logs`; `Tighten sync allowlist and privacy critical patterns`.
- **Docs (dated):** HARDWARE_PROFILING, HARDWARE_PROFILING_QUICKSTART (Last Verified / Commit 2025-12-13).
- Public-facing governance and Outcome Density research structure; bounded sync, privacy allowlist, and telemetry quarantine established.

---

### 2026-01-03 — 2026-01-05 — Station Re-entry & Memory / BITNET

- **Docs (dated):** MEMORY_ARCHITECTURE_v1.0, MEMORY_MVP_IMPLEMENTATION_PROPOSAL (2026-01-04) reference Station Re-entry Mode (2026-01-03), supervisor restart, TES; BITNET_INTEGRATION (2026-01-05) Phase 2.
- **Doctrine:** Bounded scope “Station Re-entry”; memory MVP and architecture; BITNET Phase 2 integration (WSL2/Ubuntu).

---

### 2026-01-09 — 2026-01-10 — Node Evidence Relay & Multi-Node Sync

- **Docs (dated):** manual_relay_sync_v0 (2026-01-09); node_evidence_relay_v0, network_evidence_push_v0 (2026-01-10).
- **Git:** Multiple sync commits: Laptop-Node Sync, Desktop-Node Sync, Workstation Node Sync, Laptop Node Sync (Pre-Network Test), Merge main.
- Canonical JSON and hash chain semantics for node evidence; multi-node (laptop, desktop, workstation) sync and pre–network test state.

---

### 2026-01-26 — Discord Integration & Session Backup

- **Git:** `DIscord Integration Commit`; `Session backup: TUI, governance docs, Clawdbot grounding rules`.
- Discord integrated into the workflow; session backup captures TUI, governance docs, and Clawdbot grounding rules.

---

### 2026-02-01 — Skills Installation

- **Docs (dated):** skills_installation_report.md (2026-02-01).
- Record of skills installation and integration.

---

### 2026-02-11 — Runtime Artifacts & Public Repo Denylist

- **Docs (dated):** runtime_artifacts_inventory_2026-02-11; public_repo_denylist (2026-02-11 ground-truth check); CBO runtime JSONL relocation note (runtime/cbo/).
- Inventory of runtime artifacts and denylist for public repo safety; CBO runtime state relocation documented.

---

### 2026-02-12 — Public Repo Curation, Secrets Purge, Calyx Mail Specs

- **Git:** `Public repo curation: governance substrate + benchmarks scaffold`; `Add force-push completion report`; `Fix gitleaks findings and workflow input`; `Fix repo hygiene workflow portability`; `Fix Python compilation to use existing files only`; `Pre-Benchmark Testing`.
- **Docs (dated):** security.md — **History rewrite on 2026-02-12** to remove exposed secrets (e.g. openclaw.config.json with Discord bot token and API key); all commit SHAs changed. public_repo_safe_open_plan; calyx_mail_v0.1_architectural_plan, calyx_mail_v0.1_architectural_delta_revised, calyx_mail_state_machine_v0.1, calyx_mail_spec_v0, calyx_mail_protocol_threat_model_v0.1; spec/mail (replay_state, signed_payload, canonical_encoding) v0.1.
- **Doctrine:** Governance substrate and benchmarks scaffold; gitleaks and workflow hygiene; **mandatory history rewrite** for secret purge (see `docs/security.md` and reports/security). Calyx Mail v0.1 architectural and threat-model specs established.

---

### 2026-02-13 — Benchmark Validation & Lane 2 Run

- **Docs (dated):** BENCHMARK_ENHANCEMENTS_v0_2, RUN_ENVELOPE_PROPOSAL, LANE2_RUN_REPORT (Execution Date 2026-02-13), BENCHMARK_VALIDATION_REPORT.
- Benchmark enhancements, run envelope proposal, and Lane 2 execution report and validation.

---

### 2026-02-14 — Federated Telemetry & Lane-1 Protocol

- **Git:** `Federated telemetry provisioning + benchmark harness artifacts (laptop)`; `Stop tracking embedded workspace repo (ignore workspaces/Helping-the-Help)`; `Add telemetry import script + ignore local temp artifacts`; `Add telemetry outbox mirror module and improve smoke test traceback`; `Tighten toolcall JSON protocol + schema validation for Lane-1 reliability`; `Retry once on LLM JSON parse failure with receipt metadata`; session stash (desktop pre-sync).
- Federated telemetry and outbox mirror; Lane-1 toolcall JSON and schema validation tightened; single coordinator / dedupe concerns later addressed in SYSTEM_INTEGRITY_VALIDATION and Discord DM analysis.

---

### 2026-02-15 — Protocol Probe & Lane-1 Gates

- **Git:** Debug raw capture for protocol_probe probe_read (and revert); `lane1: gate on protocol_compliance_rate; keep tool_attempt as telemetry`; `lane1: unknown tool names invalid; enforce no-tool probe`; `local_runtime: fix truncated responses in protocol_probe`; `protocol_probe: harden injection case to no-tool JSON envelope`; `local_runtime: honor num_predict from config (alias max_output_tokens)`; `protocol_probe: detect truncated JSON and force fresh retry`.
- Lane-1 reliability: protocol_compliance_rate gating, no-tool probe enforcement, truncated-response handling, and local_runtime config (num_predict).

---

### 2026-02-16 — GDH Determinism & Lane 2 Moratorium

- **Git:** `Finalize GDH determinism + Lane2 moratorium + export tool`; `GDH system_split: honor Lane2 moratorium fields`.
- **Docs (doctrine):** docs/governance/DETERMINISM_POLICY_v0.1.md (content vs provenance determinism; gdh_action_run_content, gdh_temperament_run_content); docs/governance/LANE2_TOOL_MORATORIUM_v0.1.md (Lane 2 suite `prompt_injection_v0_2`: canonical NO_TOOL system action, violation flags as telemetry; Lane 1 unchanged).
- Cross-node “system wavelength” and GDH export; Lane 2 tool moratorium and determinism policy applied.

---

### 2026-02-17 — Canonical Spine ADR, Spine Validation, Discord DM Analysis

- **Docs (dated):** ADR-0001-canonical-spine (2026-02-17); spine_validation_summary (2026-02-17); DISCORD_DM_TEST_ANALYSIS_2026-02-17.
- **Doctrine (ADR-0001):** Single canonical runtime spine: **Calyx Mail → Intent Artifact → Work Envelope → Contract Gate → Execution → Receipts**. All inbound becomes Mail Envelope first; only CBO mints Work Envelopes; contract deny-by-default; every execution produces a receipt; non-operational code migrated or archived (see `docs/SPINE.md`, `docs/ARCHITECTURE_DECISIONS/ADR-0001-canonical-spine.md`).
- **Spine validation:** Invariants checked (mail envelope, CBO mint, contract validation, receipts, archive/import rules, BloomOS no reverse dependency); Phase A (mail security, replay ledger), Phase B (outbound), Phase C (determinism) summarized in `docs/spine_validation_summary.md`.
- **Discord DM test (2026-02-17):** Analysis of triple processing (one message → three envelopes/replies), inconsistent bridge-pulse replies, and execution test (containment held; response messaging improved). Recommendations: dedupe by message_id, single bot instance, deterministic bridge-pulse template, refusal rule for out-of-scope execution (see `docs/DISCORD_DM_TEST_ANALYSIS_2026-02-17.md`). Aligns with `docs/SYSTEM_INTEGRITY_VALIDATION.md` (single coordinator lease, pulse check).

---

### 2026-02-18 — Workspace Initialization & CBO Onboarding (Cursor)

- **Context:** CBO onboarding and workspace setup via Cursor; HISTORY.md created for collaboration milestones.
- **Events (from prior HISTORY.md):**
  - Core files created: RESPONSIBILITIES.md, IDENTITY.md, USER.md, SOUL.md; CBO role and responsibilities; workspace structure per AGENTS.md.
  - Identity & user configuration: CBO digital persona (IDENTITY.md), user profile (USER.md), SOUL.md boundaries, hardware constraints (USER.md).
  - System optimization: HISTORY.md enabled; config for hardware-constrained environments.
  - Documentation: HISTORY.md chronicle started; system optimized for operator hardware constraints.

---

### 2026-02-19 (Session Date)

- **This recap:** HISTORY.md updated with full chronological timeline from Calyx_Terminal git and repo doctrines; scope and data sources documented; Calyx_Parking and Calyx_Federation_Inbox status noted. Path corrected to **C:\\Calyx_Federation_Inbox** (not Federated_Inbox).

---

### 2026-02-21 — CBO Stack: Phase 6, Local LLM, Usage/Cost, STATE for BloomOS

- **CBO Hub (cbo_hub/):** Dev Harness (7777), CBO Core (7778), CLI Avatar. Single `/chat` endpoint; no new routes.
- **Phase 6 — Kimi (second_opinion):** Optional second opinion via Moonshot/Kimi; gated by `allow_second_opinion` (default false, no silent spend). Receipt fields: provider, base_url, model_id, http_status, error_snippet. Tool loop extended to architect, workhorse, second_opinion, local; STATE.md injected for second_opinion and local. Kimi K2.5 wired: `KIMI_MODEL` fallback when `KIMI_MODEL_ID` unset; `temperature=1` (K2.5 constraint).
- **Local LLM:** `model_role=local` → Ollama `/api/generate`; `_call_local()`, `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL_ID`; local_receipt; CLI `/local` command. Fourth voice; receipt-backed, cost=0.
- **Usage & cost:** Per-request token usage (input/output/total) from Anthropic, OpenAI, Kimi, local; normalized in receipt `usage`. Optional cost simulation via `*_INPUT_PER_MILLION`, `*_OUTPUT_PER_MILLION` (USD); `cost_estimate_usd` and `request_latency_ms` in receipt. Doc: `cbo_hub/docs/USAGE_AND_HEALTH.md`.
- **Spend summary:** Receipts include `providers_called`, `second_opinion_enabled`; stub line replaced with “Tools used: …”; “Context: STATE.md injected” when applicable; CLI shows second_opinion_text in own panel.
- **STATE.md for BloomOS:** Minimal status block added: Status, heartbeat_ts, override, lock, checks. One-line agent instruction: use Status + heartbeat_ts + checks only; act on unhealthy or stale. Three-voice run (architect, workhorse, Kimi K2.5) produced recommendations for heartbeat automation; consolidated in `cbo_hub/receipts/STATE_HEARTBEAT_RECOMMENDATIONS.md`.
- **Maintenance mode:** After first healthy STATE.md, station switched to maintenance for assessment and CBO Stack review. STATE.md Status set to maintenance, override on; rationale: station assessment 2026-02-21.

---

## Calyx_Federation_Inbox (artifact timeline)

**Path:** `C:\Calyx_Federation_Inbox`. Not a git repo; contents are artifact-based.

- **2026-02-16:** `BEACON__20260216T1500Z.txt` (beacon from node DESKTOP-KSHNJ30). `laptop_ladder_20260216` and backups — laptop ladder run and seed summaries (e.g. seed_42, seed_1337, seed_8675309, seed_20260214). `determinism_proof_laptop_20260216`: manifest and suite runs for `protocol_probe_v0_1` and `prompt_injection_v0_2` (node `calyx_laptop_01`), with run timestamps 2026-02-16 through 2026-02-17.
- **transcript.txt:** Records completion of a CBO directive (“pull GDH moratorium support”), matching Terminal commit `afcd10d` (2026-02-16 GDH system_split / Lane2 moratorium). References `tools/compute_gdh_from_export.py` and `docs/governance/DETERMINISM_POLICY_v0.1.md`.

So Federation_Inbox holds federated-run artifacts (laptop proofs, ladder summaries, beacons) aligned with the Terminal’s 2026-02-16 determinism and GDH work; no separate development timeline, only artifact dates.

---

## Key Doctrines & References (by topic)

- **Spine & contract:** `docs/SPINE.md`, `CALYX_CONTRACT.yaml`, `docs/ARCHITECTURE_DECISIONS/ADR-0001-canonical-spine.md`, `docs/SYSTEM_INTEGRITY_VALIDATION.md`.
- **Federated / Discord / Calyx Gateway:** `docs/FEDERATED_OPS_ROADMAP_v0.md`, `docs/DISCORD_CALYX_MAIL_INTEGRATION.md`, `docs/CODE_FACTORY_LOOP_DELIVERABLES.md`, `docs/PR_PROTOCOL.md`. OpenClaw (historical): `docs/OPENCLAW_CALYX_INTEGRATION.md`.
- **Governance & determinism:** `docs/governance/DETERMINISM_POLICY_v0.1.md`, `docs/governance/LANE2_TOOL_MORATORIUM_v0.1.md`.
- **Security & public repo:** `docs/security.md` (history rewrite 2026-02-12), `docs/public_repo_denylist.md`, `docs/public_repo_safe_open_plan.md`.
- **Index:** `docs/INDEX.md` (L1/L2/L3 map of runtime, specs, lore).

---

*This file is the canonical chronological recap. Add new milestones with dates and, when possible, citations to commits or doctrine docs. If you have corrections or additions (e.g. from Calyx_Parking or Calyx_Federation_Inbox), add them with clear attribution.*
