#!/bin/bash
# gate.sh - Reminds or blocks git commit/push (legacy .gates or signed JWT).
# Default enforcement is warn (exit 0) so Cursor and other agents are not hard-blocked.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLKIT_DIR="$(dirname "$SCRIPT_DIR")"

INPUT=$(cat)

if command -v jq &> /dev/null; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

STRIPPED=$(printf '%s' "$COMMAND" | sed "s/'[^']*'//g; s/\"[^\"]*\"//g")
HAS_COMMIT=false
HAS_PUSH=false
while IFS= read -r seg; do
  seg=$(echo "$seg" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
  [ -z "$seg" ] && continue
  if echo "$seg" | grep -qE '^git[[:space:]]+.*[[:space:]]commit|^git[[:space:]]+commit'; then
    HAS_COMMIT=true
  fi
  if echo "$seg" | grep -qE '^git[[:space:]]+.*[[:space:]]push|^git[[:space:]]+push'; then
    HAS_PUSH=true
  fi
done <<SEGMENTS
$(printf '%s\n' "$STRIPPED" | sed 's/&&/\n/g;s/;/\n/g;s/|/\n/g')
SEGMENTS

if [ "$HAS_COMMIT" = false ] && [ "$HAS_PUSH" = false ]; then
  exit 0
fi

ACTION="commit"
if [ "$HAS_PUSH" = true ]; then
  ACTION="push"
fi

GATES_CONFIG=""
for candidate in gates.json .claude/gates.json "$SCRIPT_DIR/gates.json"; do
  if [ -f "$candidate" ]; then
    GATES_CONFIG="$candidate"
    break
  fi
done

ENFORCEMENT="warn"
GATE_MODE="legacy"
if [ -n "$GATES_CONFIG" ] && command -v jq &> /dev/null; then
  ENFORCEMENT=$(jq -r '.enforcement // "warn"' "$GATES_CONFIG" 2>/dev/null)
  GATE_MODE=$(jq -r '.gate_mode // "legacy"' "$GATES_CONFIG" 2>/dev/null)
fi

gate_emit() {
  local level="$1"
  local msg="$2"
  local prefix="GATE WARNING"
  local exit_code=0
  if [ "$level" = "block" ]; then
    prefix="BLOCKED"
    exit_code=2
  fi
  local ctx="${prefix}: ${msg}"
  if command -v jq &> /dev/null; then
    jq -n --arg ctx "$ctx" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $ctx}}'
  else
    printf '%s\n' "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"$ctx\"}}"
  fi
  exit "$exit_code"
}

gate_finish() {
  local msg="$1"
  if [ "$ENFORCEMENT" = "block" ]; then
    gate_emit block "$msg"
  fi
  gate_emit warn "$msg"
}

VERIFY_SCRIPT=""
if [ -f ".agent-toolkit/gate/scripts/verify_gate.py" ]; then
  VERIFY_SCRIPT=".agent-toolkit/gate/scripts/verify_gate.py"
fi

if [ "$GATE_MODE" = "signed" ] && [ -n "$VERIFY_SCRIPT" ] && command -v python3 &> /dev/null; then
  COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
  OUTPUT=$(python3 "$VERIFY_SCRIPT" verify --action "$ACTION" --commit "$COMMIT_SHA" 2>&1) || EXIT_CODE=$?
  EXIT_CODE=${EXIT_CODE:-0}
  if [ "$EXIT_CODE" -ne 0 ]; then
    gate_finish "git ${ACTION} failed verify: ${OUTPUT}. Run precommit and evaluate; refresh gate token."
  fi
  exit 0
fi

if [ -z "$GATES_CONFIG" ] || ! command -v jq &> /dev/null; then
  if [ "$ACTION" = "commit" ]; then
    if [ ! -f ".gates/precommit-passed" ] || ! grep -q "READY" ".gates/precommit-passed" 2>/dev/null; then
      gate_finish "git commit requires precommit skill. Run install.sh in project root."
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
    MISSING="${MISSING} ${SKILL}"
    continue
  fi
  case "$SKILL" in
    precommit)
      grep -q "READY" "$FLAG" 2>/dev/null || MISSING="${MISSING} ${SKILL}(no READY)"
      ;;
    evaluate)
      EVAL_THRESHOLD=95
      CUSTOM=$(jq -r '.eval_threshold // empty' "$GATES_CONFIG" 2>/dev/null)
      [ -n "$CUSTOM" ] && EVAL_THRESHOLD="$CUSTOM"
      if ! grep -q "PASSED" "$FLAG" 2>/dev/null; then
        MISSING="${MISSING} ${SKILL}(no PASSED)"
      else
        SCORE=$(grep -oE '[0-9]+' "$FLAG" 2>/dev/null | head -1)
        if [ -z "$SCORE" ] || [ "$SCORE" -lt "$EVAL_THRESHOLD" ]; then
          MISSING="${MISSING} ${SKILL}(score ${SCORE:-0} below ${EVAL_THRESHOLD})"
        fi
      fi
      ;;
    reviewer|assess)
      grep -q "PASSED" "$FLAG" 2>/dev/null || MISSING="${MISSING} ${SKILL}(no PASSED)"
      ;;
  esac
done

if [ -n "$MISSING" ]; then
  MISSING_TRIMMED=$(echo "$MISSING" | xargs)
  gate_finish "git ${ACTION} needs skills:${MISSING_TRIMMED}. Run precommit and evaluate when ready."
fi

exit 0
