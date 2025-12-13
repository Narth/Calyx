## Python logging helper sketch

- Function `append_task_log(path, entry)`:
  - ensure parent dirs; open in append mode; json.dump + newline
  - entry includes task_id, timestamps, peaks, scores, resource_units
- Wrapper `log_task(task_id, **kwargs)` computes resource_units if duration/gpu/ram present
- Optional integrity: write a .bak?; but append-only suffices
- Usage: call after each task to append to run file
