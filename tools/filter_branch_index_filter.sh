#!/bin/sh
# Index filter for git filter-branch: purge forbidden dirs and media extensions.
# Phase 4B offline history rewrite. Do NOT purge calyx/cbo/ dir; only the 5 runtime jsonl files.

# 1. Remove forbidden directories (NOT calyx/cbo/ - that would remove CBO source code)
for d in telemetry exports "station_calyx/data" outgoing incoming responses runtime state memory staging logs keys; do
  git rm -rf --cached --ignore-unmatch "$d" 2>/dev/null || true
done

# 2. Remove the 5 runtime jsonl files under calyx/cbo/ only
for f in calyx/cbo/objectives.jsonl calyx/cbo/objectives_history.jsonl calyx/cbo/sysint_acknowledged.jsonl calyx/cbo/task_queue.jsonl calyx/cbo/task_status.jsonl; do
  git rm --cached --ignore-unmatch "$f" 2>/dev/null || true
done

# 3. Remove media extension files (wav, mp3, m4a, png, jpg, jpeg)
git ls-files | grep -E '\.(wav|mp3|m4a|png|jpg|jpeg)$' | while read f; do
  git rm --cached --ignore-unmatch "$f" 2>/dev/null || true
done
