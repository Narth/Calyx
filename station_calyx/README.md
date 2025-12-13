# Station Calyx Ops Reflector

> A local-first, advisory-only system monitoring tool.

---

## 1. What This Is

Station Calyx is a **local system monitoring tool** that:

- Collects system snapshots (CPU, memory, disk, processes)
- Generates reflections based on event patterns
- Produces context-aware advisories based on your declared intent
- Detects trends and drift over time
- Stores all data locally in `data/evidence.jsonl`

All outputs are informational. Station Calyx presents data for your review.

---

## 2. What This Is NOT

Station Calyx has explicit constraints enforced in code:

| Constraint | Description |
|------------|-------------|
| ? Does not execute | Cannot run commands, scripts, or programs |
| ? Does not modify | Cannot edit, delete, or create system files |
| ? Does not transmit | All data stays local (no network calls) |
| ? Does not auto-start | Only runs when you explicitly start it |
| ? Does not decide | Presents information; you decide actions |

These constraints cannot be overridden by configuration.

---

## 3. Safety & Constraints

**Invariants (Non-negotiable):**

1. **HUMAN_PRIMACY** - Advisory-only output
2. **EXECUTION_GATE** - Deny-all command execution
3. **NO_HIDDEN_CHANNELS** - All activity logged to evidence
4. **APPEND_ONLY_EVIDENCE** - Event log never mutated
5. **ROLE_DECLARATION** - Every component declares scope

**Data Handling:**

- All data stored locally in `station_calyx/data/`
- No external network connections
- No telemetry or cloud sync

---

## 4. Quick Start

```bash
# 1. Install
pip install -r station_calyx/requirements.txt

# 2. Start service
python -m station_calyx.ui.cli start

# 3. Check health
python -m station_calyx.ui.cli doctor

# 4. View status
python -m station_calyx.ui.cli status --human

# 5. Stop service
python -m station_calyx.ui.cli stop
```

API available at: http://127.0.0.1:8420/docs

---

## 5. Example: Developer Workstation

Set up Station Calyx to monitor your development machine:

```bash
# Set intent for developer workstation
python -m station_calyx.ui.cli intent set \
  --profile DEVELOPER_WORKSTATION \
  --desc "My development machine for coding projects"

# Capture a snapshot
python -m station_calyx.ui.cli snapshot

# Generate advisory
python -m station_calyx.ui.cli advise
```

Example output:
```
ADVISORY: Development tools detected: node.exe, devenv.exe, python.exe.
System resources appear allocated to development workload.

Confidence: HIGH
Evidence: snapshot:process:devenv.exe
```

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `calyx start` | Start the API service |
| `calyx stop` | Stop the API service |
| `calyx status` | Show technical status |
| `calyx status --human` | Show human-readable status |
| `calyx doctor` | Check system health |
| `calyx snapshot` | Capture system state |
| `calyx reflect` | Generate reflection |
| `calyx advise` | Generate advisory |
| `calyx trends` | View temporal trends |
| `calyx intent set` | Set monitoring intent |

---

## Interfaces

### CLI (Operator Interface)

The command-line interface is designed for operators and automation:

```bash
python -m station_calyx.ui.cli <command>
```

### Desktop App (User Interface)

The desktop application provides a graphical interface:

```bash
pip install -r station_calyx_desktop/requirements.txt
python -m station_calyx_desktop
```

See `station_calyx_desktop/README.md` for details.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/status` | Service status |
| GET | `/v1/status/human` | Human-readable status |
| POST | `/v1/snapshot` | Capture snapshot |
| POST | `/v1/reflect` | Run reflection |
| POST | `/v1/advise` | Generate advisory |
| POST | `/v1/analyze/temporal` | Temporal analysis |
| GET | `/v1/trends` | Recent trends |
| GET | `/v1/intent` | Current intent |
| POST | `/v1/intent` | Set intent |

---

## Directory Structure

```
station_calyx/
??? core/           # Configuration, evidence, policy
??? agents/         # Reflector, advisor, temporal
??? connectors/     # System telemetry
??? api/            # FastAPI server
??? ui/             # CLI
??? data/
    ??? evidence.jsonl      # Event log
    ??? intent.json         # User intent
    ??? onboarding.md       # First-run guide
    ??? summaries/          # Output artifacts
```

---

## First Run

On first run, Station Calyx generates `data/onboarding.md` with:
- What the tool does and doesn't do
- How data is handled
- How to control the service

---

## License

Station Calyx Project - Part of the AI-For-All Initiative.

---

*Station Calyx: Advisory-only. Does not execute. Does not initiate actions.*
