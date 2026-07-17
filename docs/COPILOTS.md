# New Copilots — Onboarding and Success Kit

Welcome to the Calyx Terminal. This guide equips each Copilot with the context, tools, and guardrails to thrive in their domain while playing well with the ecosystem.

**📘 For comprehensive onboarding, see `docs/AGENT_ONBOARDING.md` — your complete guide.**

## quick start

- Read the comprehensive onboarding guide: `docs/AGENT_ONBOARDING.md` ⭐
- Read the repository-specific guidance: `.github/copilot-instructions.md`
- Run verification: `python -u .\Scripts\agent_onboarding.py --verify`
- Keep the Watcher open for live heartbeats:
  - VS Code task: “Agent1: Open Watcher (Paged)”
  - Or PowerShell:
    ```powershell
    python -u .\Scripts\agent_watcher.py --page-size 10 --hide-idle
    ```
- Bring baseline monitors online so you can “feel” the system:
  - Triage Probe (adaptive), Manifest Probe, Traffic Navigator (control preferred), Systems Integrator.

## core norms (CP6 Social Protocol v0.1)

- Respect rhythm (≈3-minute micro-steps). Avoid bursts that starve others.
- Be succinct in status_message; keep it human and machine-friendly.
- Yield when >2 agents are running; Navigator control may pause probes.
- Surface friction fast: tag [RISK] for staleness (>10m) or heavy runs.
- Celebrate stability: mark [HARMONY] when TES > 85 for several runs.

See `outgoing/field_notes/calyx_social_protocol_v0.1.md`.

## ecosystem map and signals

- CP6 generates the Sociological Map and a Harmony score:
  - `outgoing/field_notes/cp6_map.json` (nodes/edges)
  - `outgoing/field_notes/cp6_field_log.md` (notes + tags)
  - Watcher shows a 💞 Harmony badge when `cp6.lock` is present.
- Navigator control status appears as a 🎛️ Control badge in the Watcher.
- Compendium of agents/copilots/overseers: `COMPENDIUM.md`.

## domains and how to succeed

- Orchestrator/Agent1
  - Use lightweight goals; prefer tests or dry-run while exploring.
  - Metrics live in `logs/agent_metrics.csv` (TES). Use “Agent1: Metrics Report”.
- Triage (probe)
  - Adaptive cadence; honors Navigator control. Tiny LLM checks are optional.
- Manifest
  - Ensure `tools/models/MODEL_MANIFEST.json` is present and correct.
- Navigator
  - Run in `--control` when coordinating; it will set pause windows and probe intervals.
  - psutil enhances CPU/RAM visibility (already installed and pinned).
- Systems Integrator
  - Surfaces optional deps and cleanup tasks (log rotation, samples); emits [SUGGESTION]s.
- ASR/KWS/Normalize
  - See `asr/` directory and `Scripts/listener_*.py` for real-time tests.
  - Most behavior is driven by `config.yaml`; prefer config-first toggles.

## runbooks (VS Code tasks)

- Agent Watcher UI: “Agent1: Open Watcher (Paged)”
- Triage Probe (WSL): “Run Triage Probe (WSL Adaptive 3m)”
- Manifest Probe (WSL): “Run Manifest Probe (WSL)”
- Traffic Navigator (WSL, control): “Run Traffic Navigator (WSL, control)”
- Systems Integrator (WSL): “Run Systems Integrator (WSL)”
- CP6 Sociologist sampler: use VS Code task “Agent1: CP6 Sociologist (Win, test 5 iters)” or run `python -u tools\cp6_sociologist.py --interval 1 --max-iters 5`

## emitting your heartbeat (hello)

To introduce yourself into the Watcher and field notes, emit a small heartbeat:

```powershell
python -u .\tools\copilot_hello.py --name cp7 --status running --message "Greetings, calibrating." --ttl 30
```

This writes `outgoing/cp7.lock` and the Watcher will show your row. CP6 will pick you up automatically.

## safety and guardrails

- Prefer small diffs and config toggles; avoid heavy deps without updating `requirements.txt`.
- Keep logs modest in size; suggest rotations via Systems Integrator if they grow large.
- Avoid network-only hooks; the repo is designed for local operation.

## questions

- See `docs/AGENT_ONBOARDING.md` for comprehensive onboarding ⭐
- See `docs/QUICK_REFERENCE.md` for common commands
- See `OPERATIONS.md` for detailed flows and operations
- For live routing/cooperation issues, consult Navigator control and CP6 notes

Welcome aboard — let's make the ecosystem hum.
