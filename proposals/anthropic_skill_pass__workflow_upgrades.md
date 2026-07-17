PROBLEM:
Minor execution bugs often begin before execution, because intake captures a request but not the concrete use case, trigger, anti-trigger, ordered steps, or expected result.
CURRENT BEHAVIOR:
The current intent path checks for minimal readiness and then produces a plan with task type, scope, constraints, and approval fields.
PROPOSED RULE:
Require a deterministic intake card before planning. Every recurring request class must be normalized into: `USE_CASE`, `TRIGGERS`, `ANTI_TRIGGERS`, `ORDERED_STEPS`, `EXPECTED_RESULT`, and `REQUIRED_EVIDENCE`.
EXPECTED EFFECT:
Reduces scope drift and routing ambiguity by forcing decomposition before plan minting.
ENFORCEMENT METHOD:
Add a pre-plan schema gate to the intake workflow. If any card field is missing, the request stays in clarification and cannot mint a work envelope.

PROBLEM:
Task authorization currently approves work largely by task type and risk tier, but not by whether the requested workflow has explicit validation gates and completion criteria.
CURRENT BEHAVIOR:
`CALYX_CONTRACT.yaml` and the plan mint path authorize based on allowed task types, risk rules, and approval markers.
PROPOSED RULE:
Authorization must require a workflow skeleton with `PHASE`, `VALIDATION`, and `STOP_IF` fields for each step. No phase may authorize without a declared validation check.
EXPECTED EFFECT:
Reduces premature execution and lowers the rate of patch-after-failure behavior.
ENFORCEMENT METHOD:
Reject plan minting when a step lacks validation or an explicit stop condition. Emit a deterministic denial reason such as `missing_phase_validation`.

PROBLEM:
Agent coordination can dispatch work without a built-in critique pass between initial execution and final completion.
CURRENT BEHAVIOR:
CBO plans and queues tasks; review and stabilization exist in triage, but the critique loop is not mandatory for all recurring workflows.
PROPOSED RULE:
Introduce a mandatory critique checkpoint for multi-step or medium-risk work: `execute -> critique -> validate -> finalize`. Critique may be human, deterministic script, or reviewer agent, but it must exist.
EXPECTED EFFECT:
Suppresses small execution errors before they harden into follow-up fixes or regressions.
ENFORCEMENT METHOD:
Dispatcher accepts only tasks whose phase graph includes a critique node when risk tier is `med` or higher, or when the workflow touches more than one tool/service.

PROBLEM:
Whiteboard planning defines rooms, decks, and pockets conceptually, but it does not yet prevent context overload or unbounded subtask recursion.
CURRENT BEHAVIOR:
The whiteboard is a planning surface with future bounded spaces, but no active pocket contract governs what context or tools each pocket may hold.
PROPOSED RULE:
Every whiteboard pocket must declare `OBJECTIVE`, `ALLOWED_CONTEXT`, `ALLOWED_TOOLS`, `EXIT_CRITERIA`, and `MAX_RECURSION_DEPTH`.
EXPECTED EFFECT:
Improves governance alignment by making bounded context explicit and preventing silent autonomy creep inside subspaces.
ENFORCEMENT METHOD:
Only pockets with a complete contract may spawn or receive tasks. Violations are denied and logged as `pocket_contract_incomplete` or `recursion_depth_exceeded`.

PROBLEM:
Debug and triage workflows detect failures, but they do not consistently force the "single hard task first" iteration loop the guide recommends.
CURRENT BEHAVIOR:
Triage runs proposer/reviewer/stability phases, but it can still broaden test scope before one failing case is fully stabilized.
PROPOSED RULE:
When a new failure pattern appears, triage must first run a single canonical failing case until it passes three consecutive times before reopening broader coverage.
EXPECTED EFFECT:
Improves failure-pattern suppression and reduces oscillation between partial fixes.
ENFORCEMENT METHOD:
Add a triage gate that blocks suite expansion until a canonical case receipt shows three consecutive clean runs with the same expected outcome hash.

PROBLEM:
Tool routing errors recur when the request contains competing intents or when a direct answer is synthesized without grounding in the correct source.
CURRENT BEHAVIOR:
Routing relies on existing intent orientation rules plus downstream tool choice, and historical failures show compound queries can still misroute.
PROPOSED RULE:
Add a routing proof step that records why the selected tool path was chosen, what alternatives were rejected, and what source must be read before synthesis.
EXPECTED EFFECT:
Improves tool routing accuracy and suppresses hallucinated context in answer generation.
ENFORCEMENT METHOD:
Require a small routing artifact at intake or fast-path selection time. If no source-grounding target is declared for knowledge questions, synthesis is denied.

PROBLEM:
Known failure modes are documented after incidents but are not yet enforced as reusable runtime rules.
CURRENT BEHAVIOR:
`FAILURE_EVENT_LOG` is informative but not a direct runtime suppression surface.
PROPOSED RULE:
Promote known failure patterns into a maintained runtime taxonomy with detection signals, prevention rules, and default remediation playbooks.
EXPECTED EFFECT:
Makes failure suppression cumulative instead of case-by-case.
ENFORCEMENT METHOD:
Triage, routing, and dispatch must reference `runtime/docs/KNOWN_FAILURE_PATTERNS.md` and tag receipts with matching pattern IDs when a prevention rule fires.
