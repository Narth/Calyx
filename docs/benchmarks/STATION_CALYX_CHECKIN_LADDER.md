# Station Calyx — Model Check-In Benchmark Ladder

Human-guided benchmark: same check-in prompt across each model role to verify routing, confirm-receipt behavior, and second-opinion wiring. **CBO is included in all test and assessment metrics:** CBO is the responder (confirm receipt) and the orchestrator (cbo_core); every ladder run assesses CBO.

## Check-in prompt (canonical)

```
CBO, please confirm receipt.
```

## Ladder 1 — Human-guided (2026-02-21 / 2026-02-22)

**Context:** First ladder run via Avatar Web; confirm-receipt prompt change and `allow_second_opinion` when second_opinion selected were in place.

| Run | Model role      | Result |
|-----|-----------------|--------|
| 1   | (unspecified)   | CBO replied; Tools used: repo_list; no explicit "Receipt confirmed" in snippet. |
| 2   | (unspecified)   | "Receipt confirmed." |
| 3   | (unspecified)   | "Acknowledged. Receipt confirmed." |
| 4   | second_opinion  | "Receipt confirmed. Station Calyx CBO Hub acknowledges." + Second opinion (Kimi) panel. |
| 5   | (unspecified)   | STATE block echoed in reply; Tools used: repo_list; Context: STATE.md injected. |

**Notes:**
- Brief confirmations observed (no tool-heavy replies for confirm receipt).
- Second opinion (Kimi) participated when selected; Avatar Web now sends `allow_second_opinion: true` when model is second_opinion.
- STATE block in one reply showed typos in model output (e.g. calles, cbopass.docs, StopFirsst); source STATE.md on disk is correct — corruption from model echo/summary.

---

## Ladder 2 — CBO-driven (automated check-in per model)

**Run:** 2026-02-22 (CBO invoked POST /chat for each role from repo.)

| Model role     | HTTP | Reply snippet | second_opinion_text | Notes |
|----------------|------|----------------|---------------------|-------|
| architect      | 200  | Receipt confirmed. | — | Tools: repo_list. |
| workhorse      | 200  | Receipt confirmed. | — | Tools: repo_list. |
| second_opinion | 200  | Receipt confirmed. | Receipt confirmed. | Kimi wired; STATE injected. |
| local          | 200  | STATE echo + Tools used: repo_list | — | Ollama/tinyllama; STATE echoed with minor typos in model output. |

**Result:** All four roles returned 200 and a brief confirmation. Ladder pass.

---

## How to run a ladder (manual)

1. Ensure Station Calyx is up: `Scripts\start_calyx_core_services.ps1 [-StopFirst]`.
2. For each model_role in architect, workhorse, second_opinion, local:
   - POST to `http://127.0.0.1:7778/chat` with JSON:
     - `user_text`: "CBO, please confirm receipt."
     - `session_id`: "home"
     - `mode`: "dev"
     - `allow_tools`: true
     - `model_role`: \<role\>
     - `allow_second_opinion`: true when model_role is second_opinion.
3. Record reply_text (snippet), receipt_sha256, second_opinion_text (if any), and any errors.

---

*Canonical log for Station Calyx check-in ladders. Append new ladders with date and results table.*
