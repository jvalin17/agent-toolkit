#!/bin/bash
# skill-reminder.sh — After file edits, reminds Claude about available skills
#
# Runs as PostToolUse hook on Edit/Write tools.
# Injects context so Claude knows to run quality gates.

cat <<REMINDER_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Files were modified. Remember: G-PUSH-1 requires /precommit before any git commit. Run /precommit when ready to commit."
  }
}
REMINDER_EOF

exit 0
