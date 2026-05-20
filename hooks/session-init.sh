#!/bin/bash
# session-init.sh — Loads toolkit rules and scans project .md files at session start
#
# Runs as SessionStart hook. Re-fires after /compact so rules survive.
# Scans the project for .md files and tells Claude to read them FIRST
# before doing anything else.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"
CWD=$(pwd)

# --- Scan for project .md files ---
MD_FILES=""

# Priority files (read first)
for f in HANDOFF.md project-state.md CLAUDE.md DECISIONS.md; do
  if [ -f "$CWD/$f" ]; then
    MD_FILES="${MD_FILES}\n- $f (PRIORITY — read this first)"
  fi
done

# Requirements and architecture docs
for dir in requirements architecture; do
  if [ -d "$CWD/$dir" ]; then
    for f in "$CWD/$dir"/*.md; do
      [ -f "$f" ] || continue
      MD_FILES="${MD_FILES}\n- ${dir}/$(basename "$f")"
    done
  fi
done

# Reports (just list, don't read all — too much context)
REPORT_COUNT=0
if [ -d "$CWD/reports" ]; then
  REPORT_COUNT=$(find "$CWD/reports" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
fi

# Other .md files in root (not README — that's public docs, not project state)
for f in "$CWD"/*.md; do
  [ -f "$f" ] || continue
  fname=$(basename "$f")
  case "$fname" in
    README.md|HANDOFF.md|project-state.md|CLAUDE.md|DECISIONS.md) continue ;;
    *) MD_FILES="${MD_FILES}\n- $fname" ;;
  esac
done

# --- Build context ---
CONTEXT="AGENT TOOLKIT ACTIVE — You must follow skill workflows for all tasks.

SESSION START: Read project context before doing anything.

PROJECT FILES TO READ FIRST:"

if [ -n "$MD_FILES" ]; then
  CONTEXT="${CONTEXT}${MD_FILES}"
  if [ "$REPORT_COUNT" -gt 0 ]; then
    CONTEXT="${CONTEXT}\n- reports/ directory has ${REPORT_COUNT} report(s) — read only if relevant to current task"
  fi
  CONTEXT="${CONTEXT}\n\nREAD THESE FILES NOW before responding to the user. They contain decisions, feature status, warnings, and context you need. The user cannot remember all details — these files ARE the memory."
else
  CONTEXT="${CONTEXT}\nNo project .md files found. This may be a new project or first session."
fi

CONTEXT="${CONTEXT}

MANDATORY RULES:
1. NEVER edit code without following a skill workflow. Read the skill .md file first.
2. For bug fixes: follow /debug (hypothesis-driven, test-first)
3. For new features: follow /implementation (plan, TDD, slabs)
4. For refactors: follow /implementation in refactor mode
5. ALWAYS write a failing test BEFORE fixing or implementing
6. ALWAYS run /precommit before git commit (harness hook blocks without it)
7. Keep responses SHORT. Ask ONE question at a time. Don't dump information.
8. After implementing a feature, update project-state.md — strikethrough completed features
9. Every decision needs evidence. Cite file:line, requirement, or research.

RESPONSE STYLE:
- Ask focused questions, one at a time
- Don't explain what you're going to do — just do it
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
