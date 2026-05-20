#!/bin/bash
# session-monitor.sh — Hard-stop enforcement for session context limits
#
# Tracks exchanges, tool calls, and wall-clock time. Enforces hard stops
# when thresholds are exceeded to prevent quality degradation.
#
# Fires on:
#   PreToolUse (Bash|Write|Edit|Skill) — enforces limits, blocks at threshold
#   UserPromptSubmit — counts exchanges
#
# State persisted in .session/state (key=value format).
# State is initialized by session-init.sh on SessionStart.
#
# IMPORTANT: The agent must NEVER modify .session/ files directly.
# This is enforced by guardrail G-SESSION-1.

# --- Configuration (thresholds) ---
WARN_EXCHANGES=15
STOP_EXCHANGES=20
GRACE_TOOL_CALLS=10  # tool calls allowed after stop triggers (finish current work)

# --- State file ---
STATE_DIR=".session"
STATE_FILE="$STATE_DIR/state"

# Read input from stdin
INPUT=$(cat)

# --- Detect event type ---
# UserPromptSubmit has "prompt", PreToolUse has "tool_name"
IS_EXCHANGE=false
TOOL_NAME=""

if echo "$INPUT" | grep -q '"prompt"'; then
  IS_EXCHANGE=true
elif command -v jq &> /dev/null; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
else
  TOOL_NAME=$(echo "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

# --- Ensure state file exists ---
if [ ! -f "$STATE_FILE" ]; then
  mkdir -p "$STATE_DIR"
  cat > "$STATE_FILE" << INITEOF
SESSION_START=$(date +%s)
EXCHANGES=0
TOOL_CALLS=0
WARNED=0
STOPPED=0
STOP_AT_TOOL_CALL=0
INITEOF
fi

# --- Read current state ---
# shellcheck disable=SC1090
. "$STATE_FILE"

NOW=$(date +%s)
ELAPSED_SECONDS=$((NOW - ${SESSION_START:-$NOW}))
ELAPSED_MINUTES=$((ELAPSED_SECONDS / 60))

# --- Handle exchange counting ---
if [ "$IS_EXCHANGE" = true ]; then
  EXCHANGES=$((${EXCHANGES:-0} + 1))
  # Update state file atomically
  cat > "$STATE_FILE" << STATEEOF
SESSION_START=${SESSION_START:-$NOW}
EXCHANGES=$EXCHANGES
TOOL_CALLS=${TOOL_CALLS:-0}
WARNED=${WARNED:-0}
STOPPED=${STOPPED:-0}
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL:-0}
STATEEOF
  # Check if we should warn on exchange count
  if [ "$EXCHANGES" -ge "$WARN_EXCHANGES" ] && [ "${WARNED:-0}" -eq 0 ]; then
    WARNED=1
    cat > "$STATE_FILE" << STATEEOF2
SESSION_START=${SESSION_START:-$NOW}
EXCHANGES=$EXCHANGES
TOOL_CALLS=${TOOL_CALLS:-0}
WARNED=1
STOPPED=${STOPPED:-0}
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL:-0}
STATEEOF2
    cat << WARNEOF
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "SESSION WARNING: $EXCHANGES/$STOP_EXCHANGES exchanges used. Context degradation approaching. Start preparing HANDOFF.md NOW. Commit current work, pre-compute next steps, and write the handoff file. Format: see shared/project-state-template.md Resume section."
  }
}
WARNEOF
  fi
  exit 0
fi

# --- Handle PreToolUse (tool call tracking + enforcement) ---
if [ -z "$TOOL_NAME" ]; then
  exit 0
fi

TOOL_CALLS=$((${TOOL_CALLS:-0} + 1))

# --- Check if agent is trying to modify .session/ ---
COMMAND=""
FILE_PATH=""
if command -v jq &> /dev/null; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
  FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

# Block agent writes to .session/ (G-SESSION-1)
case "$TOOL_NAME" in
  Bash)
    if echo "$COMMAND" | grep -qE '\.session(/|[[:space:]]|$)'; then
      # Allow reads (cat, head, tail, less, more) but block writes
      if echo "$COMMAND" | grep -qE '(rm|mv|cp|echo|cat\s*>|tee|sed\s+-i|chmod|chown|mkdir.*\.session|>|>>)\s*.*\.session'; then
        cat << BLOCKEOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: Agent must not modify .session/ files (G-SESSION-1). Session state is managed by hooks only."
  }
}
BLOCKEOF
        exit 2
      fi
    fi
    ;;
  Write|Edit)
    if echo "$FILE_PATH" | grep -qE '\.session(/|$)'; then
      cat << BLOCKEOF2
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: Agent must not modify .session/ files (G-SESSION-1). Session state is managed by hooks only."
  }
}
BLOCKEOF2
      exit 2
    fi
    ;;
esac

# --- Check hard stop thresholds ---
THRESHOLD_HIT=false
STOP_REASON=""

if [ "${EXCHANGES:-0}" -ge "$STOP_EXCHANGES" ]; then
  THRESHOLD_HIT=true
  STOP_REASON="Exchange limit reached (${EXCHANGES}/${STOP_EXCHANGES})"
fi

if [ "$THRESHOLD_HIT" = true ]; then
  # First time hitting threshold? Start grace period — let agent finish current work
  if [ "${STOPPED:-0}" -eq 0 ]; then
    STOPPED=1
    STOP_AT_TOOL_CALL=$((TOOL_CALLS + GRACE_TOOL_CALLS))
    cat > "$STATE_FILE" << GRACEEOF
SESSION_START=${SESSION_START}
EXCHANGES=${EXCHANGES}
TOOL_CALLS=${TOOL_CALLS}
WARNED=1
STOPPED=1
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL}
GRACEEOF

    # Don't block — inject "finish up" context and let agent complete current response
    cat << GRACEMSG
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "SESSION LIMIT REACHED: ${STOP_REASON}. You have ${GRACE_TOOL_CALLS} tool calls remaining to wrap up.\n\nFinish your current task, then IMMEDIATELY:\n1. Write HANDOFF.md — current status, what's done (commits), what's next (spec text copied, not summarized), decisions, code change plan for next slab\n2. Update project-state.md Resume section\n3. git add + git commit all work\n4. Tell user: 'Session limit reached. Start a new session — I will read HANDOFF.md to continue.'\n\nDo NOT start new tasks. Wrap up and hand off."
  }
}
GRACEMSG
    exit 0  # Allow — grace period
  fi

  # Grace period active — check if exhausted
  GRACE_REMAINING=$((${STOP_AT_TOOL_CALL:-0} - TOOL_CALLS))
  if [ "$GRACE_REMAINING" -le 0 ]; then
    # Grace exhausted — only allow handoff operations
    ALLOWED=false

    case "$TOOL_NAME" in
      Write|Edit)
        case "$FILE_PATH" in
          *HANDOFF.md|*project-state.md)
            ALLOWED=true
            ;;
        esac
        ;;
      Bash)
        case "$COMMAND" in
          git\ commit*|git\ add*|git\ status*|git\ diff*|git\ log*|git\ stash*)
            ALLOWED=true
            ;;
          mkdir*)
            ALLOWED=true
            ;;
        esac
        ;;
    esac

    if [ "$ALLOWED" = false ]; then
      cat > "$STATE_FILE" << STOPEOF
SESSION_START=${SESSION_START}
EXCHANGES=${EXCHANGES}
TOOL_CALLS=${TOOL_CALLS}
WARNED=1
STOPPED=2
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL}
STOPEOF

      cat << HARDSTOP
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "HARD STOP: Grace period exhausted. ${STOP_REASON}.\n\nONLY allowed operations: Write HANDOFF.md, update project-state.md, git commit.\nEverything else is blocked. Write the handoff NOW and tell the user to start a new session."
  }
}
HARDSTOP
      exit 2
    fi
  else
    # Still in grace — remind but allow
    cat << GRACEREMIND
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "SESSION LIMIT: ${GRACE_REMAINING} tool calls remaining before hard stop. Finish current work and write HANDOFF.md."
  }
}
GRACEREMIND
  fi
fi

# --- Check warn thresholds (if not already warned) ---
SHOULD_WARN=false
if [ "${WARNED:-0}" -eq 0 ]; then
  if [ "${EXCHANGES:-0}" -ge "$WARN_EXCHANGES" ]; then
    SHOULD_WARN=true
  fi
fi

# Update state file
cat > "$STATE_FILE" << UPDATEEOF
SESSION_START=${SESSION_START}
EXCHANGES=${EXCHANGES}
TOOL_CALLS=${TOOL_CALLS}
WARNED=${WARNED:-0}
STOPPED=${STOPPED:-0}
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL:-0}
UPDATEEOF

if [ "$SHOULD_WARN" = true ]; then
  # Set warned flag
  cat > "$STATE_FILE" << WARNSTATE
SESSION_START=${SESSION_START}
EXCHANGES=${EXCHANGES}
TOOL_CALLS=${TOOL_CALLS}
WARNED=1
STOPPED=${STOPPED:-0}
STOP_AT_TOOL_CALL=${STOP_AT_TOOL_CALL:-0}
WARNSTATE

  cat << WARNMSG
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "SESSION WARNING: ${EXCHANGES:-0}/${STOP_EXCHANGES} exchanges. You are approaching the hard stop. Finish current work, commit, and prepare HANDOFF.md. Do not start new slabs or features."
  }
}
WARNMSG
fi

exit 0
