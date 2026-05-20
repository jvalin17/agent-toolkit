#!/bin/bash
# gate-cleanup.sh — Clears all gate flags after successful commit
#
# Every new commit requires fresh skill passes.
# Runs as PostToolUse hook on Bash tool.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

case "$COMMAND" in
  git\ commit*)
    rm -rf .gates 2>/dev/null
    ;;
esac

exit 0
