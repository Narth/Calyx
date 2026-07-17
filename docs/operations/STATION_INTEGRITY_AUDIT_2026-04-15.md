---
status: active
owner: station
last_reviewed_utc: "2026-04-15"
doctrine_scope: governed
---

# Station Integrity Audit - 2026-04-15

Scope: repository, context, doctrine, runtime health, security posture, and robustness sweep after moving the active compendium to repo root.

Node mode: local Station Calyx workspace at `C:\Calyx_Terminal`.

## Executive Result

Status: PASS WITH FIXES APPLIED.

The inspection found and corrected four concrete operational defects:

1. Stale active references to the former docs-local compendium path after the compendium move.
2. `Scripts/station_health_check.ps1` failed to parse under the active PowerShell runtime because of source-encoding-sensitive punctuation.
3. Discord Gateway Python preflight and gateway fallback parsing did not accept the Markdown-bold format used by `DISCORD_IDS.md`.
4. `DISCORD_IDS.md` was not ignored, leaving private Discord routing IDs commit-prone.
5. The new audit report initially missed the required docs status header, causing CBO Core startup preflight to fail.
6. Sunrise captured the service-check exit code after piping through `Select-Object`, allowing a failed CBO Core check to be reported in a nominally successful sunrise.

The post-fix validation suite passed:

- `python -m pytest -q`: 347 passed, 4 warnings.
- `git diff --check`: pass.
- PowerShell parse sweep over `Scripts/*.ps1`: pass.
- Python AST parse sweep over `calyx`, `cbo_hub`, `Scripts`, `tools`, `policy`: pass.
- JSON/YAML governance-policy parse: pass, with one expected malformed artifact already in `governance/intents/quarantine/`.
- Redacted secret-pattern scan over committable files: pass.
- Station health and core services: pass.
- Discord Gateway preflight: pass.

## Doctrine Alignment

Checked against local doctrine:

- `AGENTS.md`: explicit consent, scoped identity, deny-by-default execution, evidence requirement, sunrise after system-level changes.
- `SOUL.md`: CBO as steward, station health loop, Discord Gateway, pre-heavy-work checks.
- `USER.md`: operator context and hardware constraints.
- `MEMORY.md`: curated operational continuity.
- `COMPENDIUM.md`: root authority for recognized Station agents and control surfaces.
- `CALYX_CONTRACT.yaml`, `policy/*`, `governance/*`: contract, tripwire, competitor, evidence, and receipt surfaces.

Result: current posture is directionally aligned with Station values: explicit scope, reversible action preference, evidence/receipts, deny-by-default gates, and human authority. The fixes above strengthen that posture by making the checks executable rather than merely declared.

## Local Repairs Applied

### Compendium relocation repair

Moved active compendium authority to:

`C:\Calyx_Terminal\COMPENDIUM.md`

Removed stale literal references to the former docs-local compendium path.

Updated active references in:

- `HISTORY.md`
- `MEMORY.md`
- `Scripts/navigator.ps1`
- `Scripts/triage_orchestrator.ps1`
- `tools/cp6_sociologist.py`
- `tools/cp7_chronicler.py`
- `tools/cp9_auto_tuner.py`
- `docs/AGENT_REPOSITORY.md`
- `docs/AGENT_ONBOARDING.md`
- `docs/AGENT_ONBOARDING_SVF_v2.md`
- `docs/CBO_AGENT_ONBOARDING.md`
- `docs/COPILOTS.md`
- `docs/DOCUMENTATION_AUDIT_2025-10-24.md`
- `docs/DOCUMENTATION_AUDIT_2025-10-25_CBO.md`
- `docs/operations/NAVIGATOR_TRIAGE_MINIMAL_SUNRISE.md`
- `docs/QUICK_REFERENCE.md`
- `docs/prompts/*`

Validation:

Stale docs-local compendium path scan.

Result: no matches.

### Health-check parser repair

Finding: `Scripts/station_health_check.ps1` failed before execution with a PowerShell parser error.

Cause: source text used non-ASCII punctuation in strings/comments and was parsed in the active Windows PowerShell environment in a way that broke string termination.

Fix: normalized affected header/status text to ASCII.

Validation:

`powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\station_health_check.ps1`

Result: PASS. Core services reported `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`.

### Discord allowlist parser repair

Finding: `Scripts/discord_gateway_preflight.py` failed in a clean shell even though sunrise succeeded.

Cause: PowerShell sunrise accepted the actual `DISCORD_IDS.md` Markdown-bold format, but the Python preflight and gateway fallback parser expected digits immediately after a colon.

Fix:

- Relaxed ID extraction in `Scripts/discord_gateway_preflight.py`.
- Relaxed ID extraction in `calyx/cbo/discord_gateway.py`.
- Added `tests/test_discord_ids_resolution.py` for the Markdown-bold format.

Validation:

- `python .\Scripts\discord_gateway_preflight.py`: PASS.
- `python -m pytest tests/test_discord_ids_resolution.py tests/test_contract_intake_parity.py -q`: 5 passed.

### Private Discord ID commit prevention

Finding: `DISCORD_IDS.md` was untracked and not ignored.

Risk: private routing identifiers could be committed accidentally.

Fix:

- Added `DISCORD_IDS.md` to `.gitignore`.
- Added `DISCORD_IDS.md` to `docs/public_repo_denylist.md`.

Validation:

`git check-ignore -v DISCORD_IDS.md`

Result: ignored by `.gitignore`.

### STATE trailing whitespace generator repair

Finding: `git diff --check` failed on `STATE.md` because empty values were emitted as `key: `.

Fix: `Scripts/runtime_truth_contract.ps1` now emits `key:` for empty values instead of trailing whitespace.

Validation:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\update_state_checks.ps1`: PASS.
- `git diff --check`: PASS.

### CBO Core startup-preflight repair

Finding: after a governed sunset-to-sunrise, CBO Core did not remain up on port `7778`.

Cause: this report was added under `docs/operations/` without the required document status header. CBO Core correctly failed its doc-integrity preflight.

Fix: added the required front matter:

- `status: active`
- `owner: station`
- `last_reviewed_utc: "2026-04-15"`
- `doctrine_scope: governed`

Validation:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\restart_service.ps1 -Service cbo_core`: PASS.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\check_calyx_core_services.ps1`: `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`.

### Sunrise validation fail-closed repair

Finding: sunrise printed `cbo_core=fail` but still wrote a successful sunrise receipt.

Cause: `Scripts/start_calyx_core_services.ps1` piped checker output before capturing `$LASTEXITCODE`, so the exit status was not reliably the service-check exit status.

Fix: capture checker output first, immediately store `$LASTEXITCODE`, then select the first output line for display.

Validation target: future sunrise now uses the service checker exit code directly for `validationPassed`.

Final validation:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\station_patch_sunrise.ps1`: PASS.
- Final check result: `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`.
- Final audit health: no mismatches detected.

## Validation Log

Commands and outcomes:

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\patch_readiness.ps1`
  - `PATCH_READY entropy_tier=pass health=pass`
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\Scripts\check_calyx_core_services.ps1`
  - `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`
- `.venv_cbohub311\Scripts\python.exe -m calyx.kernel.external_emitter_gate`
  - no OpenClaw detected
- `.venv_cbohub311\Scripts\python.exe .\Scripts\audit_health.py --since-minutes 30`
  - no mismatches detected
- `python -m pytest -q`
  - 347 passed, 4 warnings
- PowerShell parser sweep over `Scripts/*.ps1`
  - pass
- Python AST parse sweep over `calyx`, `cbo_hub`, `Scripts`, `tools`, `policy`
  - pass
- JSON parse over `policy` and `governance`, using `utf-8-sig`
  - pass
  - expected malformed quarantine artifact: `governance\intents\quarantine\malformed-3d77b19e.json`
- YAML parse over `policy` and `governance`
  - pass
- Redacted secret-pattern scan over committable files
  - pass
- `git diff --check`
  - pass

## Runtime Receipts Observed

Initial sunrise receipt:

`C:\Calyx_Terminal\runtime\receipts\sunrise_receipt__20260415_143626.json`

Key fields observed:

- `status`: `ok`
- `external_emitter_gate`: `passed`
- `audit_health_passed`: `true`
- `boot_context_missing_total`: `0`
- `boot_context_budget_pass`: `true`
- `checks`: `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`
- `openclaw_gateway_task_state`: `Disabled`

Later governed sunset-to-sunrise exposed the CBO Core preflight failure described above:

`C:\Calyx_Terminal\runtime\receipts\sunrise_receipt__20260415_150614.json`

That receipt contained `checks: dev_harness=ok,cbo_core=fail,avatar_web=ok,telemetry_gateway=ok`, which drove the sunrise validation repair.

Final governed sunset-to-sunrise receipt after repairs:

`C:\Calyx_Terminal\runtime\receipts\sunrise_receipt__20260415_151031.json`

Key fields observed:

- `status`: `ok`
- `external_emitter_gate`: `passed`
- `audit_health_passed`: `true`
- `boot_context_missing_total`: `0`
- `boot_context_budget_pass`: `true`
- `checks`: `dev_harness=ok,cbo_core=ok,avatar_web=ok,telemetry_gateway=ok`

State after refresh:

- `health: pass`
- `entropy_tier: pass`
- `runtime_truth_state: fresh`
- `failure_flags_active: 0`
- `failure_change_lane: clear`
- `failure_risk_lane: clear`

## External Cross-Check

External guidance reviewed on 2026-04-15:

- NIST AI RMF Generative AI Profile, AI 600-1:
  `https://doi.org/10.6028/NIST.AI.600-1`
- OWASP Agentic AI - Threats and Mitigations:
  `https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/`
- OpenAI Agents SDK Guardrails:
  `https://openai.github.io/openai-agents-python/guardrails/`
- OpenAI Agents SDK Tracing:
  `https://openai.github.io/openai-agents-python/tracing/`
- MITRE ATLAS fact sheet / AI adversary knowledge base:
  `https://atlas.mitre.org/pdf-files/MITRE_ATLAS_Fact_Sheet.pdf`

Cross-check summary:

- NIST emphasizes lifecycle risk management and trustworthiness across design, development, deployment, use, and evaluation. Station alignment: doctrine files, contract gates, policy validators, receipts, and tests.
- OWASP agentic guidance emphasizes threats from autonomy, tool misuse, access control failures, memory/control-plane risks, and mitigations. Station alignment: deny-by-default tool surface, allowlists, external emitter gate, Discord allowlists, and audit ledger.
- OpenAI guardrails documentation emphasizes input/output/tool guardrails and tripwires, especially blocking guardrails before expensive or side-effectful execution. Station alignment: patch readiness, external emitter gate, contract validation, approval tokens, and preflight scripts.
- OpenAI tracing documentation emphasizes comprehensive workflow traces across LLM generations, tools, handoffs, guardrails, and custom events. Station alignment: runtime receipts, evidence ledger, audit health, task budgets, correlation logs, and sunrise receipts.
- MITRE ATLAS frames AI-enabled systems as having adversary tactics and techniques that should inform threat assessment and red-team thinking. Station alignment: explicit threat posture in governance docs, OpenClaw emitter gate, deny-by-default routing, and audit scripts.

Gap from external cross-check:

- Station has strong local checks, but there is no single committed "house inspector" command that runs this full bundle end-to-end and emits one signed/structured audit receipt. Current checks exist, but orchestration is manual.

Recommended follow-up: create `Scripts\station_integrity_audit.ps1` to run the full audit bundle, redact sensitive values, classify expected quarantine artifacts, emit `runtime/receipts/audit/station_integrity_audit__*.json`, and optionally write/update this report.

## Residual Risks

1. Dirty worktree is large and predates this audit.
   - The audit avoided reverting unrelated work.
   - Some changed/untracked files are outside the scoped fixes and need owner review before commit.

2. One governance signing receipt uses a UTF-8 BOM.
   - Parsed successfully with `utf-8-sig`.
   - Not modified because receipt/signing evidence should not be rewritten casually.

3. One malformed JSON artifact exists under quarantine.
   - Treated as expected because it is already under `governance/intents/quarantine/`.

4. Full runtime restart was required after these system-level edits.
   - Completed through `Scripts\station_patch_sunrise.ps1`.
   - Final sunrise receipt is `C:\Calyx_Terminal\runtime\receipts\sunrise_receipt__20260415_151031.json`.

5. External-source review was guidance-level, not a formal adversarial red-team exercise.
   - The local posture now better aligns with NIST/OWASP/OpenAI/MITRE controls, but true red-team validation remains future work.

## Integrity Conclusion

Station Calyx is stronger after this pass. The compendium authority is coherent, the private Discord ID file is protected from accidental commit, health/preflight checks execute correctly, runtime/service validation is green, and the unit test suite passes.

The main remaining structural improvement is to convert this manual inspection into a first-class governed audit command with its own receipt.
