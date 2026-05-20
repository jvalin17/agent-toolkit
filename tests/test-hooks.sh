#!/bin/bash
# test-hooks.sh — Tests for harness hooks
#
# Runs gate.sh, skill-passed.sh, gate-cleanup.sh, route-to-skill.sh
# with fixture JSON inputs and verifies correct behavior.
#
# Usage: ./tests/test-hooks.sh
# Exit code: 0 = all pass, 1 = failures

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOKS_DIR="$(dirname "$SCRIPT_DIR")/hooks"
PASS=0
FAIL=0
TEST_DIR=$(mktemp -d)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}PASS${NC}: $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}FAIL${NC}: $1 — $2"; FAIL=$((FAIL + 1)); }

# Setup: working directory with gates.json
cd "$TEST_DIR"
cat > gates.json << 'EOF'
{
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
EOF

echo "=== gate.sh ==="

# Test 1: git commit without precommit-passed → BLOCKED (exit 2)
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "git commit blocked without precommit"
else
  fail "git commit should be blocked (exit 2)" "got exit $EXIT_CODE"
fi

# Test 2: git commit with valid precommit-passed → ALLOWED (exit 0)
mkdir -p .gates && echo "READY 2026-05-20-1200" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "git commit allowed with precommit-passed"
else
  fail "git commit should be allowed (exit 0)" "got exit $EXIT_CODE"
fi

# Test 3: git push without evaluate-passed → BLOCKED
rm -rf .gates && mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "git push blocked without evaluate-passed"
else
  fail "git push should be blocked (exit 2)" "got exit $EXIT_CODE"
fi

# Test 4: git push with both valid flags → ALLOWED
echo "PASSED 96% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "git push allowed with all flags"
else
  fail "git push should be allowed (exit 0)" "got exit $EXIT_CODE"
fi

# Test 5: non-git command → ALLOWED (exit 0)
EXIT_CODE=0
echo '{"tool_input":{"command":"ls -la"}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "non-git command allowed"
else
  fail "non-git command should be allowed" "got exit $EXIT_CODE"
fi

# Test 6: precommit flag without READY marker → BLOCKED
rm -rf .gates && mkdir -p .gates && touch .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "empty precommit flag (no READY) blocked"
else
  fail "empty precommit flag should be blocked" "got exit $EXIT_CODE"
fi

# Test 7: evaluate flag with low score → BLOCKED (for push)
rm -rf .gates && mkdir -p .gates
echo "READY 2026-05-20" > .gates/precommit-passed
echo "PASSED 40% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "evaluate flag with 40% score blocked for push"
else
  fail "low eval score should block push" "got exit $EXIT_CODE"
fi

# Test 8: profile-based gates
cat > gates.json << 'EOF'
{
  "profile": "strict",
  "profiles": {
    "strict": {
      "commit_requires": ["precommit", "evaluate"],
      "push_requires": ["precommit", "evaluate", "reviewer"]
    }
  }
}
EOF
rm -rf .gates && mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | "$HOOKS_DIR/gate.sh" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "strict profile: commit blocked without evaluate"
else
  fail "strict profile should block commit without evaluate" "got exit $EXIT_CODE"
fi

echo ""
echo "=== gate-cleanup.sh ==="

# Test 9: git commit clears .gates/
rm -rf .gates && mkdir -p .gates
echo "READY" > .gates/precommit-passed
echo "PASSED 96%" > .gates/evaluate-passed
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | "$HOOKS_DIR/gate-cleanup.sh" > /dev/null 2>&1
if [ ! -d ".gates" ]; then
  pass "git commit clears .gates directory"
else
  fail "git commit should clear .gates" "directory still exists"
fi

# Test 10: non-commit doesn't clear .gates/
mkdir -p .gates && echo "READY" > .gates/precommit-passed
echo '{"tool_input":{"command":"git status"}}' | "$HOOKS_DIR/gate-cleanup.sh" > /dev/null 2>&1
if [ -f ".gates/precommit-passed" ]; then
  pass "non-commit preserves .gates"
else
  fail "non-commit should preserve .gates" "flag was deleted"
fi

echo ""
echo "=== skill-passed.sh ==="

# Test 9: skill completion WITHOUT flag file → reports not passed
rm -rf .gates
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | "$HOOKS_DIR/skill-passed.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "did NOT pass"; then
  pass "skill without flag reports not passed"
else
  fail "should report skill did not pass" "got: $OUTPUT"
fi

# Test 12: skill completion WITH flag file → reports passed
mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | "$HOOKS_DIR/skill-passed.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "PASSED"; then
  pass "skill with flag reports passed"
else
  fail "should report skill passed" "got: $OUTPUT"
fi

# Test 11: non-gated skill → no output
OUTPUT=$(echo '{"tool_input":{"skill":"explore"}}' | "$HOOKS_DIR/skill-passed.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "non-gated skill produces no output"
else
  fail "non-gated skill should produce no output" "got: $OUTPUT"
fi

echo ""
echo "=== route-to-skill.sh ==="

# Test 12: "fix the bug" → debug routing
OUTPUT=$(echo '{"prompt":"fix the login bug"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  pass "\"fix the login bug\" routes to debug"
else
  fail "should route to debug" "got: $OUTPUT"
fi

# Test 13: "fix the design" → should NOT route to debug
OUTPUT=$(echo '{"prompt":"fix the design of the homepage"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  fail "\"fix the design\" should NOT route to debug" "false positive"
else
  pass "\"fix the design\" does not route to debug"
fi

# Test 14: "build an inventory app" → implementation routing
OUTPUT=$(echo '{"prompt":"build an inventory app"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "implementation"; then
  pass "\"build an inventory app\" routes to implementation"
else
  fail "should route to implementation" "got: $OUTPUT"
fi

# Test 15: "/debug something" → no injection (user invoked directly)
OUTPUT=$(echo '{"prompt":"/debug something"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "\"/debug\" prefix skips routing"
else
  fail "slash-command should skip routing" "got: $OUTPUT"
fi

# Test 16: "refactor the auth module" → implementation refactor mode
OUTPUT=$(echo '{"prompt":"refactor the auth module"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "refactor mode"; then
  pass "\"refactor\" routes to implementation refactor mode"
else
  fail "should route to refactor mode" "got: $OUTPUT"
fi

# Test 17: "the search is broken" → debug routing
OUTPUT=$(echo '{"prompt":"the search is broken"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  pass "\"broken\" routes to debug"
else
  fail "should route to debug" "got: $OUTPUT"
fi

# Test 18: generic prompt → no routing
OUTPUT=$(echo '{"prompt":"what time is it"}' | "$HOOKS_DIR/route-to-skill.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "generic prompt has no routing"
else
  fail "generic prompt should have no routing" "got: $OUTPUT"
fi

echo ""
echo "=== tdd-enforce.sh ==="

# Test 19: editing source file with no test → TDD reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.py"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "TDD CHECK"; then
  pass "source file without test triggers TDD reminder"
else
  fail "should trigger TDD reminder" "got: $OUTPUT"
fi

# Test 20: editing a test file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/tests/test_users.py"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "test file skips TDD reminder"
else
  fail "test file should skip TDD reminder" "got: $OUTPUT"
fi

# Test 21: editing .md file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/README.md"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".md file skips TDD reminder"
else
  fail ".md file should skip TDD reminder" "got: $OUTPUT"
fi

# Test 22: editing config file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/Dockerfile"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "Dockerfile skips TDD reminder"
else
  fail "Dockerfile should skip TDD reminder" "got: $OUTPUT"
fi

# Test 23: editing .spec.ts file → no reminder (it IS a test)
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.spec.ts"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".spec.ts file skips TDD reminder"
else
  fail ".spec.ts should skip TDD reminder" "got: $OUTPUT"
fi

# Test 24: TDD reminder mentions bug fix workflow
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/auth.py"}}' | "$HOOKS_DIR/tdd-enforce.sh" 2>/dev/null)
if echo "$OUTPUT" | grep -q "BUG FIX"; then
  pass "TDD reminder includes bug fix workflow"
else
  fail "should mention bug fix workflow" "got: $OUTPUT"
fi

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "=== Results ==="
echo -e "Passed: ${GREEN}${PASS}${NC}, Failed: ${RED}${FAIL}${NC}"
if [ "$FAIL" -gt 0 ]; then
  exit 1
else
  echo "All hook tests passed."
  exit 0
fi
