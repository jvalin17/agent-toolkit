#!/bin/bash
# skill-passed.sh — Sets gate flag when any gated skill completes
#
# Runs as PostToolUse hook on Skill tool.
# Creates .gates/<skill>-passed for any skill that's in the gates config.

INPUT=$(cat)

# Extract skill name
SKILL=$(echo "$INPUT" | grep -o '"skill"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

if [ -z "$SKILL" ]; then
  exit 0
fi

# Gated skills — any skill that could be required by gates.json
GATED_SKILLS="precommit evaluate reviewer assess"

for GATED in $GATED_SKILLS; do
  if [ "$SKILL" = "$GATED" ]; then
    mkdir -p .gates
    touch ".gates/${SKILL}-passed"
    cat <<PASS_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "/${SKILL} passed. Gate unlocked. Run other required skills or proceed with git commit/push."
  }
}
PASS_EOF
    break
  fi
done

exit 0
