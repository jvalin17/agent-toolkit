#!/usr/bin/env bash
# Generate short AGENTS.md for each demo and run pytest.
set -euo pipefail
DEMOS_ROOT="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_ROOT="$(cd "$DEMOS_ROOT/.." && pwd)"
GEN="$TOOLKIT_ROOT/generate-project-rules.sh"

filter="${1:-}"
failed=0

for demo in calculators unit-converter todo-list password-strength; do
  if [[ -n "$filter" && "$demo" != "$filter" ]]; then
    continue
  fi
  dir="$DEMOS_ROOT/$demo"
  if [[ ! -d "$dir" ]]; then
    echo "skip missing $demo"
    continue
  fi
  echo "=== $demo ==="
  "$GEN" --cursor --project "$dir" >/dev/null
  if ! (cd "$dir" && python3 -m pytest tests/ -q); then
    echo "FAIL: $demo"
    failed=1
  else
    echo "OK: $demo"
  fi
  echo
done

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi
echo "All selected demos passed."
