#!/usr/bin/env bash
set -euo pipefail

DENY_PATHS='^(telemetry/|exports/|station_calyx/data/|outgoing/|incoming/|responses/|runtime/)'
DENY_FILES='(evidence\.jsonl$|audit\.jsonl$|messages\.jsonl$|receipts\.jsonl$|\.wav$|\.mp3$|\.png$|\.jpg$|\.jpeg$)'

# Get all tracked files
tracked=$(git ls-files)

# Check for forbidden paths
path_hits=$(echo "$tracked" | grep -E "$DENY_PATHS" || true)

# Check for forbidden file extensions
file_hits=$(echo "$tracked" | grep -E "$DENY_FILES" || true)

# Combine violations
violations=$(printf "%s\n%s\n" "$path_hits" "$file_hits" | grep -v '^$' || true)

if [[ -n "$violations" ]]; then
  echo "Forbidden tracked paths/files detected:" >&2
  echo "$violations" >&2
  exit 1
fi

echo "No forbidden tracked paths detected."
exit 0
