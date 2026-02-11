#!/usr/bin/env bash
set -euo pipefail

DENY_PATHS='^(telemetry/|exports/|station_calyx/data/|outgoing/|incoming/|responses/|runtime/)'
DENY_FILES='(evidence\.jsonl$|audit\.jsonl$|messages\.jsonl$|receipts\.jsonl$|\.wav$|\.mp3$|\.png$|\.jpg$|\.jpeg$)'

tracked=$(git ls-files)
path_hits=$(printf "%s
" "$tracked" | rg -n "$DENY_PATHS" || true)
file_hits=$(printf "%s
" "$tracked" | rg -n "$DENY_FILES" || true)

violations=$(printf "%s
%s
" "$path_hits" "$file_hits" | sed '/^$/d')

if [[ -n "$violations" ]]; then
  echo "Forbidden tracked paths/files detected:" >&2
  echo "$violations" >&2
  exit 1
fi

echo "No forbidden tracked paths detected."
