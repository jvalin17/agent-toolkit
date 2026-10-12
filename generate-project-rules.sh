#!/usr/bin/env bash
# Thin wrapper — generates short AGENTS.md / host rules from toolkit bootstrap.
set -euo pipefail
TOOLKIT_ROOT="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$TOOLKIT_ROOT/scripts/generate_project_rules.py" --toolkit "$TOOLKIT_ROOT" "$@"
