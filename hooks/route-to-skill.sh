#!/bin/bash
# route-to-skill.sh — Detects user intent and injects skill routing context
#
# Runs as UserPromptSubmit hook. Reads the user's prompt, detects what
# they're trying to do, and injects context telling Claude WHICH skill
# to use and HOW to follow it.
#
# This is the structural enforcement that prevents the agent from
# "just doing things" without following the skill workflow.

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | sed -n 's/.*"prompt"[[:space:]]*:[[:space:]]*"\(.*\)"/\1/p' | head -1)

# Normalize to lowercase for matching
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# If user is already invoking a skill, don't interfere
case "$PROMPT_LOWER" in
  /*)
    exit 0
    ;;
esac

CONTEXT=""

# Bug fix / something broken
if echo "$PROMPT_LOWER" | grep -qE '(fix|bug|broken|crash|error|failing|not working|doesn.t work|blank page|0 results|silent fail)'; then
  CONTEXT="SKILL ROUTING: This looks like a bug fix. You MUST follow the /debug workflow:
1. Read skills/debug/SKILL.md — follow it strictly
2. Hypothesis-driven: form hypotheses, test them, eliminate
3. Write a FAILING test that reproduces the bug BEFORE fixing
4. Fix the code to make the test pass
5. Run /precommit before committing
Do NOT just edit the file and say 'fixed'. Follow the skill file step by step."

# Build / implement / add feature
elif echo "$PROMPT_LOWER" | grep -qE '(build|implement|create|add feature|new feature|make a|set up|scaffold)'; then
  CONTEXT="SKILL ROUTING: This is a build/implement task. You MUST follow the /implementation workflow:
1. Read skills/implementation/SKILL.md — follow it strictly
2. If no requirements exist: run /requirements first (ask Q1 + Q4, draft early)
3. If no architecture exists: run /architecture first (design with evidence)
4. Create a code change plan BEFORE writing any code
5. Build slab-by-slab with TDD — test first, then implementation
6. Run /precommit before committing
Do NOT just start writing code. Read the skill file and follow the flow."

# Refactor
elif echo "$PROMPT_LOWER" | grep -qE '(refactor|clean up|restructure|reorganize|simplify)'; then
  CONTEXT="SKILL ROUTING: This is a refactor task. You MUST follow /implementation in refactor mode:
1. Read skills/implementation/SKILL.md — follow refactor mode
2. Ensure all tests pass BEFORE refactoring
3. Refactor in small steps — tests must pass after each step
4. Run /precommit before committing
Do NOT refactor without confirming tests pass first."

# Understand / explore codebase
elif echo "$PROMPT_LOWER" | grep -qE '(understand|explore|what does|how does|explain|onboard|walk me through)'; then
  CONTEXT="SKILL ROUTING: This is a codebase exploration. Use /explore:
1. Read skills/explore/SKILL.md — follow the 4-phase analysis
2. Recon → Architecture → Conventions → Issues
3. Write findings to project-state.md"

# Review / check quality
elif echo "$PROMPT_LOWER" | grep -qE '(review|check quality|audit|how good|grade|score|evaluate)'; then
  CONTEXT="SKILL ROUTING: This is a quality check. Use the appropriate skill:
- Code review → /reviewer (read skills/reviewer/SKILL.md)
- Quality score → /evaluate (read skills/evaluate/SKILL.md)
- Architecture fitness → /assess (read skills/assess/SKILL.md)
Read the skill file and follow it strictly."

# Deploy / setup
elif echo "$PROMPT_LOWER" | grep -qE '(deploy|setup|install|docker|dockerfile|makefile|ci|cd)'; then
  CONTEXT="SKILL ROUTING: This is a setup/deploy task. Use /setup:
1. Read skills/setup/SKILL.md — follow it strictly
2. Generate install scripts, Docker config, README from code analysis"

# Requirements / planning
elif echo "$PROMPT_LOWER" | grep -qE '(require|plan|scope|what should|feature list|user stor)'; then
  CONTEXT="SKILL ROUTING: This is requirements gathering. Use /requirements:
1. Read skills/requirements/SKILL.md — follow it strictly
2. Ask Q1 (what?) + Q4 (how do you do this today?) — draft early
3. Go deeper on demand, don't force all questions upfront
4. Keep responses focused — ask ONE question at a time, don't dump information"

# Architecture / design
elif echo "$PROMPT_LOWER" | grep -qE '(architect|design|database|schema|api design|tech stack|pattern)'; then
  CONTEXT="SKILL ROUTING: This is architecture/design. Use /architecture:
1. Read skills/architecture/SKILL.md — follow it strictly
2. Present 2-3 options with trade-offs, user decides
3. Log decisions with evidence in project-state.md"
fi

# If we detected intent, inject context
if [ -n "$CONTEXT" ]; then
  # Escape for JSON
  CONTEXT_ESCAPED=$(echo "$CONTEXT" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')
  cat <<ROUTE_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "$CONTEXT_ESCAPED"
  }
}
ROUTE_EOF
fi

exit 0
