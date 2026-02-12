#!/bin/sh
# Index filter for git filter-branch: remove openclaw.config.json from all history.
# Secret history purge - 2026-02-12

# Remove openclaw.config.json from all commits
git rm --cached --ignore-unmatch "openclaw.config.json" 2>/dev/null || true
