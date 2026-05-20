#!/bin/bash
# skill-passed.sh — Informs Claude about gate status after a gated skill runs
#
# IMPORTANT: This hook does NOT set gate flags. Only the skill itself
# sets .gates/<skill>-passed when it actually passes (e.g., precommit
# ends READY TO COMMIT, evaluate scores ≥ threshold).
#
# This hook only tells Claude what gates are still needed.

INPUT=$(cat)

# Extract skill name — use jq if available, fallback to grep
if command -v jq &> /dev/null; then
  SKILL=$(echo "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null)
else
  SKILL=$(echo "$INPUT" | grep -o '"skill"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

if [ -z "$SKILL" ]; then
  exit 0
fi

# Check which gates exist and which are still needed
GATED_SKILLS="precommit evaluate reviewer assess"
IS_GATED=false
for GATED in $GATED_SKILLS; do
  if [ "$SKILL" = "$GATED" ]; then
    IS_GATED=true
    break
  fi
done

if [ "$IS_GATED" = false ]; then
  exit 0
fi

# Check if the skill set its own flag (meaning it actually passed)
if [ -f ".gates/${SKILL}-passed" ]; then
  # Skill set its own flag — it passed
  # Report remaining gates
  MISSING=""
  for GATED in $GATED_SKILLS; do
    if [ ! -f ".gates/${GATED}-passed" ]; then
      MISSING="${MISSING} /${GATED}"
    fi
  done

  if [ -n "$MISSING" ]; then
    MISSING_TRIMMED=$(echo "$MISSING" | xargs)
    MSG="/${SKILL} PASSED — gate unlocked. Still needed: ${MISSING_TRIMMED}"
  else
    MSG="/${SKILL} PASSED — all gates unlocked. git commit/push is allowed."
  fi
else
  # Skill did NOT set its flag — it did not pass
  MSG="/${SKILL} ran but did NOT pass. Gate remains locked. The skill must end with a passing result to unlock the gate. Check the skill output for BLOCKED reasons."
fi

cat <<INFO_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "$MSG"
  }
}
INFO_EOF

exit 0
