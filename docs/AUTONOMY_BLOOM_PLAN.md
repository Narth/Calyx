# Autonomy Bloom Plan (Phase 3)

Station Calyx transitions from research stabilization into **Bloom Mode** once the core pillars converge:

| Metric | Threshold | Current |
| --- | --- | --- |
| AGII | >=95 sustained over 48h | 97 (green) |
| TES (mean last 50) | >=95 | 96.95 |
| AREI | >=90 | 98.7 |
| WARN ratio | <=5% | 3.6% |

--- 

## Objectives
1. Promote autonomy where data proves trustworthiness.
2. Enable multimodal agents (vision, audio, text) to pursue specialized curricula while protecting shared infrastructure.
3. Maintain rapid recovery paths if any pillar dips below threshold.

---

## Promotion Gates
| Stage | Requirements | Result |
| --- | --- | --- |
| **Core** | TES >=90, AREI >=85 | Runs in `tests` mode with live supervision. |
| **Applied** | TES >=94, AREI >=90, WARN <=5% | Promotion to `apply_tests`, CBO monitoring. |
| **Expedition** | TES >=96, AREI >=95, AGII >=97 | Eligible for cascading autonomy through Agent4 loops. |

Falling below thresholds downgrades autonomy automatically and triggers CBO review.

---

## Bloom Pillars
1. **Multimodal Perception** - Train agents on vision tagging, audio alignment, and text reasoning in cohesive loops. Success = 95%+ TES in perception tasks and AREI sustainability >=0.9.
2. **Systems Excellence** - Deepen self-healing, resource arbitration, and watchdog co-training. Success = no watchdog interventions across 20 runs and AGII Safeguards >=95.

Each pillar aligns to curricula defined in `config.yaml:scheduler.bloom_mode.specialization_pillars`.

---

## Operational Changes\n- Scheduler cadences tightened (Agent2 420s, Agent3 540s, Agent4 660s) to keep multi-agent lessons frequent without overloading CPU (<70% enforcement via watchdog).\n- Agent4 enabled with max 5 steps to host advanced multimodal drills.\n- 	ools/metrics_cron.py + 	ools/agent_resilience_monitor.py provide hourly AREI and TES feed for promotion logic.\n- 	ools/metrics_stress_test.py is the regression suite for autonomy readiness.\n- 	ools/bloom_dispatcher.py + config.yaml:scheduler.bloom_mode.objectives coordinate curriculum dispatch; metrics feed stored under eports/bloom_metrics_feed.*.\n
---

## Rollback & Safety
- Any metric beneath its gate for more than two consecutive samples pauses bloom mode and reverts to research mode templates.
- Watchdog WARN >5% triggers investigation ticket in `reports/core_pillars_manifest.md`.
- Recovery protocol: downgrade autonomy, run stress harness to ensure guardrails respond, re-evaluate after 12h stable telemetry.

---

## Next Actions
1. Integrate bloom metrics into dashboards (`reports/core_pillars_manifest.md` + live UI).
2. Assign multimodal objectives to Agent2-Agent4 with curriculum tags.
3. Expand stress scenarios to include prompt-injection drills before full expeditionary autonomy.

