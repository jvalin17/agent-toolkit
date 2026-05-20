#!/bin/bash
# gate.sh — Blocks git commit/push unless signed gate token validates (or legacy .gates).
#
# Signed mode: verifies .gate/gate-token.jwt via verify_gate.py (report-bound JWT).
# Legacy mode: reads .gates/*-passed files (gate_mode in gates.json).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"

INPUT=$(cat)

if command -v jq &> /dev/null; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

ACTION=""
case "$COMMAND" in
  git\ commit*)  ACTION="commit" ;;
  git\ push*)    ACTION="push" ;;
  *)             exit 0 ;;
esac

# Signed verify only when project was bootstrapped (not toolkit path alone)
VERIFY_SCRIPT=""
if [ -f ".agent-toolkit/gate/scripts/verify_gate.py" ]; then
  VERIFY_SCRIPT=".agent-toolkit/gate/scripts/verify_gate.py"
fi

GATE_MODE="legacy"
if [ -f "gates.json" ] && command -v jq &> /dev/null; then
  GATE_MODE=$(jq -r '.gate_mode // "legacy"' gates.json 2>/dev/null)
fi

if [ "$GATE_MODE" = "signed" ] && [ -n "$VERIFY_SCRIPT" ] && command -v python3 &> /dev/null; then
  COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
  OUTPUT=$(python3 "$VERIFY_SCRIPT" verify --action "$ACTION" --commit "$COMMIT_SHA" 2>&1) || EXIT_CODE=$?
  EXIT_CODE=${EXIT_CODE:-0}
  if [ "$EXIT_CODE" -ne 0 ]; then
    MSG=$(echo "$OUTPUT" | tr '\n' ' ')
    cat <<SIGNED_BLOCK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git ${ACTION} — ${MSG} Run skills (/precommit, /evaluate), push to GitHub for CI to issue signed gate-token.jwt, or download the gate-token artifact."
  }
}
SIGNED_BLOCK_EOF
    exit 2
  fi
  exit 0
fi

# --- Legacy .gates/ validation (gate_mode: legacy) ---
GATES_CONFIG=""
if [ -f "gates.json" ]; then
  GATES_CONFIG="gates.json"
elif [ -f ".claude/gates.json" ]; then
  GATES_CONFIG=".claude/gates.json"
elif [ -f "$SCRIPT_DIR/gates.json" ]; then
  GATES_CONFIG="$SCRIPT_DIR/gates.json"
fi

if [ -z "$GATES_CONFIG" ] || ! command -v jq &> /dev/null; then
  if [ "$ACTION" = "commit" ]; then
    if [ ! -f ".gates/precommit-passed" ] || ! grep -q "READY" ".gates/precommit-passed" 2>/dev/null; then
      cat <<FALLBACK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git commit requires /precommit (signed mode needs gate-token.jwt). Run ./install.sh in project root."
  }
}
FALLBACK_EOF
      exit 2
    fi
  fi
  exit 0
fi

PROFILE=$(jq -r '.profile // empty' "$GATES_CONFIG" 2>/dev/null)
if [ -n "$PROFILE" ]; then
  REQUIRED=$(jq -r ".profiles.${PROFILE}.${ACTION}_requires[]?" "$GATES_CONFIG" 2>/dev/null)
else
  REQUIRED=$(jq -r ".${ACTION}_requires[]?" "$GATES_CONFIG" 2>/dev/null)
fi

if [ -z "$REQUIRED" ]; then
  exit 0
fi

MISSING=""
for SKILL in $REQUIRED; do
  FLAG=".gates/${SKILL}-passed"
  if [ ! -f "$FLAG" ]; then
    MISSING="${MISSING} /${SKILL}"
    continue
  fi
  case "$SKILL" in
    precommit)
      grep -q "READY" "$FLAG" 2>/dev/null || MISSING="${MISSING} /${SKILL}(no READY)"
      ;;
    evaluate)
      EVAL_THRESHOLD=95
      CUSTOM=$(jq -r '.eval_threshold // empty' "$GATES_CONFIG" 2>/dev/null)
      [ -n "$CUSTOM" ] && EVAL_THRESHOLD="$CUSTOM"
      if ! grep -q "PASSED" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} /${SKILL}(no PASSED)"
      else
        SCORE=$(grep -oE '[0-9]+' "$FLAG" 2>/dev/null | head -1)
        [ -z "$SCORE" ] || [ "$SCORE" -lt "$EVAL_THRESHOLD" ] && \
          MISSING="${MISSING} /${SKILL}(score ${SCORE:-?}% < ${EVAL_THRESHOLD}%)"
      fi
      ;;
    reviewer|assess)
      grep -q "PASSED" "$FLAG" 2>/dev/null || MISSING="${MISSING} /${SKILL}(no PASSED)"
      ;;
  esac
done

if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | xargs)
  cat <<BLOCK_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "BLOCKED: git ${ACTION} requires: ${MISSING_TRIMMED}. Run skills, then set-gate or use signed CI token."
  }
}
BLOCK_EOF
  exit 2
fi

exit 0
