# Remote Public Readiness Audit (Verified Attempt)

- Repository target: `https://github.com/Narth/Calyx`
- Audit date (UTC): 2026-02-12
- Auditor context: fresh container, direct remote access attempted

## 1) Remote default branch visibility (`main`)

### Result
**Not retrievable from this environment** due outbound tunnel blocking.

### Direct access attempts
1. `git ls-remote --symref https://github.com/Narth/Calyx`
   - Error: `fatal: unable to access 'https://github.com/Narth/Calyx/': CONNECT tunnel failed, response 403`
2. `git clone --mirror https://github.com/Narth/Calyx /tmp/calyx_remote_audit_<ts>`
   - Error: `fatal: unable to access 'https://github.com/Narth/Calyx/': CONNECT tunnel failed, response 403`

## 2) Forbidden artifact scan (remote tree)

The following forbidden paths/patterns were requested:

- `telemetry/`
- `exports/`
- `station_calyx/data/`
- `outgoing/`
- `incoming/`
- `responses/`
- `runtime/`
- `logs/`
- `keys/`
- `state/`
- `memory/`
- `staging/`
- media captures (`*.wav`, `*.mp3`, `*.m4a`, `*.png`, `*.jpg`, `*.jpeg`)
- CBO runtime JSONLs previously identified

### Status
**UNVERIFIED (remote inaccessible).**

No authoritative remote tree traversal could be completed from this environment.

## 3) Required file presence/content checks

Required files:

- `.github/workflows/public-repo-hygiene.yml`
- `tools/check_forbidden_tracked_paths.sh`
- `README.md`
- `docs/gateway.md`

### Status
**UNVERIFIED (remote inaccessible).**

## 4) Remote branches/tags and sensitive-history check

### Result
**UNVERIFIED (remote inaccessible).**

Attempted method:
- `git ls-remote --heads --tags https://github.com/Narth/Calyx`

Observed error:
- `fatal: unable to access 'https://github.com/Narth/Calyx/': CONNECT tunnel failed, response 403`

## 5) Secret/sensitive string detection (README/config)

### Result
**UNVERIFIED (remote inaccessible).**

Unable to fetch README or config files for remote scanning.

## 6) Proxy fallback attempt (GitHub API v3)

Attempted:
- `curl -i -sS https://api.github.com/repos/Narth/Calyx`
- `curl -i -sS https://raw.githubusercontent.com/Narth/Calyx/main/README.md`

Observed error (both):
- `curl: (56) CONNECT tunnel failed, response 403`
- HTTP response:
  - `HTTP/1.1 403 Forbidden`
  - `server: envoy`
  - `content-type: text/plain`

## 7) Go/No-Go recommendation

## **NO-GO (cannot verify public safety posture)**

Rationale:
- Remote repository content, branch history, and tag history could not be accessed.
- Forbidden artifact checks and governance-file confirmations remain unverified.
- Inability to perform minimum visibility and hygiene controls check means publication readiness cannot be responsibly attested.

## 8) What to run in a network-allowed environment

Run the following from a host with outbound GitHub HTTPS access:

1. `git ls-remote --symref --heads --tags https://github.com/Narth/Calyx`
2. `git clone --mirror https://github.com/Narth/Calyx /tmp/calyx_remote_audit`
3. Enumerate default branch tree and run forbidden-path/media scans across all refs.
4. Confirm existence/content of:
   - `.github/workflows/public-repo-hygiene.yml`
   - `tools/check_forbidden_tracked_paths.sh`
   - `README.md`
   - `docs/gateway.md`
5. Perform secret scanning on README + config files for leaked tokens/keys/endpoints.

