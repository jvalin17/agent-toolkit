#!/bin/bash
# precommit-gate.sh — Blocks git commit/push unless /precommit has passed
#
# How it works:
# 1. /precommit skill creates .precommit-passed after all checks pass
# 2. This hook runs BEFORE every Bash tool call
# 3. If the command is git commit/push and .precommit-passed doesn't exist → BLOCK (exit 2)
# 4. After successful commit, .precommit-passed is cleared
#
# Install: Symlinked by install.sh into project .claude/hooks/
# Configure: Added to settings.json PreToolUse hooks

# Read tool input from stdin (Claude Code passes JSON)
INPUT=$(cat)

# Extract the command being run
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')

# Only care about git commit and git push
case "$COMMAND" in
  git\ commit*|git\ push*)
    ;;
  *)
    exit 0  # Not a git commit/push — allow
    ;;
esac

# Check for the precommit-passed flag
FLAG_FILE=".precommit-passed"

if [ ! -f "$FLAG_FILE" ]; then
  # Output JSON with context for Claude
  cat <<BLOCK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED by precommit-gate hook. You MUST run /precommit first. This is a structural enforcement — not a suggestion. Run /precommit now, and only after it passes will git commit be allowed."
  }
}
BLOCK_EOF
  exit 2  # BLOCK the tool call
fi

# Flag exists — allow the commit, then clean up
# (cleanup happens in post-commit hook)
exit 0
