#!/bin/bash
# tdd-enforce.sh — Reminds agent about TDD before every file edit
#
# Runs as PreToolUse hook on Edit and Write tools.
# Checks if the file being edited is a source file (not a test).
# If so, injects context: "Did you write the test first?"
#
# Does NOT block — blocking Edit would break too many legitimate workflows.
# Instead, injects context that Claude sees before proceeding.

INPUT=$(cat)

# Extract file path — jq first, grep fallback
if command -v jq &> /dev/null; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"//;s/"$//')
fi

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

FILENAME=$(basename "$FILE_PATH")
DIRPATH=$(dirname "$FILE_PATH")

# Skip non-code files
case "$FILENAME" in
  *.md|*.json|*.yml|*.yaml|*.toml|*.cfg|*.ini|*.env*|*.txt|*.csv|*.lock|*.svg|*.png|*.jpg)
    exit 0
    ;;
esac

# Skip if this IS a test file
case "$FILENAME" in
  test_*|*_test.*|*.test.*|*.spec.*|*Test.*|*Spec.*)
    exit 0
    ;;
esac
case "$DIRPATH" in
  *test*|*__tests__*|*spec*)
    exit 0
    ;;
esac

# Skip config/setup files
case "$FILENAME" in
  *.config.*|Makefile|Dockerfile|docker-compose*|setup.*|*.sh)
    exit 0
    ;;
esac

# This is a source file, not a test — check if a corresponding test exists
TEST_EXISTS=false

# Common test file patterns — scoped search (same dir, tests/, __tests__, test/)
BASENAME="${FILENAME%.*}"
EXT="${FILENAME##*.}"
SRC_DIR=$(dirname "$FILE_PATH")

# Directories to check for test files (relative to project root)
TEST_DIRS="$SRC_DIR ${SRC_DIR}/../tests ${SRC_DIR}/../test ${SRC_DIR}/../__tests__ ./tests ./test ./__tests__"

for test_pattern in \
  "test_${BASENAME}.${EXT}" \
  "${BASENAME}_test.${EXT}" \
  "${BASENAME}.test.${EXT}" \
  "${BASENAME}.spec.${EXT}" \
  "${BASENAME}Test.${EXT}" \
  "${BASENAME}Spec.${EXT}"; do
  for dir in $TEST_DIRS; do
    if [ -f "$dir/$test_pattern" ] 2>/dev/null; then
      TEST_EXISTS=true
      break 2
    fi
  done
done

if [ "$TEST_EXISTS" = false ]; then
  # No test file found — strong TDD reminder (covers both new features AND bug fixes)
  MSG="TDD CHECK: You are editing $FILENAME but no corresponding test file exists.

FOR NEW FEATURES: Write the test FIRST with specific assertions, then implement.
FOR BUG FIXES: Write a FAILING test that reproduces the bug FIRST, then fix the code to make it pass. The test stays as a permanent regression test.

If this is a config/setup file that does not need tests, proceed."

  if command -v jq &> /dev/null; then
    jq -n --arg ctx "$MSG" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $ctx}}'
  else
    MSG_ESCAPED=$(echo "$MSG" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')
    cat <<TDD_EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "$MSG_ESCAPED"
  }
}
TDD_EOF
  fi
fi

exit 0
