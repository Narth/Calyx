# Public-Release Readiness Audit — Station Calyx / BloomOS

_Date:_ 2026-02-11  
_Auditor:_ Codex (adversarial review)

## 0) Repository Map & Entry Points (produced first per request)

### High-level map
- Root appears to be a mixed monorepo (research artifacts + runtime code + tools + dashboards + telemetry dumps).
- Runtime/security-relevant directories:
  - `station_calyx/` (FastAPI service, evidence store, ingestion, governance logic)
  - `dashboard/backend/` (Flask backend with write-capable endpoints)
  - `tools/` (automation and execution-adjacent scripts)
  - `telemetry/`, `exports/`, `station_calyx/data/` (tracked runtime data artifacts)
  - `governance/`, `security/`, `docs/` (policy and docs)

### Runtime entry points

#### API servers / web surfaces
1. **FastAPI: Station Calyx API**
   - Entrypoint: `station_calyx/api/server.py`
   - Run modes: `python -m uvicorn station_calyx.api.server:app` and `run_server()` helper. (`station_calyx/api/server.py:92-100`, `192-199`)
   - Network scope: default local (`127.0.0.1`), but host can be overridden by caller in `run_server(host=...)` and in service launcher. (`station_calyx/api/server.py:192-195`, `station_calyx/core/service.py:175-185`)

2. **Flask: Dashboard backend**
   - Entrypoint: `dashboard/backend/main.py`
   - Starts with `app.run(host='127.0.0.1', port=8080, debug=True)`. (`dashboard/backend/main.py:181-184`)
   - CORS enabled globally with defaults (`CORS(app)`) and no per-route auth gates. (`dashboard/backend/main.py:17`)

#### CLI / service control
- `station_calyx/ui/cli.py` — command surface including service start/stop and governance operations. (`station_calyx/ui/cli.py`)
- `station_calyx/core/service.py` — background process spawn / PID handling (`subprocess.Popen`, `taskkill`). (`station_calyx/core/service.py:175-205`, `254-263`)
- `calyx_comm_cli.py`, `calyx.py`, `crb_runtime_bridge.py` — additional root-level CLIs.

### Network-exposed HTTP surfaces (identified)

#### FastAPI (`/v1/*`)
From `station_calyx/api/routes.py`:
- Read-like endpoints: `/status`, `/health`, `/intent` (GET), `/trends`, `/status/human`, `/assess`, `/notifications/recent`, `/nodes`, `/nodes/{node_id}/evidence`.
- Write/compute endpoints: `/ingest`, `/snapshot`, `/reflect`, `/intent` (POST), `/advise`, `/analyze/temporal`, `/ingest/evidence`.
- Only `/ingest/evidence` includes token-based auth logic; other routes are unauthenticated. (`station_calyx/api/routes.py:742-795`)

#### Flask dashboard (`/api/*`)
From `dashboard/backend/main.py`:
- Read-like routes: `/api/health/*`, `/api/analytics/*`, `/api/agents/*`, `/api/leases/*`, `/api/approvals/pending`, `/api/chat/history`, `/api/chat/agent-responses`, `/api/chat/receipts/<msg_id>`.
- Action routes (side effects):
  - `POST /api/leases/<lease_id>/approve`
  - `POST /api/approvals/<approval_id>/approve`
  - `POST /api/approvals/<approval_id>/reject`
  - `POST /api/chat/broadcast`
  - `POST /api/chat/direct`
- No request auth enforcement in route handlers. (`dashboard/backend/main.py:95-166`)

---

## 1) Executive Summary

- **Overall risk rating:** **CRITICAL**
- **Public release recommendation:** **NO-GO** (current state is unsafe for internet/public use)

### Why NO-GO
1. Sensitive runtime/user telemetry and evidence artifacts are committed to git (`station_calyx/data/evidence.jsonl`, `telemetry/*`, `exports/*`), including sender identifiers and message previews. (`station_calyx/data/evidence.jsonl:6-7`, `.gitignore:52-66`)
2. `.gitignore` is malformed at line 1, causing ignore semantics/tooling breakage and materially increasing accidental secret/data commits risk. (`.gitignore:1`)
3. Flask dashboard has mutating endpoints with no authentication and placeholder auth that always returns success. (`dashboard/backend/main.py:95-166`, `dashboard/backend/auth.py:25`, `37`)
4. FastAPI global exception handler returns raw exception strings to clients (potential info leak). (`station_calyx/api/server.py:145-148`)
5. Ingest token comparison is plain string compare, and local bypass exists when token absent (safe only if local-only is enforced operationally). (`station_calyx/api/routes.py:693-699`, `712-713`)
6. Global permissive CORS in dashboard and permissive CORS pattern in FastAPI raise browser-abuse exposure if host binding is widened. (`dashboard/backend/main.py:17`, `station_calyx/api/server.py:103-108`)

### Top 10 must-fix items
1. **CRITICAL** — Remove committed runtime data/evidence/telemetry from repo and history (`station_calyx/data/evidence.jsonl`, `telemetry/`, `exports/`). Rationale: privacy leakage and deanonymization risk.
2. **CRITICAL** — Fix `.gitignore` syntax and enforce denylist for runtime artifacts/secrets. Rationale: current ignore file is effectively unreliable.
3. **CRITICAL** — Implement real authN/authZ on dashboard write endpoints; currently effectively unauthenticated action surface.
4. **CRITICAL** — Disable Flask debug mode by default in all non-dev execution paths.
5. **HIGH** — Remove raw exception string from FastAPI client responses.
6. **HIGH** — Require token for all non-loopback ingest regardless of deployment mode; use constant-time compare.
7. **HIGH** — Add rate-limits and abuse controls on `/v1/ingest/evidence` and dashboard messaging endpoints.
8. **HIGH** — Split repository: code vs generated runtime artifacts; enforce artifact storage outside git.
9. **MED** — Pin dependencies with lockfiles and add SBOM generation.
10. **MED** — Add SECURITY.md, CONTRIBUTING.md, and secure deployment docs.

---

## 2) Sensitive Data & Privacy Audit (CRITICAL)

### Confirmed sensitive artifact exposure in tracked files
- Evidence log with message metadata and sender identifiers is tracked:
  - `station_calyx/data/evidence.jsonl` contains sender IDs and message previews. (`station_calyx/data/evidence.jsonl:6-7`, `17`)
- Export bundles are tracked in `exports/` and `station_calyx/data/exports/` (evidence payloads committed over time).
- Large telemetry directories with operational snapshots and environmental fingerprints are tracked (`telemetry/energy/*`, `telemetry/network/*`, etc.) per git index listing.

### “Should never be in git” patterns (and `.gitignore` implications)
Current `.gitignore` intends to ignore logs/runtime dirs, but malformed first line likely breaks parsing in tools and can break trust in ignores. (`.gitignore:1`)

Must-ignore patterns for public release:
- `station_calyx/data/**`
- `telemetry/**`
- `exports/**`
- `outgoing/**`, `incoming/**`, `responses/**`
- `**/*.jsonl` under runtime evidence/log paths
- audio/screenshot/transcript artifacts (`*.wav`, `*.mp3`, `*.png` runtime captures)
- `.env*`, `keys/**`, `*.pem`, `*.key`

### Secrets scan observations
- No hardcoded production secrets were directly found in sampled code/docs, but auth placeholders and token examples exist.
- Because `.gitignore` is malformed and large data files are tracked, **secret spillage probability is high** over time.

### Accidental logging risks
- FastAPI logs request method/path; exception handler logs full exception details and returns exception text to clients. (`station_calyx/api/server.py:121-125`, `128-148`)
- Evidence model stores raw `payload` and summaries from ingest endpoints, including user-provided fields. (`station_calyx/core/evidence.py:18-22`)
- Ingest audit stores `remote_addr` and `node_id` in append-only logs (PII/operator metadata). (`station_calyx/evidence/audit.py:65-75`)

### Safe logging mode (recommended default spec)
1. **Default = privacy-preserving mode ON** in production/public builds.
2. Store only:
   - event type, coarse timestamps, bounded status codes
   - hashed/pseudonymous actor IDs
3. Never store raw user text, prompts, message bodies, bearer tokens, IPs in default logs.
4. Redaction pipeline before persist:
   - remove auth headers/tokens
   - mask IDs (`sha256(id+salt)[:10]`)
   - truncate all free text to safe preview with explicit opt-in override.
5. Separate debug logs gated by explicit local env var and auto-expiry rotation.

---

## 3) Git History Risk

### What is analyzable here
- Git history is accessible and shows repeated commits of runtime data artifacts, including evidence and telemetry files.
- `git log --name-only` confirms multiple commits touching `station_calyx/data/evidence.jsonl`, `exports/evidence_bundle_*`, and `telemetry/**`.

### Risk conclusion
- **High probability that sensitive runtime artifacts already exist throughout history.**
- Recommend **history rewrite before public open** if any personal/sensitive data was included.

### Recommended maintainer actions
1. Run targeted history scan locally:
   - `git log --name-only --pretty=format: | rg 'evidence|telemetry|exports|outgoing|incoming|\.env|key|token'`
2. Run deep secret scanners on full history:
   - `gitleaks detect --source . --no-git` and `gitleaks detect --source .`
   - optionally `trufflehog git file://.`
3. If sensitive data confirmed:
   - rewrite history (`git filter-repo` / BFG)
   - rotate any potentially exposed credentials
   - force-push + invalidate stale clones per incident playbook

---

## 4) Endpoint & External Call Safety

## FastAPI endpoint review (`station_calyx/api/routes.py`)
- **Unauthenticated by default:** most routes have no auth requirement.
- `/v1/ingest/evidence` has auth logic, but:
  - token optional if local (`local_bypass`) (`693-699`)
  - no constant-time compare (`712-713`)
  - no replay protection/nonces
  - no explicit rate-limits
- Side effects:
  - `/ingest` writes evidence log
  - `/snapshot` collects system telemetry and writes event
  - `/reflect`, `/advise`, `/analyze/temporal` produce and save artifacts
  - `/ingest/evidence` writes per-node evidence + audit logs

## Flask dashboard endpoint review (`dashboard/backend/main.py`)
- No auth checks on route handlers.
- `POST /api/approvals/<id>/approve` mutates lease files by appending human cosignature. (`dashboard/backend/api/approvals.py:76-96`)
- `POST /api/chat/broadcast` and `/api/chat/direct` invoke messaging core and persist communications artifacts. (`dashboard/backend/api/chat.py:64-97`, `183-214`)
- `CORS(app)` with default open behavior increases browser-origin abuse risk if network-exposed. (`dashboard/backend/main.py:17`)

### CSRF / abuse control
- No CSRF protections observed for mutating Flask routes.
- No per-endpoint rate limiting detected.
- No anti-replay controls for ingest token flow.

---

## 5) Governance Integrity & Bypass Search

### Core governance gates
- Policy gate denies execution (`deny-all`) in station API policy module. (`station_calyx/core/policy.py:31-43`)
- Station API describes advisory-only invariants. (`station_calyx/api/server.py:183-187`)

### Bypass vectors found
1. **Dashboard auth placeholder always-true** — bypasses any intended signature validation.
   - `verify_signature()` returns `True`. (`dashboard/backend/auth.py:25`)
   - `authenticate_request()` returns `(True, "user1")`. (`dashboard/backend/auth.py:37`)
   - Severity: **CRITICAL**

2. **Dashboard write endpoints don’t call auth gate**
   - Direct file-mutation/message routes without auth middleware. (`dashboard/backend/main.py:95-166`)
   - Severity: **CRITICAL**

3. **Flask debug mode enabled**
   - `debug=True` at startup. (`dashboard/backend/main.py:184`)
   - Severity: **HIGH**

4. **Potential host bind widening via service controls**
   - `start_service(... host: str)` accepts arbitrary host; can run on `0.0.0.0` if invoked that way. (`station_calyx/core/service.py:116-119`, `175-185`)
   - Severity: **MED/HIGH** (operational misuse risk)

5. **Exception detail disclosure**
   - returns `{"error": str(exc)}` to caller. (`station_calyx/api/server.py:145-148`)
   - Severity: **HIGH**

No obvious command injection (`shell=True`) observed in audited web handlers, but subprocess use exists in service/TUI modules and should remain unreachable from unauthenticated remote routes.

---

## 6) Dependency & Supply Chain Checks

### Ecosystems observed
- Python (root + `station_calyx` + `dashboard` + many tools)
- Small Node packages under `skills/*`

### Findings
- Requirements mostly use loose minimum specifiers (`>=`) without lockfiles:
  - root `requirements.txt` (`fastapi>=0.109`, `uvicorn>=0.23`).
  - `station_calyx/requirements.txt`, `dashboard/requirements.txt` similar.
- No repo-wide lockfile strategy observed.
- No SBOM artifacts observed.

### Recommendations
- Generate lockfiles per deployable component.
- Add CI checks for dependency vulnerabilities (pip-audit, osv-scanner, npm audit where relevant).
- Produce SBOM (CycloneDX/SPDX) per release.

---

## 7) Operational Stability

### Brittle assumptions / unsafe defaults
- Flask backend starts in debug mode (unsafe default). (`dashboard/backend/main.py:184`)
- Runtime data directories are tracked in git, coupling operation to source control state.

### Concurrency / race risks
- JSONL append without locking in evidence/comms paths can race under concurrent writers. (`station_calyx/core/evidence.py:24-29`, `tools/svf_comms_core.py:141-150`, `177-186`)
- Receipt updates rewrite full file without lock (`update_receipt`). (`tools/svf_comms_core.py:190-252`)

### Error handling issues
- Broad `except Exception` patterns suppress failures and can hide corruption paths.
- Client-visible raw exception strings in FastAPI.
- `dashboard/backend/api/chat.py` currently fails bytecode compilation due to indentation mismatch (`IndentationError` at line 38), indicating an unstable backend module for public release.

### Test coverage gaps (governance-critical)
- Existing tests focus on evidence envelope/hash-chain; no clear tests for:
  - authN/authZ enforcement on HTTP endpoints
  - deny-by-default endpoint access
  - CSRF/rate-limit behavior
  - logging redaction

---

## 8) Public Repo Hygiene

### Presence check
- Present: `README.md`, `LICENSE`.
- Missing: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.

### Documentation quality concerns
- README references runtime log/output paths (`logs/`, `outgoing/`) as normal workflow and doesn’t clearly separate publishable code from private runtime data. (`README.md:65-67`, `89-90`)
- Public safety model (what endpoints do/do not do, deployment hardening defaults) is not yet documented as a formal public contract.

### Tailored Public Release Checklist
1. Purge runtime artifacts from git + history.
2. Repair `.gitignore`; verify with test commit simulation.
3. Add SECURITY.md with vulnerability reporting and supported versions.
4. Add deployment hardening guide: bind-local, reverse proxy auth, TLS, firewall defaults.
5. Enforce auth on every mutating endpoint.
6. Disable debug mode and sensitive error disclosures.
7. Add rate limits / abuse controls.
8. Add CI secret scanning + dependency scanning + policy tests.
9. Create public threat model doc for endpoint misuse scenarios.
10. Tag first public release only after red-team checklist passes.

---

## 9) Remediation Plan (Prioritized)

### CRITICAL
1. **Remove sensitive tracked runtime data + rewrite history if needed**
   - Files/areas: `station_calyx/data/evidence.jsonl`, `station_calyx/data/exports/*`, `exports/*`, `telemetry/**`
   - Patch approach: move runtime outputs to non-repo storage; commit only schemas/examples.
   - Verify: `git ls-files | rg 'telemetry|evidence\.jsonl|exports/'` returns only sanitized fixtures.

2. **Fix `.gitignore` and enforce runtime-deny patterns**
   - File: `.gitignore:1`
   - Patch approach: correct malformed first line and add strict runtime/sensitive patterns.
   - Verify: `git check-ignore -v <sample-runtime-file>` shows expected ignore matches.

3. **Implement real dashboard auth and authorization middleware**
   - Files: `dashboard/backend/auth.py`, `dashboard/backend/main.py`
   - Patch approach: mandatory signed/JWT auth for all `/api/*`; role checks for approve/reject/direct message routes.
   - Verify: unauthenticated POSTs return 401/403; integration tests for role matrix.

4. **Remove always-true auth stubs**
   - File: `dashboard/backend/auth.py:25`, `37`
   - Patch approach: either implement or hard-fail (`NotImplementedError`) in non-dev mode.
   - Verify: startup/test ensures no placeholder auth in production profile.

### HIGH
5. **Disable Flask debug in default path**
   - File: `dashboard/backend/main.py:184`
   - Patch approach: `debug` from env default false; refuse true unless explicit local-dev flag.
   - Verify: process logs confirm debug off in production profile.

6. **Stop returning raw exception text to clients**
   - File: `station_calyx/api/server.py:145-148`
   - Patch approach: generic client error body + internal correlation ID.
   - Verify: induced exception response omits stack/message details.

7. **Harden ingest auth/token handling**
   - File: `station_calyx/api/routes.py:693-715`
   - Patch approach: require token whenever route reachable over network; use constant-time compare; add nonce/timestamp signature.
   - Verify: replay attempts fail; invalid token timing not distinguishable in basic test.

8. **Add rate limiting and abuse controls**
   - Files: FastAPI and Flask route layers
   - Patch approach: per-IP/user limits, payload budgets, and backoff.
   - Verify: repeated burst requests trigger 429 and audit entries.

### MED
9. **Dependency locking + SBOM**
   - Files: `requirements.txt`, `station_calyx/requirements.txt`, `dashboard/requirements.txt`
   - Patch approach: lockfiles, pip-audit in CI, SBOM generation at release.
   - Verify: CI pipeline fails on vulnerable/unpinned policy violations.

10. **Public repo governance docs**
   - Add: `SECURITY.md`, `CONTRIBUTING.md`, optionally `CODE_OF_CONDUCT.md`
   - Verify: files present, linked in README, and include responsible disclosure workflow.

---

## 10) Minimal “Safe-to-Open” Baseline

Smallest acceptable pre-public set:
1. Repair `.gitignore` and remove all runtime artifacts from git (plus history rewrite if sensitive content found).
2. Disable dashboard debug mode and block all write endpoints behind real auth.
3. Remove raw exception leakage from API responses.
4. Add SECURITY.md + explicit “safe deployment defaults” doc.
5. Add basic rate-limiting on ingest and action endpoints.

---

## Final Go/No-Go

**NO-GO for public release in current state.**

Primary blockers are privacy leakage via tracked runtime data, broken ignore protections, and unauthenticated action-capable HTTP routes.
