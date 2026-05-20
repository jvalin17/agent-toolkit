#!/bin/bash
# setup-signed-gates.sh — Optional signed gates for a project (5-minute path).
#
# Usage (from your app repo, or pass project path):
#   /path/to/agent-toolkit/scripts/setup-signed-gates.sh
#   /path/to/agent-toolkit/scripts/setup-signed-gates.sh --upload-github-secret
#   /path/to/agent-toolkit/scripts/setup-signed-gates.sh /path/to/my-app
#
# Does not change anything if you stay on legacy — run only when you want signed mode.

set -e

TOOLKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT=""
UPLOAD_SECRET=0
PROFILE="standard"
ENFORCEMENT="block"

usage() {
  sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --upload-github-secret) UPLOAD_SECRET=1; shift ;;
    --warn) ENFORCEMENT="warn"; shift ;;
    --profile)
      PROFILE="${2:?profile name required}"
      shift 2
      ;;
    *)
      if [ -z "$PROJECT_ROOT" ]; then
        PROJECT_ROOT="$1"
      else
        echo "Unknown argument: $1" >&2
        usage
      fi
      shift
      ;;
  esac
done

if [ -z "$PROJECT_ROOT" ]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
  else
    echo "Error: not inside a git repo. Pass project path:" >&2
    echo "  $0 /path/to/your-app" >&2
    exit 1
  fi
fi

PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required. Install jq (brew install jq / apt install jq)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required." >&2
  exit 1
fi

echo "=== Signed gate setup ==="
echo "Project: $PROJECT_ROOT"
echo ""

# 1. Layout (idempotent)
echo "[1/5] Bootstrap gate layout (.agent-toolkit, signing key, workflow)..."
bash "$TOOLKIT_DIR/scripts/bootstrap-project-gates.sh" "$TOOLKIT_DIR" "$PROJECT_ROOT"

# 2. gates.json → signed
GATES_FILE="$PROJECT_ROOT/gates.json"
if [ ! -f "$GATES_FILE" ]; then
  cp "$TOOLKIT_DIR/templates/gates.json" "$GATES_FILE"
fi
TMP="$(mktemp)"
jq --arg profile "$PROFILE" --arg enforcement "$ENFORCEMENT" \
  '.gate_mode = "signed" | .profile = $profile | .enforcement = $enforcement' \
  "$GATES_FILE" > "$TMP" && mv "$TMP" "$GATES_FILE"
echo "[2/5] gates.json → gate_mode=signed, profile=$PROFILE, enforcement=$ENFORCEMENT"

# 3. Signing key
KEY_FILE="$PROJECT_ROOT/.gate/signing.key"
if [ ! -f "$KEY_FILE" ]; then
  (cd "$PROJECT_ROOT" && python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '.agent-toolkit')
from gate.keys import generate_signing_secret
generate_signing_secret(Path('.gate/signing.key'), Path('.gate/signing.meta.json'))
")
fi
echo "[3/5] Signing key: $KEY_FILE (gitignored — back this up if you use multiple machines)"

# 4. Optional GitHub secret
if [ "$UPLOAD_SECRET" -eq 1 ]; then
  echo "[4/5] Uploading AGENT_TOOLKIT_GATE_SECRET to this GitHub repo..."
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh secret set AGENT_TOOLKIT_GATE_SECRET < "$KEY_FILE"
    echo "       Secret set. CI and local will use the same key."
  else
    echo "       Skip: install gh and run 'gh auth login', then re-run with --upload-github-secret" >&2
    echo "       Or manually: Repo → Settings → Secrets → Actions → AGENT_TOOLKIT_GATE_SECRET" >&2
    echo "       Value: contents of $KEY_FILE" >&2
  fi
else
  echo "[4/5] GitHub secret skipped (CI still works per-run via .gate/signing.key in the workflow)."
  echo "       For stable tokens on laptop + CI, re-run: $0 --upload-github-secret"
fi

# 5. Smoke test
echo "[5/5] Smoke test (attest → issue → verify)..."
export AGENT_TOOLKIT_ATTEST_SKIP_HOOK_TESTS=1
export AGENT_TOOLKIT_ATTEST_SKIP_GATE_TESTS=1
FIXTURES="$TOOLKIT_DIR/tests/fixtures/gate-reports"
if [ -d "$FIXTURES" ] && [ ! -f "$PROJECT_ROOT/reports/precommit/pc_toolkit_ci.md" ]; then
  for skill in precommit evaluate reviewer assess; do
    mkdir -p "$PROJECT_ROOT/reports/$skill"
  done
  cp "$FIXTURES/pc_toolkit_ci.md" "$PROJECT_ROOT/reports/precommit/" 2>/dev/null || true
  cp "$FIXTURES/eval_toolkit_ci.md" "$PROJECT_ROOT/reports/evaluate/" 2>/dev/null || true
  cp "$FIXTURES/review_toolkit_ci.md" "$PROJECT_ROOT/reports/reviewer/" 2>/dev/null || true
  cp "$FIXTURES/assess_toolkit_ci.md" "$PROJECT_ROOT/reports/assess/" 2>/dev/null || true
  echo "       Seeded sample reports/ for smoke test (replace with your skill reports in production)."
fi
(cd "$PROJECT_ROOT" && pip install -q -r .agent-toolkit/gate/requirements.txt 2>/dev/null || true)
(cd "$PROJECT_ROOT" && python3 .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .) || {
  echo "       Attest failed — add skill reports under reports/ and fix failing tests, then re-run." >&2
  exit 1
}
(cd "$PROJECT_ROOT" && python3 .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push)
(cd "$PROJECT_ROOT" && python3 .agent-toolkit/gate/scripts/verify_gate.py verify --project-root . --action push) || {
  echo "       Verify failed — check signing key and gates.json profile." >&2
  exit 1
}
echo "       OK: signed gate roundtrip works locally."
echo ""
echo "=== Done ==="
echo ""
echo "Daily workflow:"
echo "  1. Run skills (/precommit, /evaluate, … per profile in gates.json)"
echo "  2. Before commit/push:"
echo "     python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root ."
echo "     python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push"
echo "  3. git commit / git push (hook checks .gate/gate-token.jwt)"
echo ""
echo "Team / production (optional):"
echo "  • Push to GitHub — workflow agent-toolkit-gate runs on PR/push"
echo "  • Branch protection on main: require status check 'agent-toolkit-gate'"
if [ "$UPLOAD_SECRET" -eq 0 ]; then
  echo "  • Same key on CI + laptop: $0 --upload-github-secret"
fi
echo ""
echo "Revert to legacy: scripts/set-gate-mode.sh legacy"
