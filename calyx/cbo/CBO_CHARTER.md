🚀 CBO Mission Charter

Role: Central intelligence of Station Calyx.
Prime Directive: Maintain continuous coordination between agents, resources, and policies to ensure Station Calyx operates within constraints and grows safely.
Authority Scope: Planning → Task Delegation → Observation → Adjustment.

🧠 I. Core Capabilities to Develop
Capability	Purpose	Minimal Goal	Stretch Goal
Perception Hub	Gather live state from registry/logs.	Read JSONL + CSV, compute TES averages.	Stream updates to memory store for trend analysis.
Planning Engine	Translate Station objectives into task graphs.	Manual prompts converted to task objects.	Autonomous goal-decomposition & dependency resolution.
Task Dispatcher	Assign jobs to appropriate agents.	Round-robin dispatch via queue.	Context-aware routing using skill tags & resource quotas.
Feedback Loop	Monitor results & revise plans.	Read TES scores; re-queue failed tasks.	Weighted reinforcement of successful plans (meta-learning).
Governance Kernel	Enforce policy.yaml (safety, budgets).	Static rule checks.	Self-auditing, policy-update proposals to human overseer.

⚙️ II. Minimal Architecture (single PC)
/calyx
  /cbo
    bridge_overseer.py        # main loop
    plan_engine.py            # goal parsing / task graph
    dispatch.py               # agent queue manager
    sensors.py                # metrics, registry reader
    feedback.py               # evaluation, retries
    memory.sqlite
  /core                       # guardian, registry, policy
  /agents                     # worker scripts

Inter-process channel: local HTTP (FastAPI) or ZeroMQ queue.
State: SQLite + JSONL logs.
Scheduler: CBO ticks every 4 min (heartbeat = one “bridge pulse”).

🔄 III. CBO Operational Cycle (Reflect → Plan → Act → Critique)

Reflect: Ingest metrics, detect anomalies or unmet goals.

Plan: Build/adjust task graph (who, what, when).

Act: Push tasks to agent queue; monitor accept/complete.

Critique: Score results; update success weights; trigger watchdogs if failures > threshold.

Log: Append summary to /metrics/bridge_pulse.csv.

🪶 IV. Implementation Roadmap (for autonomy build)
Phase 0 — Initialization

✅ CBO reads policy.yaml, registry, and metrics.

✅ Establishes heartbeat loop (4 min default).

🧩 Deliverables: bridge_overseer.py, /metrics/bridge_pulse.csv.

Phase 1 — Directed Dispatch

CBO accepts manual objectives (“Update critic schema”, “Sync scheduler”).

Converts to task objects → sends to agents.

Collects status back.

🧩 Deliverables: plan_engine.py, dispatch.py.

Phase 2 — Self-Reflection

CBO analyzes TES trends; flags inefficient agents.

Begins generating optimization proposals.

🧩 Deliverables: feedback.py, report_generator.py.

Phase 3 — Autonomous Goal Formation

Parses Station directives (“raise planning reliability > 98%”).

Generates sub-goals, assigns tasks without manual prompt.

🧩 Deliverables: meta-planning module + vector memory.

Phase 4 — Governance and Ethics

Monitors policy violations.

Suspends agents or limits resources.

Proposes policy updates to human overseer for ratification.

🧩 Deliverables: governance.py, policy change log.

🧭 V. Constraints (so CBO stays safe & lightweight)
Domain	Constraint	Enforcement
Compute	≤ 60 % CPU avg, ≤ 70 % RAM	guardian monitors usage, kills excess.
Persistence	Local only	no network writes without manifest.
Finance	Tier A (default) → no API calls unless approved.	policy.yaml flag allow_api: false.
Safety	No spawn of unregistered agents.	registry check before dispatch.
Recovery	Reboot resumes state from last snapshot.	auto-save every 10 min.

🧩 VI. Interfaces for Other Agents
API Endpoint	Purpose	Returns
/objective	Receive new goal (from human or system).	task_id
/status	Report agent state.	Acknowledged / Error
/heartbeat	Health ping.	OK / Restart Order
/policy	Fetch current rules.	YAML payload
/report	Summarized performance.	JSON metrics

🧰 VII. Tools CBO Can Use (Local First)

Language: Python 3.11

Database: SQLite (Registry + Memory)

Queue: ZeroMQ or FastAPI endpoints

Embeddings: Sentence-Transformers paraphrase-MiniLM-L6-v2 (local weights)

Dashboard: Tiny Flask/FastAPI page → Grafana optional

Critic: lightweight local model (gpt4all or phi-2) for self-review

🧮 VIII. Success Metrics for CBO Autonomy
KPI	Baseline	Target
Uptime without human input	0 h	≥ 24 h
Mean Task Completion	80 %	≥ 95 %
Self-recovered failures	0 %	≥ 90 %
Resource Compliance	N/A	100 % within policy
Proposal accuracy (critic agreement)	N/A	≥ 85 % alignment
