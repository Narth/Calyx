# Outcome Density Run Protocol (Telemetry-Ready)

Goal: make OD runs auditable with zero heuristics. The system should declare when it is working.

## 1) Create a run_id (anchor)
Example: `OD-2025-12-13T06-00-UTC`

Use this run_id everywhere:
- prompt phases
- resource monitor `--tag`
- MD headers
- reflections/envelopes

## 2) Mark prompt phases (ground truth)
Use the helper:
```
python benchmarks/tools/od_phase_logger.py --run-id <RUN_ID> --prompt-id OD-01 --event PROMPT_START
# generate response
python benchmarks/tools/od_phase_logger.py --run-id <RUN_ID> --prompt-id OD-01 --event PROMPT_END
```
Appends to `logs/system/prompt_phases.jsonl`:
- timestamp (UTC)
- event: PROMPT_START | PROMPT_END
- run_id
- prompt_id

## 3) Tag resource monitor with run_id
Start the monitor in a separate shell:
```
python benchmarks/tools/resource_monitor.py --interval 2 --duration 600 --tag "<RUN_ID>"
```
Logs to `logs/system/resource_usage.jsonl` with the same run_id tag.

## 4) Embed timing in MD outputs
At top of each OD MD file, include:
```
<!--
run_id: <RUN_ID>
prompt_id: OD-01
generated_at_start_utc: 2025-12-13T06:02:14.123Z
generated_at_end_utc:   2025-12-13T06:02:41.987Z
-->
```

## 5) Analysis contract (CBO/CALYX)
- Primary truth: `logs/system/prompt_phases.jsonl`
- Telemetry join: `resource_usage.jsonl` filtered by [PROMPT_START, PROMPT_END] for matching run_id/prompt_id.
- MD headers are secondary validation.
- If phase markers are missing, analysis should report degraded mode (no heuristics).

## 6) Metrics to compute (once aligned)
Per prompt:
- exact duration
- CPU/RAM avg/max
- GPU util avg/max
- GPU power avg/max; energy Wh (full coverage)
- (optional) idle vs active deltas

Per run:
- total active time
- total GPU energy cost
- efficiency (Wh per prompt; add tokens later if available)

## 7) One-line alignment reminder
If the system doesn’t declare when it is working, telemetry is forensic.
If it declares phases in real time, telemetry becomes ground truth.
