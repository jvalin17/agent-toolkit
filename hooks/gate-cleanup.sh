#!/bin/bash
# gate-cleanup.sh — Clears all gate flags after successful commit
#
# Every new commit requires fresh skill passes.
# Runs as PostToolUse hook on Bash tool.

INPUT=$(cat)

# Extract command — jq first, grep fallback
if command -v jq &> /dev/null; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

case "$COMMAND" in
  git\ commit*)
    rm -rf .gates 2>/dev/null
    ;;
esac

exit 0
