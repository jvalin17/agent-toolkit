#!/bin/bash
# precommit-passed.sh — Creates .precommit-passed flag when /precommit skill completes
#
# Runs as PostToolUse hook on Skill tool, matched to "precommit".
# This is the ONLY way to unlock git commit.

INPUT=$(cat)

# Check if the skill that just ran was /precommit
SKILL=$(echo "$INPUT" | grep -o '"skill"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

if [ "$SKILL" = "precommit" ]; then
  touch .precommit-passed
  cat <<PASS_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Precommit passed. .precommit-passed flag set. git commit is now unlocked for this change set."
  }
}
PASS_EOF
fi

exit 0
