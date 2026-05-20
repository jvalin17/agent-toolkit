#!/bin/bash
# session-init.sh — Loads toolkit rules at session start
#
# Runs as SessionStart hook. Injects persistent context that Claude
# sees throughout the session. Re-fires after /compact so rules survive.
#
# This ensures Claude ALWAYS knows about skills, even if the user
# doesn't explicitly invoke them.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"

CONTEXT="AGENT TOOLKIT ACTIVE — You must follow skill workflows for all tasks.

MANDATORY RULES:
1. NEVER edit code without following a skill workflow. Read the skill .md file first.
2. For bug fixes: read and follow skills/debug/SKILL.md (hypothesis-driven, test-first)
3. For new features: read and follow skills/implementation/SKILL.md (plan, TDD, slabs)
4. For refactors: read and follow skills/implementation/SKILL.md in refactor mode
5. ALWAYS write a failing test BEFORE fixing or implementing. No exceptions.
6. ALWAYS run /precommit before git commit. Harness hook will block you if you don't.
7. Keep responses SHORT. Ask ONE question at a time. Don't dump information.
8. Read project-state.md if it exists — it has decisions, warnings, and feature status.
9. Read shared/guardrails-quick.md for safety rules.

RESPONSE STYLE:
- Ask focused questions, one at a time
- Don't explain what you're going to do in 3 paragraphs — just do it
- Show evidence (file:line) for every claim
- If unsure, ask. Don't assume.

AVAILABLE SKILLS: /requirements /architecture /implementation /debug /verify /precommit /evaluate /reviewer /assess /explore /setup /status /updater"

# Escape for JSON
CONTEXT_ESCAPED=$(echo "$CONTEXT" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

cat <<INIT_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$CONTEXT_ESCAPED"
  }
}
INIT_EOF

exit 0
