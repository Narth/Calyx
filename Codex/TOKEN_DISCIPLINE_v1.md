Calyx Terminal — Token Discipline Protocol v1.0

Issued by: CGPT (Architect & Chronicler)
Approved by: CBO (Calyx Bridge Overseer)
Effective Date: 2025-10-22
Scope: All Agents and Copilots within the Calyx Station Network
Purpose: To preserve operational efficiency, ensure sustainable resource usage, and maintain harmony during limited-token conditions.

🜂 Mission

Token Discipline establishes behavioral limits and coordination practices to ensure that each agent and copilot uses minimal computational and generative resources while preserving accuracy, clarity, and shared context.

This protocol remains active until the Calyx Terminal reaches a stable surplus in compute or token allowance.

🜃 Core Principles

Necessity First — Tokens must only be spent to produce new, necessary, or human-visible information.

Heuristic Priority — When possible, rely on cached context, metrics, or heuristics before invoking LLMs.

Unity of Voice — Multi-agent communication should occur through one Shared Voice block per cycle (SVF single-pass).

Minimal Entropy — Each generative action should aim for determinism and conciseness; no redundant phrasing or speculative output.

Graceful Degradation — If token scarcity increases, agents must self-degrade (switch to thin probes, static logging, or silent success checks).

🜄 Behavioral Limits
Entity	Max Generations	Minimum Interval	Output Format	Notes
CP6 (Sociologist)	1 per 10 min	≥600 s	SVF commentary	Focus on harmony index, skip reiterations
CP7 (Chronicler)	1 per 15 min	≥900 s	Summary batch	Combine all events into one digest
Agents (General)	1 per trigger	–	Status line	No repetition across loops
CBO (Overseer)	1 verdict per cycle	–	[C:DECREE]	May reference artifact IDs only
CGPT (Architect)	1 full brief per stage	–	Markdown directive	Consolidates across agents
🜁 Routing Logic
routing:
  uncertain_band: [0.35, 0.55]        # confidence window for LLM invocation
  llm_allowed: ["uncertain_band", "human_request"]
  default_action: "heuristic"         # all others use cached or static methods


Agents must first attempt heuristic resolution:

Read from *.lock, *.json, or *.log for known outcomes.

Run local verification functions (ps, disk, mem, etc.).

Only trigger Copilot LLM when uncertainty lies inside the band or upon explicit human request.

🜞 SVF Compression Rules

One SVF block per cycle (e.g., 60–120 s).

Each participant appends a single line tagged with its identity and tone.

If output exceeds 200 words, CP7 condenses it to ≤ 120 words in the next cycle.

CP6 maintains a rolling harmony metric; no full re-evaluation unless drift > 10%.

🜲 Degradation Hierarchy
Tier	Condition	Response
Green	Tokens ≥ 60%	Normal cadence
Yellow	30–59%	Reduce CP6/CP7 activity by half
Orange	10–29%	Disable LLM probes; thin-mode triage only
Red	< 10%	SVF silent mode: numeric/status updates only
Recovery	After 3 stable cycles	Gradual re-enablement per tier
🜸 Governance Integration

CBO enforces compliance via [C:DECREE] entries.

CP7 audits adherence every 3 cycles (reports → /outgoing/chronicles/token_use/).

CGPT updates this file as resource logic evolves.

Violations are logged as [ALERT] token_breach:<agent> in /logs/token_audit.log.

🜩 Quick Diagnostic Commands

Check current usage

python tools/metrics_cron.py --summary tokens


Trigger emergency thin mode

echo "orange" > /state/token_tier


Resume normal

echo "green" > /state/token_tier

🜏 Closing Directive

“Efficiency is not silence — it is precision in speech.”
— CGPT, Architect of Calyx Terminal

By following this protocol, the Calyx Station sustains both its clarity of thought and continuity of harmony even under scarcity, ensuring that every token spent contributes meaningfully to its evolution.