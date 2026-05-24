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

# Setup: working directory with gates.json
cd "$TEST_DIR"
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
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

# Test 3: git push without evaluate-passed → BLOCKED
rm -rf .gates && mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "git push blocked without evaluate-passed"
else
  fail "git push should be blocked (exit 2)" "got exit $EXIT_CODE"
fi

# Test 4: git push with both valid flags → ALLOWED
echo "PASSED 96% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "git push allowed with all flags"
else
  fail "git push should be allowed (exit 0)" "got exit $EXIT_CODE"
fi

# Test 4b: git commit && git push — must enforce push gates (not commit-only)
rm -rf .gates && mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\" && git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "commit && push blocked without evaluate (push gates enforced)"
else
  fail "commit && push should be blocked without evaluate" "got exit $EXIT_CODE"
fi

# Test 4c: git -C subdir push — still enforces push gates
rm -rf .gates && mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git -C /tmp/repo push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "git -C dir push blocked without evaluate"
else
  fail "git -C push should be blocked without evaluate" "got exit $EXIT_CODE"
fi

# Test 4d: commit; push (semicolon) — push gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"x\"; git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "commit; push blocked without evaluate"
else
  fail "commit; push should be blocked" "got exit $EXIT_CODE"
fi

# Test 4e: commit && push allowed when all flags present
echo "PASSED 96% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\" && git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "commit && push allowed with all flags"
else
  fail "commit && push should be allowed" "got exit $EXIT_CODE"
fi

# Test 5: non-git command → ALLOWED (exit 0)
EXIT_CODE=0
echo '{"tool_input":{"command":"ls -la"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "non-git command allowed"
else
  fail "non-git command should be allowed" "got exit $EXIT_CODE"
fi

# Test 5b: enforcement warn — missing flags still exit 0 (advisory for Cursor/LLMs)
rm -rf .gates
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "warn",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
EOF
EXIT_CODE=0
OUT=$(echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" 2>&1) || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ] && echo "$OUT" | grep -q "GATE WARNING"; then
  pass "warn mode: commit without flags exits 0 with warning"
else
  fail "warn mode should exit 0 with GATE WARNING" "exit=$EXIT_CODE out=$OUT"
fi
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
EOF

# Test 5c: commit message mentioning git push — must not require push gates
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

# Test 7: evaluate flag with 40% score → BLOCKED (for push)
rm -rf .gates && mkdir -p .gates
echo "READY 2026-05-20" > .gates/precommit-passed
echo "PASSED 40% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "evaluate flag with 40% score blocked for push"
else
  fail "low eval score should block push" "got exit $EXIT_CODE"
fi

# Test 7b: evaluate flag with 94% → BLOCKED (below 95% default threshold)
rm -rf .gates && mkdir -p .gates
echo "READY 2026-05-20" > .gates/precommit-passed
echo "PASSED 94% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "evaluate at 94% blocked (below 95% threshold)"
else
  fail "94% should be blocked (threshold is 95%)" "got exit $EXIT_CODE"
fi

# Test 7c: evaluate flag with 95% → ALLOWED
rm -rf .gates && mkdir -p .gates
echo "READY 2026-05-20" > .gates/precommit-passed
echo "PASSED 95% 2026-05-20" > .gates/evaluate-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "evaluate at 95% allowed (meets threshold)"
else
  fail "95% should be allowed" "got exit $EXIT_CODE"
fi

# Test 7d: reviewer flag without PASSED marker → BLOCKED
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate", "reviewer"]
}
EOF
rm -rf .gates && mkdir -p .gates
echo "READY 2026-05-20" > .gates/precommit-passed
echo "PASSED 96% 2026-05-20" > .gates/evaluate-passed
touch .gates/reviewer-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "reviewer flag without PASSED marker blocked"
else
  fail "empty reviewer flag should be blocked" "got exit $EXIT_CODE"
fi

# Test 7e: reviewer flag with PASSED marker → ALLOWED
echo "PASSED 2026-05-20" > .gates/reviewer-passed
EXIT_CODE=0
echo '{"tool_input":{"command":"git push origin main"}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
  pass "reviewer flag with PASSED marker allowed"
else
  fail "reviewer with PASSED should be allowed" "got exit $EXIT_CODE"
fi

# Restore default gates.json
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
EOF

# Test 8: profile-based gates
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "block",
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
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "strict profile: commit blocked without evaluate"
else
  fail "strict profile should block commit without evaluate" "got exit $EXIT_CODE"
fi

echo ""
echo "=== gate_cleanup.py ==="

# Test 9: git commit clears .gates/
rm -rf .gates && mkdir -p .gates
echo "READY" > .gates/precommit-passed
echo "PASSED 96%" > .gates/evaluate-passed
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$HOOKS_DIR/gate_cleanup.py" > /dev/null 2>&1
if [ ! -d ".gates" ]; then
  pass "git commit clears .gates directory"
else
  fail "git commit should clear .gates" "directory still exists"
fi

# Test 10: non-commit doesn't clear .gates/
mkdir -p .gates && echo "READY" > .gates/precommit-passed
echo '{"tool_input":{"command":"git status"}}' | python3 "$HOOKS_DIR/gate_cleanup.py" > /dev/null 2>&1
if [ -f ".gates/precommit-passed" ]; then
  pass "non-commit preserves .gates"
else
  fail "non-commit should preserve .gates" "flag was deleted"
fi

echo ""
echo "=== skill_passed.py ==="

# Test 9: skill completion WITHOUT flag file → reports not passed
rm -rf .gates
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "did NOT pass"; then
  pass "skill without flag reports not passed"
else
  fail "should report skill did not pass" "got: $OUTPUT"
fi

# Test 12: skill completion WITH flag file → reports passed
mkdir -p .gates && echo "READY 2026-05-20" > .gates/precommit-passed
OUTPUT=$(echo '{"tool_input":{"skill":"precommit"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "PASSED"; then
  pass "skill with flag reports passed"
else
  fail "should report skill passed" "got: $OUTPUT"
fi

# Test 11: non-gated skill → no output
OUTPUT=$(echo '{"tool_input":{"skill":"explore"}}' | python3 "$HOOKS_DIR/skill_passed.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "non-gated skill produces no output"
else
  fail "non-gated skill should produce no output" "got: $OUTPUT"
fi

echo ""
echo "=== route_to_skill.py ==="

# Test 12: "fix the bug" → debug routing
OUTPUT=$(echo '{"prompt":"fix the login bug"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  pass "\"fix the login bug\" routes to debug"
else
  fail "should route to debug" "got: $OUTPUT"
fi

# Test 13: "fix the design" → should NOT route to debug
OUTPUT=$(echo '{"prompt":"fix the design of the homepage"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  fail "\"fix the design\" should NOT route to debug" "false positive"
else
  pass "\"fix the design\" does not route to debug"
fi

# Test 14: "build an inventory app" → implementation routing
OUTPUT=$(echo '{"prompt":"build an inventory app"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "implementation"; then
  pass "\"build an inventory app\" routes to implementation"
else
  fail "should route to implementation" "got: $OUTPUT"
fi

# Test 15: "/debug something" → no injection (user invoked directly)
OUTPUT=$(echo '{"prompt":"/debug something"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "\"/debug\" prefix skips routing"
else
  fail "slash-command should skip routing" "got: $OUTPUT"
fi

# Test 16: "refactor the auth module" → implementation refactor mode
OUTPUT=$(echo '{"prompt":"refactor the auth module"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "refactor mode"; then
  pass "\"refactor\" routes to implementation refactor mode"
else
  fail "should route to refactor mode" "got: $OUTPUT"
fi

# Test 17: "the search is broken" → debug routing
OUTPUT=$(echo '{"prompt":"the search is broken"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "debug"; then
  pass "\"broken\" routes to debug"
else
  fail "should route to debug" "got: $OUTPUT"
fi

# Test 18: generic prompt → no routing
OUTPUT=$(echo '{"prompt":"what time is it"}' | python3 "$HOOKS_DIR/route_to_skill.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "generic prompt has no routing"
else
  fail "generic prompt should have no routing" "got: $OUTPUT"
fi

echo ""
echo "=== tdd_enforce.py ==="

# Test 19: editing source file with no test → TDD reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "TDD CHECK"; then
  pass "source file without test triggers TDD reminder"
else
  fail "should trigger TDD reminder" "got: $OUTPUT"
fi

# Test 20: editing a test file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/tests/test_users.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "test file skips TDD reminder"
else
  fail "test file should skip TDD reminder" "got: $OUTPUT"
fi

# Test 21: editing .md file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/README.md"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".md file skips TDD reminder"
else
  fail ".md file should skip TDD reminder" "got: $OUTPUT"
fi

# Test 22: editing config file → no reminder
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/Dockerfile"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass "Dockerfile skips TDD reminder"
else
  fail "Dockerfile should skip TDD reminder" "got: $OUTPUT"
fi

# Test 23: editing .spec.ts file → no reminder (it IS a test)
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/users.spec.ts"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if [ -z "$OUTPUT" ]; then
  pass ".spec.ts file skips TDD reminder"
else
  fail ".spec.ts should skip TDD reminder" "got: $OUTPUT"
fi

# Test 24: TDD reminder mentions bug fix workflow
OUTPUT=$(echo '{"tool_input":{"file_path":"/app/src/auth.py"}}' | python3 "$HOOKS_DIR/tdd_enforce.py" 2>/dev/null)
if echo "$OUTPUT" | grep -q "BUG FIX"; then
  pass "TDD reminder includes bug fix workflow"
else
  fail "should mention bug fix workflow" "got: $OUTPUT"
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
  "enforcement": "block",
  "profile": "minimal",
  "eval_threshold": 95,
  "profiles": {
    "minimal": {
      "commit_requires": ["precommit"],
      "push_requires": ["precommit"]
    }
  }
}
GATEJSON

COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "deadbeef")
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

cat > gates.json << 'GATEJSON'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
GATEJSON

echo ""
echo "=== gate_hook.py enforcement escalation ==="

# Reset to warn mode
cat > gates.json << 'EOF'
{
  "gate_mode": "legacy",
  "enforcement": "warn",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
EOF
rm -rf .gates

# Test: env var AGENT_TOOLKIT_ENFORCEMENT overrides gates.json
EXIT_CODE=0
AGENT_TOOLKIT_ENFORCEMENT=block echo '{"tool_input":{"command":"git commit -m \"test\""}}' | AGENT_TOOLKIT_ENFORCEMENT=block python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "env var AGENT_TOOLKIT_ENFORCEMENT=block overrides warn mode"
else
  fail "env var should override to block (exit 2)" "got exit $EXIT_CODE"
fi

# Test: .gates/enforcement-override file overrides gates.json
mkdir -p .gates
echo "block" > .gates/enforcement-override
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass ".gates/enforcement-override=block overrides warn mode"
else
  fail "override file should escalate to block (exit 2)" "got exit $EXIT_CODE"
fi
rm -f .gates/enforcement-override

# Test: warn mode auto-escalates — first violation writes override file
rm -rf .gates
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"test\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ] && [ -f ".gates/enforcement-override" ] && grep -q "block" .gates/enforcement-override 2>/dev/null; then
  pass "warn mode auto-escalates: writes enforcement-override on first violation"
else
  fail "first violation should create .gates/enforcement-override=block" "exit=$EXIT_CODE, file exists=$([ -f .gates/enforcement-override ] && echo yes || echo no)"
fi

# Test: subsequent commit after escalation is hard-blocked
EXIT_CODE=0
echo '{"tool_input":{"command":"git commit -m \"second attempt\""}}' | python3 "$GATE_RUNNER" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 2 ]; then
  pass "second commit after escalation is hard-blocked"
else
  fail "post-escalation should block (exit 2)" "got exit $EXIT_CODE"
fi

rm -rf .gates

# Restore block mode for remaining cleanup
cat > gates.json << 'GATEJSON'
{
  "gate_mode": "legacy",
  "enforcement": "block",
  "commit_requires": ["precommit"],
  "push_requires": ["precommit", "evaluate"]
}
GATEJSON

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
