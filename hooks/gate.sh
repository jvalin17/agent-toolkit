#!/bin/bash
# gate.sh — Blocks git commit/push unless required skills have passed
#
# Reads gates.json (from project root, or toolkit default) to determine
# which skills must pass before commit and push are allowed.
#
# Each skill creates .gates/<skill>-passed when it completes.
# This hook checks for all required flags.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read tool input from stdin
INPUT=$(cat)

# Extract the command
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

# Determine action type
ACTION=""
case "$COMMAND" in
  git\ commit*)  ACTION="commit" ;;
  git\ push*)    ACTION="push" ;;
  *)             exit 0 ;;  # Not a git commit/push — allow
esac

# Find gates config: project root first, then toolkit default
GATES_CONFIG=""
if [ -f "gates.json" ]; then
  GATES_CONFIG="gates.json"
elif [ -f ".claude/gates.json" ]; then
  GATES_CONFIG=".claude/gates.json"
elif [ -f "$SCRIPT_DIR/gates.json" ]; then
  GATES_CONFIG="$SCRIPT_DIR/gates.json"
fi

# If no config found, default to requiring precommit for commit
if [ -z "$GATES_CONFIG" ] || ! command -v jq &> /dev/null; then
  # Fallback: just check precommit for commits
  if [ "$ACTION" = "commit" ] && [ ! -f ".gates/precommit-passed" ]; then
    cat <<FALLBACK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git commit requires /precommit to pass first. Run /precommit now."
  }
}
FALLBACK_EOF
    exit 2
  fi
  exit 0
fi

# Check if a profile is set
PROFILE=$(jq -r '.profile // empty' "$GATES_CONFIG" 2>/dev/null)

if [ -n "$PROFILE" ]; then
  REQUIRED=$(jq -r ".profiles.${PROFILE}.${ACTION}_requires[]?" "$GATES_CONFIG" 2>/dev/null)
else
  REQUIRED=$(jq -r ".${ACTION}_requires[]?" "$GATES_CONFIG" 2>/dev/null)
fi

# If no requirements defined for this action, allow
if [ -z "$REQUIRED" ]; then
  exit 0
fi

# Check each required skill
MISSING=""
for SKILL in $REQUIRED; do
  if [ ! -f ".gates/${SKILL}-passed" ]; then
    MISSING="${MISSING} /${SKILL}"
  fi
done

# If any missing, block
if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | xargs)
  cat <<BLOCK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git ${ACTION} requires these skills to pass first: ${MISSING_TRIMMED}. Run them now. This is structural enforcement — cannot be bypassed."
  }
}
BLOCK_EOF
  exit 2
fi

exit 0
