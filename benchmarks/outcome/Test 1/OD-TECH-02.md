## telemetry_history_viewer directory tree

```
telemetry_history_viewer/
  __init__.py
  cli.py              # entrypoint to select range/window
  loader.py           # read/parse telemetry.jsonl, events.jsonl
  filters.py          # slice by time, subsystem, event_type
  summarizer.py       # aggregates, counts, recent highlights
  renderer.py         # text/markdown output
  templates/
    report.md.j2      # optional Jinja template
```
