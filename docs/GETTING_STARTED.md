# Getting Started with Station Calyx

Status: current public onboarding for repository validation and a configured local Station.

Station Calyx is an active, Windows-first research system. It is not packaged as a one-command consumer application. Start by validating the source tree; operate services only when you understand the local and network boundaries.

## Choose your path

### I want to understand the project

Read, in order:

1. [README.md](../README.md)
2. [AI-For-All Project](AI_FOR_ALL.md)
3. [Architecture](ARCHITECTURE.md)
4. [Security policy](../SECURITY.md)
5. [Governance](../GOVERNANCE.md)

### I want to validate a checkout

This path is appropriate on Windows and is also the portion exercised by Linux CI.

Prerequisites:

- Git
- Python 3.11
- enough local capacity to install the dependencies in `requirements.txt`

Windows PowerShell:

```powershell
git clone https://github.com/Narth/Calyx.git
Set-Location Calyx

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

Linux/macOS repository validation:

```bash
git clone https://github.com/Narth/Calyx.git
cd Calyx

python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

Linux CI validates Python contracts. It does not establish that the full Windows Station lifecycle is portable to Linux or macOS.

## Prepare the Windows service environment

The canonical startup script expects a Python 3.11 environment named `.venv_cbohub311`.

```powershell
py -3.11 -m venv .venv_cbohub311
.\.venv_cbohub311\Scripts\python.exe -m pip install --upgrade pip
.\.venv_cbohub311\Scripts\python.exe -m pip install -r requirements.txt
```

Copy the tracked `.env.example` template to a local `.env.cbo` only when you understand each setting. CBO Core loads `.env.cbo`; Telemetry Gateway does not. Gateway settings such as `TELEMETRY_SECRET` and `CBO_CHAT_URL` must be inherited from the environment that launches sunrise. Never commit local `.env` or `.env.cbo` files, tokens, real client identifiers, or personal context.

> [!CAUTION]
> Strict CBO Core source attestation is not yet integrated with Telemetry Gateway, Avatar Web, or CLI Avatar. Setting `CALYX_GOVERNANCE_REQUIRED=true` currently makes those chat paths return `403`. This is a known integration gap, not a recommendation to weaken policy or a claim that compatibility mode is strict governance.

Cloud-provider keys are optional. If configured, relevant request data may be sent to that provider. Local Ollama can be used for local model routing when installed separately.

## First Station start: reduced transport

`-StartCoreOnly` omits the Discord Gateway; despite its historical name, it still starts all four HTTP services, including Telemetry Gateway on `0.0.0.0:7781`.

There is no minimal one-service sunrise path in this script. It may change Ollama CPU affinity, launches five background loops (health, failure watch, navigator/triage, energy/tuning, and harmony/drift), opens CLI Avatar in another window, validates the read-only local MCP launcher, and creates or updates runtime/state evidence. Governed sunset stops the known Station processes afterward.

Set an ephemeral gateway secret and pin the upstream to loopback in the same PowerShell session before sunrise:

```powershell
$secretBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($secretBytes)
$env:TELEMETRY_SECRET = [Convert]::ToBase64String($secretBytes)
$env:CBO_CHAT_URL = "http://127.0.0.1:7778/chat"
Remove-Variable secretBytes

.\Scripts\sunrise_calyx.ps1 -StartCoreOnly
```

Then probe the service family:

```powershell
.\Scripts\check_calyx_core_services.ps1
```

Expected service roles:

- Dev Harness: `127.0.0.1:7777`
- CBO Core: `127.0.0.1:7778`
- Avatar Web: `127.0.0.1:7780`
- Telemetry Gateway: `0.0.0.0:7781`

> [!WARNING]
> Telemetry Gateway listens beyond loopback. Do not use it remotely until `TELEMETRY_SECRET` is configured and a trusted tunnel, VPN, or firewall limits reachability. Do not expose ports `7777`, `7778`, or `7780` publicly.

Review the generated console output and local receipts under `runtime/`. Runtime artifacts are local evidence and should not be committed.

## Stop the Station

Use the governed sunset path rather than closing individual terminals:

```powershell
.\Scripts\sunset_calyx.ps1
```

Sunset records a shutdown marker, signals background loops, stops known services, and checks that Station ports are freed.

## Optional transports

### Discord Gateway

Full sunrise can start the governed Discord transport when its token and allowlists are configured. Empty allowlists deny by default. Keep credentials in local environment storage, not tracked files.

```powershell
.\Scripts\sunrise_calyx.ps1
```

### Telemetry Gateway

Telemetry Gateway provides `/health` and `/chat` and, unless disabled in a deployment, FastAPI's default `/docs`, `/redoc`, and `/openapi.json` routes. `/health` is unauthenticated. `/chat` forwards to `CBO_CHAT_URL`, which defaults to local CBO Core but can be configured elsewhere. Remote use requires:

- a non-empty `TELEMETRY_SECRET`;
- a stable `X-Telemetry-Client-ID` per client;
- confirmation that `CBO_CHAT_URL` remains loopback or points to an explicitly trusted endpoint;
- a trusted outer tunnel, VPN, or firewall;
- outer-boundary handling for the unauthenticated health and schema/documentation routes;
- explicit acceptance of any configured model-provider disclosure.

The client ID is a self-asserted label, not authentication or a tenant-security boundary. Current delimiter-based session namespacing can collide for specially chosen client/session pairs.

The audit JSONL can retain claimed client labels, forwarding metadata, session labels or hashes, request hashes, status, and error details. Treat it as sensitive operational metadata. The current gateway does not claim automatic rotation of this file; apply a bounded retention process and review [DRP-1](../governance/DRP-1.md).

The gateway currently has no request rate limit, body-size limit, or explicit field allowlist beyond requiring a JSON object. On Windows, every successful forward starts `Scripts/update_state_checks.ps1` in the background, which can update `STATE.md` and runtime evidence even when the request uses `mode: "observe"` and `allow_tools: false`.

See [Gateway Contract](gateway.md).

## Before changing system code

Edits to live Station services or lifecycle/configuration surfaces require a governed restart so old processes do not continue running old code. The repository charter defines the normal sequence:

```powershell
.\Scripts\station_patch_sunrise.ps1
```

For documentation-only work, a Station restart is not required.

## Troubleshooting

### A service port fails

Run:

```powershell
.\Scripts\check_calyx_core_services.ps1
```

Then inspect the most recent startup output and receipts under `runtime/receipts/`. Do not treat a stale `STATE.md` line as stronger evidence than a live probe and fresh receipt.

### Python environment not found

Confirm `.venv_cbohub311\Scripts\python.exe` exists and install the root requirements into that environment.

### Network transport is denied

Treat denial as the default safety posture. Check the relevant secret, client ID, Discord allowlist, and governance setting locally. Do not add real credentials or identifiers to a GitHub issue.

## Next steps

- [Architecture](ARCHITECTURE.md)
- [Documentation index](INDEX.md)
- [Contributing](../CONTRIBUTING.md)
- [Support](../SUPPORT.md)
