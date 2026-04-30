---
status: active
owner: station
last_reviewed_utc: "2026-02-27"
doctrine_scope: governed
---

# Avatar Web — Sub-agents, Task Tracking & Viewable Calyx Agents (Planning Whiteboard)

**Purpose:** Plan the path to an LLM-driven Avatar Web that handles sub-agents and task tracking, with viewable agent avatars for Calyx Agents in the browser. Local-network first, **gated by hardware capability** so we don’t overreach. Station Calyx deserves its flag and its crew — local first also means visible.

**Status:** Planning / whiteboard. Implementation is incremental and hardware-gated.

---

## North star

- **Visible crew:** A browser UI where operators see Calyx Agents as viewable avatars (per node, per role, or per task), not just a single chat line.
- **Sub-agents & task tracking:** Avatar Web uses an LLM (or a lightweight coordinator) to assign work to sub-agents and keep a visible task list; each agent has an identity and an avatar in the UI.
- **Local first:** Start on local network; no public exposure until stack policy allows. When we have the hardware, the experience should feel “local and visible” — the station’s flag and crew on screen.
- **Marketing / product:** A friendly, visible sub-agent (e.g. per-node or per-activity) is part of the story. Without a credible path to that, the fallback is pushing CBO to sales/SEO for charm — we’d rather build the whiteboard and the path so the crew is real.

---

## Hardware gate (current understanding)

From USER.md and HARDWARE_OPTIMIZATION.md:

- **GPU:** ~8 GB VRAM; Ollama (e.g. qwen3:8b) uses GPU but tokenization/sampling/KV-cache remain CPU-bound; CPU can hit 100% during CBO replies.
- **Latency:** Hardware constraints already cause 10+ min response times in some cases.
- **Implication:** One CBO conversation already stresses the box. Adding **concurrent** sub-agent LLM calls (multiple agents replying at once) would likely overreach.

**Options that respect the gate:**

| Approach | Description | Hardware fit |
|--------|-------------|--------------|
| **A. Serialized single agent** | Avatar Web shows a “crew” UI but only one agent (CBO or one sub-agent) runs at a time; task list is static or updated after each turn. | **Feasible** — same load as today, just better UX and task visibility. |
| **B. Tiny coordinator + one worker** | Small local model (e.g. 1–3B) does task routing/selection; CBO (or one worker) does the heavy reply. Coordinator and worker never run concurrently. | **Maybe** — if a tiny model fits alongside or we swap quickly; needs measurement. |
| **C. Cloud coordinator, local worker** | Coordinator in the cloud (or optional cloud) decides tasks; Station runs one local agent (CBO) and shows avatars/tasks in browser. | **Feasible** — adds network and product choice (local-first purity vs. capability). |
| **D. Full local multi-agent** | Multiple local LLM calls (coordinator + N sub-agents). | **Likely overreach** on current hardware — defer until upgrade or proven capacity. |

**Recommendation:** Build the **whiteboard and data model** now. Implement **A** (serialized single agent, task list, viewable avatar for CBO and placeholders for future sub-agents) so the UI and concepts exist. Gate **B/D** on a small hardware check (e.g. “can we run one 1–3B coordinator + one 8B worker without sustained 100% CPU?”). Revisit **C** only if we explicitly accept a non–fully-local coordinator.

---

## Whiteboard: architecture (target state)

### 1. Avatar Web as orchestrator UI

- **Task list (viewable):** List of tasks (e.g. “Summarize STATE,” “Check heartbeat,” “Reply to user query”). Each task has status (pending / in progress / done / failed), optional assignee agent id, and optional result snippet.
- **Agent roster (viewable):** List of Calyx Agents (CBO + future sub-agents). Each has: id, display name, avatar (image or placeholder), “current task” or idle, optional per-node or per-role label.
- **LLM integration point:** One of:
  - **Thin:** User or a fixed flow picks a task; Avatar Web sends one /chat to CBO Core (current behavior); UI shows that single agent as “speaking” and updates task status when done.
  - **Coordinator (later):** A small LLM (local or cloud) receives “pending tasks” and “available agents,” returns “assign task X to agent Y”; Avatar Web sends work to CBO (or a future sub-agent endpoint) and updates roster + task list.

### 2. Data model (minimal, for planning)

- **Task:** `id`, `title`, `status`, `assigned_agent_id?`, `result_snippet?`, `created_at`, `updated_at`.
- **Agent:** `id`, `display_name`, `avatar_url` (or placeholder key), `current_task_id?`, `node_id?` (for per-node display).
- **Session:** Existing session_id; task list can be per-session or global for the station.

### 3. Per-node / per-activity “friendly sub-agent”

- **Per node:** In a multi-node or federated view, each node could show one “face” (avatar + name) — e.g. “Station Calyx (CBO),” “Laptop bridge,” etc. Today that’s one avatar per node; later, each node could have a dedicated small model or the same CBO with a node-specific persona.
- **Per activity:** One “friendly” sub-agent for a specific activity (e.g. “Heartbeat checker,” “Report summarizer”) — same hardware constraint: serialized or tiny coordinator.

### 4. Implementation order (incremental)

1. **Whiteboard & doc (this file):** Vision, hardware gate, data model — done.
2. **Task list in Avatar Web (no extra LLM):** UI shows a list of tasks; user or a single “Run next” action triggers one /chat; task status updates from that one response. No coordinator yet.
3. **Agent roster + avatars in UI:** CBO is the first agent; show one avatar (CBO) and “current task.” Placeholder slots for future sub-agents (grey avatar, “Coming when hardware allows” or “Per-node agent”).
4. **Build safety check:** Run `Scripts\build_safety_check.ps1` before/during crucial builds; runbook `docs/planning/BUILD_SAFETY_CHECK.md`. Ensures we don't over-excite or fry hardware and avoid crash loops. Pass = proceed; Warn = one agent at a time; Fail = do not add load.
5. **Coordinator (later):** If hardware allows or we accept cloud coordinator: small service or prompt that returns (task_id, agent_id); Avatar Web assigns and displays.

---

## What we’re not doing yet

- Exposing Avatar Web beyond localhost (still under STATION_STACK_POLICY.md).
- Multiple concurrent local LLM calls for sub-agents (until hardware supports or we introduce a cloud coordinator).
- Replacing CBO with “sales/SEO only” — we’re building the plan so the crew is real and visible, and we can ship a friendly per-node/per-activity agent when the stack and hardware allow.

---

## Summary

- **Vision:** LLM-driven Avatar Web with sub-agents, task tracking, and viewable Calyx Agent avatars; local first, visible crew.
- **Gate:** Current hardware likely supports only serialized single-agent or “tiny coordinator + one worker” with measurement; we don’t overreach.
- **Next steps:** Keep this whiteboard as the plan; add task list + agent roster (with CBO avatar and placeholders) to Avatar Web when we’re ready to implement; gate full sub-agent spawning on hardware check or upgrade. Future: literal rooms/decks and channel pockets (docs/planning/WHITEBOARD_ROOMS_DECKS.md).

*Station Calyx deserves its flag and its crew. This is the planning board to get there.*
