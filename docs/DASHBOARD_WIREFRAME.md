# Bloom Dashboard Wireframe (Placeholder)

Implementation deferred, but this wireframe documents how live analytics should be wired once UI work resumes.

## Data Sources
- `reports/bloom_metrics_feed.json` / `.csv`: primary bloom telemetry (AGII/TES/AREI/WARN + latest agent runs).
- `reports/core_pillars_manifest.md`: textual summary of triad status.
- `reports/bloom_status_*.md`: session-by-session narratives.
- `outgoing/bloom_reflections.md`: qualitative log from agents.

## Layout Sketch
1. **Header Strip**
   - Pillar gauges for AGII, TES, AREI, WARN (color-coded by thresholds).
   - Timestamp of `bloom_metrics_feed`.
2. **Agent Carousel**
   - Cards for Agent2/3/4 showing last goal, mode, TES, duration, status.
   - CTA to view full run logs (`outgoing/agent_run_*`).
3. **Trend Charts (Future)**
   - AGII/TES/AREI line chart over 72h (pull from metrics feed once historical data is appended).
   - WARN ratio sparkline.
4. **Reflection Panel**
   - Markdown render of the latest entry in `outgoing/bloom_reflections.md`.
5. **Action Queue**
   - Upcoming objectives pulled from `config.yaml:scheduler.bloom_mode.objectives`.

## Implementation Notes
- Use the JSON feed as the canonical API; keep CSV for spreadsheet/BI tooling.
- When ready, set up a small script (or existing dashboard service) to regenerate the feed after each bloom dispatcher run.
- UI stack TBD; previous attempts stalled on hosting, so defer until infrastructure questions are resolved.
