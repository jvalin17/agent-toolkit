#!/bin/bash
# post-commit-cleanup.sh — Clears .precommit-passed flag after successful commit
#
# This ensures every NEW commit requires a fresh /precommit pass.
# Runs as PostToolUse hook on Bash tool.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

case "$COMMAND" in
  git\ commit*)
    rm -f .precommit-passed 2>/dev/null
    ;;
esac

exit 0
