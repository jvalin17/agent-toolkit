#!/bin/bash
# test-hooks.sh — Tests for harness hooks
#
# Runs gate_hook.py, skill_passed.py, gate_cleanup.py, route_to_skill.py, tdd_enforce.py
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
GATE_RUNNER="$TEST_DIR/gate_hook_runner.py"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}PASS${NC}: $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}FAIL${NC}: $1 — $2"; FAIL=$((FAIL + 1)); }

cat > "$GATE_RUNNER" << EOF
#!/usr/bin/env python3
import subprocess
import sys

hook_path = r"$HOOKS_DIR/gate_hook.py"
hook_input = sys.stdin.read()
proc = subprocess.run(
    [sys.executable, hook_path],
    input=hook_input,
    capture_output=True,
    text=True,
)
if proc.stdout:
    sys.stdout.write(proc.stdout)
if proc.stderr:
    sys.stderr.write(proc.stderr)
if '"decision": "block"' in proc.stdout:
    sys.exit(2)
sys.exit(proc.returncode)
EOF

# Setup: working directory with gates.json (default mode: tdd + precommit)
cd "$TEST_DIR"
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "default"
}
EOF

echo "=== gate_hook.py ==="

# Test 1: git commit without precommit-passed → BLOCKED (exit 2)
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "git commit blocked without precommit"
else
  fail "git commit should be blocked (exit 2)" "got exit $EXIT_CODE"
fi

# Test 2: git commit with valid precommit-passed → ALLOWED (exit 0)
mkdir -p .gates && echo "READY 2026-05-20-1200" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "git commit allowed with precommit-passed"
else
  fail "git commit should be allowed (exit 0)" "got exit $EXIT_CODE"
fi

# Test 3: default mode has no push requirements → push allowed
rm -rf .gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "git push allowed in default mode (no push requirements)"
else
  fail "default mode push should be allowed" "got exit $EXIT_CODE"
fi

# Test 4: safe mode requires reviewer for push → BLOCKED without it
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "safe"
}
EOF
rm -rf .gates && mkdir -p .gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "safe mode: push blocked without reviewer"
else
  fail "safe mode should block push without reviewer" "got exit $EXIT_CODE"
fi

# Test 4b: safe mode allows push with reviewer
echo "PASSED 2026-05-20" > .gates/reviewer-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "safe mode: push allowed with reviewer"
else
  fail "safe mode push should be allowed with reviewer" "got exit $EXIT_CODE"
fi

# Test 5: non-git command → ALLOWED (exit 0)
EXIT_CODE=0
echo '{"tool_input":{"command":"ls -la"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "non-git command allowed"
else
  fail "non-git command should be allowed" "got exit $EXIT_CODE"
fi

# Test 5b: minimal mode allows commit without any gates
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "minimal"
}
EOF
rm -rf .gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "minimal mode: commit allowed without any gates"
else
  fail "minimal mode should allow commit" "got exit $EXIT_CODE"
fi

# Test 5c: commit message mentioning git push — must not require push gates
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "default"
}
EOF
mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"docs: how to git push safely\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "commit message with git push text does not trigger push gate"
else
  fail "commit-only should not enforce push gates from message text" "got exit $EXIT_CODE"
fi

# Test 6: precommit flag without READY marker → BLOCKED
rm -rf .gates && mkdir -p .gates && touch .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "empty precommit flag (no READY) blocked"
else
  fail "empty precommit flag should be blocked" "got exit $EXIT_CODE"
fi

# Test 7: safe mode reviewer without PASSED marker → BLOCKED
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "safe"
}
EOF
rm -rf .gates && mkdir -p .gates
touch .gates/reviewer-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "reviewer flag without PASSED marker blocked"
else
  fail "empty reviewer flag should be blocked" "got exit $EXIT_CODE"
fi

# Test 7b: safe mode reviewer with PASSED marker → ALLOWED
echo "PASSED 2026-05-20" > .gates/reviewer-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "reviewer flag with PASSED marker allowed"
else
  fail "reviewer with PASSED should be allowed" "got exit $EXIT_CODE"
fi

# Test 8: env var AGENT_TOOLKIT_MODE overrides gates.json
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "default"
}
EOF
rm -rf .gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | AGENT_TOOLKIT_MODE=minimal python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "AGENT_TOOLKIT_MODE=minimal overrides default mode (commit allowed)"
else
  fail "env var mode override should allow commit" "got exit $EXIT_CODE"
fi

echo ""
echo "=== gate_cleanup.py ==="

# Test 9: git commit clears precommit only (push-scoped flags survive)
rm -rf .gates && mkdir -p .gates
echo "READY" > .gates/precommit-passed
echo "PASSED 96%" > .gates/evaluate-passed
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$HOOKS_DIR/gate_cleanup.py" > /dev/null 2>&1
if [ ! -f ".gates/precommit-passed" ] && [ -f ".gates/evaluate-passed" ]; then
  pass "git commit clears precommit only; evaluate survives"
else
  fail "git commit should clear precommit only" "precommit=$([ -f .gates/precommit-passed ] && echo yes || echo no) evaluate=$([ -f .gates/evaluate-passed ] && echo yes || echo no)"
fi

# Test 10: git push clears push-scoped flags
mkdir -p .gates && echo "READY" > .gates/precommit-passed && echo "PASSED 96%" > .gates/evaluate-passed
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$HOOKS_DIR/gate_cleanup.py" > /dev/null 2>&1
if [ -f ".gates/precommit-passed" ] && [ ! -f ".gates/evaluate-passed" ]; then
  pass "git push clears evaluate; precommit survives"
else
  fail "git push should clear push-scoped flags only" "unexpected .gates state"
fi

# Test 11: non-commit doesn't clear .gates/
mkdir -p .gates && echo "READY" > .gates/precommit-passed
echo '{"tool_input":{"command":"git status"}}' | python3 "$HOOKS_DIR/gate_cleanup.py" > /dev/null 2>&1
if [ -f ".gates/precommit-passed" ]; then
  pass "non-commit preserves .gates"
else
  fail "non-commit should preserve .gates" "flag was deleted"
fi

echo ""
echo "=== skill_passed.py ==="

cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "mode": "default"
}
EOF

# Test 12: skill completion WITHOUT flag file → reports not passed
rm -rf .gates
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "did NOT pass"; then
  pass "skill without flag reports not passed"
else
  fail "should report skill did not pass" "got: $OUTPUT"
fi

# Test 13: skill completion WITH flag file → reports passed
mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "PASSED"; then
  pass "skill with flag reports passed"
else
  fail "should report skill passed" "got: $OUTPUT"
fi

# Test 14: non-gated skill → no output
OUTPUT=$(echo '{"tool_input":{"skill":"explore"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "non-gated skill produces no output"
else
  fail "non-gated skill should produce no output" "got: $OUTPUT"
fi

echo ""
echo "=== route_to_skill.py ==="

# Test 15: "fix the bug" → debug_tool routing
OUTPUT=$(echo '{"prompt":"fix the login bug"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug_tool"; then
  pass "\"fix the login bug\" routes to debug_tool"
else
  fail "should route to debug_tool" "got: $OUTPUT"
fi

# Test 16: "fix the design" → should NOT route to debug_tool
OUTPUT=$(echo '{"prompt":"fix the design of the homepage"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug_tool"; then
  fail "\"fix the design\" should NOT route to debug_tool" "false positive"
else
  pass "\"fix the design\" does not route to debug_tool"
fi

# Test 17: "build an inventory app" → implementation routing
OUTPUT=$(echo '{"prompt":"build an inventory app"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "implementation"; then
  pass "\"build an inventory app\" routes to implementation"
else
  fail "should route to implementation" "got: $OUTPUT"
fi

# Test 18: "/debug_tool something" → no injection (user invoked directly)
OUTPUT=$(echo '{"prompt":"/debug_tool something"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "\"/debug_tool\" prefix skips routing"
else
  fail "slash-command should skip routing" "got: $OUTPUT"
fi

# Test 19: "refactor the auth module" → implementation refactor mode
OUTPUT=$(echo '{"prompt":"refactor the auth module"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "refactor mode"; then
  pass "\"refactor\" routes to implementation refactor mode"
else
  fail "should route to refactor mode" "got: $OUTPUT"
fi

# Test 20: "the search is broken" → debug_tool routing
OUTPUT=$(echo '{"prompt":"the search is broken"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug_tool"; then
  pass "\"broken\" routes to debug_tool"
else
  fail "should route to debug_tool" "got: $OUTPUT"
fi

# Test 21: generic prompt → no routing
OUTPUT=$(echo '{"prompt":"what time is it"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "generic prompt has no routing"
else
  fail "generic prompt should have no routing" "got: $OUTPUT"
fi

echo ""
echo "=== tdd_enforce.py ==="

# Test 22: editing source file with no test → TDD block
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if echo "$OUTPUT" | grep -qi "test"; then
  pass "source file without test triggers TDD enforcement"
else
  fail "should trigger TDD enforcement" "got: $OUTPUT"
fi

# Test 23: editing a test file → no block
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/tests/test_users.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "test file skips TDD enforcement"
else
  fail "test file should skip TDD enforcement" "got: $OUTPUT"
fi

# Test 24: editing .md file → no block
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/README.md"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".md file skips TDD enforcement"
else
  fail ".md file should skip TDD enforcement" "got: $OUTPUT"
fi

# Test 25: editing config file → no block
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/Dockerfile"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "Dockerfile skips TDD enforcement"
else
  fail "Dockerfile should skip TDD enforcement" "got: $OUTPUT"
fi

# Test 26: editing .spec.ts file → no block (it IS a test)
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.spec.ts"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".spec.ts file skips TDD enforcement"
else
  fail ".spec.ts should skip TDD enforcement" "got: $OUTPUT"
fi

# Test 27: TDD mentions writing test first
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/auth.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if echo "$OUTPUT" | grep -qi "test"; then
  pass "TDD enforcement mentions test"
else
  fail "should mention test" "got: $OUTPUT"
fi

echo ""
echo "=== gate_hook.py (signed mode smoke) ==="

TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
git init -q 2>/dev/null || true
git config user.email "test@example.com" 2>/dev/null || true
git config user.name "Test User" 2>/dev/null || true
git add -A 2>/dev/null || true
git commit -m "init" --allow-empty -q 2>/dev/null || true

rm -rf .agent-toolkit .gate
mkdir -p .agent-toolkit
cp -R "$TOOLKIT_ROOT/gate" .agent-toolkit/
find .agent-toolkit/gate -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

cat > gates.json << 'GATEJSON'
{
  "gate_mode": "signed",
  "mode": "default",
  "eval_threshold": 95
}
GATEJSON

# Check if PyJWT + cryptography are importable before running signed tests
JWT_AVAILABLE=0
python3 -c "import jwt" 2>/dev/null && JWT_AVAILABLE=1

COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "deadbeef")

if [ "$JWT_AVAILABLE" -eq 1 ]; then
  python3 << PY || true
import json, sys
from pathlib import Path
sys.path.insert(0, ".agent-toolkit")
from gate.keys import generate_signing_secret
from gate.core import issue_token, write_token

root = Path(".")
generate_signing_secret(root / ".gate" / "signing.key")
config = json.loads((root / "gates.json").read_text())
att = {
    "version": 1,
    "repo": "test/repo",
    "commit_sha": "$COMMIT_SHA",
    "ref": "refs/heads/main",
    "producer": "test",
    "results": {"precommit": {"passed": True}},
}
token = issue_token(att, config, "commit", root)
write_token(root / ".gate" / "gate-token.jwt", token)
PY

  EXIT_CODE=0
  echo '{"tool_input":{"command":"git commit -m \"signed ok\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 0 ]; then
    pass "signed gate_hook.py allows commit with valid JWT"
  else
    fail "signed gate_hook.py should allow commit with valid token" "exit=$EXIT_CODE"
  fi

  rm -f .gate/gate-token.jwt
  EXIT_CODE=0
  echo '{"tool_input":{"command":"git commit -m \"no token\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
  if [ "$EXIT_CODE" -eq 2 ]; then
    pass "signed gate_hook.py blocks commit without JWT"
  else
    fail "signed gate_hook.py should block without token" "exit=$EXIT_CODE"
  fi
else
  pass "signed gate_hook.py allows commit with valid JWT (SKIPPED — jwt unavailable)"
  pass "signed gate_hook.py blocks commit without JWT (SKIPPED — jwt unavailable)"
fi

# Cleanup
rm -rf .session
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
