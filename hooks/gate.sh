#!/bin/bash
# gate.sh — Blocks git commit/push unless required skills have passed
#
# Reads gates.json (from project root, or toolkit default) to determine
# which skills must pass before commit and push are allowed.
#
# Each skill creates .gates/<skill>-passed ONLY when it actually passes
# (not on mere invocation). This hook checks for those flags.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Read tool input from stdin
INPUT=$(cat)

# Extract the command — jq first, grep fallback
if command -v jq &> /dev/null; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

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

# If no config or no jq, fallback to precommit-only check with content validation
if [ -z "$GATES_CONFIG" ] || ! command -v jq &> /dev/null; then
  if [ "$ACTION" = "commit" ]; then
    if [ ! -f ".gates/precommit-passed" ] || ! grep -q "READY" ".gates/precommit-passed" 2>/dev/null; then
      cat <<FALLBACK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git commit requires /precommit to pass first (with READY marker). Run /precommit now."
  }
}
FALLBACK_EOF
      exit 2
    fi
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

# Check each required skill — validate flag content, not just existence
MISSING=""
for SKILL in $REQUIRED; do
  FLAG=".gates/${SKILL}-passed"
  if [ ! -f "$FLAG" ]; then
    MISSING="${MISSING} /${SKILL}"
    continue
  fi

  # Hardened validation: check flag content for proof of pass
  case "$SKILL" in
    precommit)
      # Flag must contain "READY" (written by precommit skill on pass)
      if ! grep -q "READY" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} /${SKILL}(flag exists but no READY marker — re-run)"
      fi
      ;;
    evaluate)
      # Flag must contain PASSED + score >= 95 (default threshold from orchestrator)
      # Read threshold from gates.json if available, otherwise default 95
      EVAL_THRESHOLD=95
      if [ -n "$GATES_CONFIG" ] && command -v jq &> /dev/null; then
        CUSTOM_THRESHOLD=$(jq -r '.eval_threshold // empty' "$GATES_CONFIG" 2>/dev/null)
        if [ -n "$CUSTOM_THRESHOLD" ]; then
          EVAL_THRESHOLD="$CUSTOM_THRESHOLD"
        fi
      fi
      if ! grep -q "PASSED" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} /${SKILL}(flag exists but no PASSED marker — re-run)"
      else
        SCORE=$(grep -oE '[0-9]+' "$FLAG" 2>/dev/null | head -1)
        if [ -z "$SCORE" ] || [ "$SCORE" -lt "$EVAL_THRESHOLD" ]; then
          MISSING="${MISSING} /${SKILL}(score ${SCORE:-?}% < ${EVAL_THRESHOLD}% threshold — re-run)"
        fi
      fi
      ;;
    reviewer)
      # Flag must contain PASSED (written by reviewer when no high-severity findings)
      if ! grep -q "PASSED" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} /${SKILL}(flag exists but no PASSED marker — high-severity findings remain)"
      fi
      ;;
    assess)
      # Flag must contain PASSED (written by assess when no critical anti-patterns)
      if ! grep -q "PASSED" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} /${SKILL}(flag exists but no PASSED marker — critical issues remain)"
      fi
      ;;
  esac
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
