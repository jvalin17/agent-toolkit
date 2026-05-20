#!/bin/bash
# bootstrap-project-gates.sh — Configure signed gates in the current git project.
# Called automatically from install.sh. Idempotent.

set -e

TOOLKIT_DIR="${1:-}"
PROJECT_ROOT="${2:-}"

if [ -z "$TOOLKIT_DIR" ]; then
  TOOLKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

if [ -z "$PROJECT_ROOT" ]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
  else
    echo "  [skip] project gates — not inside a git repository"
    exit 0
  fi
fi

PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
TOOLKIT_VERSION="$(git -C "$TOOLKIT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")"

echo ""
echo "Configuring signed gates in: $PROJECT_ROOT"

AGENT_DIR="$PROJECT_ROOT/.agent-toolkit"
GATE_DIR="$AGENT_DIR/gate"
mkdir -p "$AGENT_DIR"

# Sync gate module into project (self-contained for CI)
rm -rf "$GATE_DIR"
mkdir -p "$GATE_DIR"
cp -R "$TOOLKIT_DIR/gate/." "$GATE_DIR/"
# Remove __pycache__ if any
find "$GATE_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

cat > "$AGENT_DIR/config.json" << EOF
{
  "toolkit_path": "$TOOLKIT_DIR",
  "toolkit_version": "$TOOLKIT_VERSION",
  "gate_mode": "signed",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
echo "  [installed] .agent-toolkit/config.json"

# gates.json
if [ ! -f "$PROJECT_ROOT/gates.json" ]; then
  cp "$TOOLKIT_DIR/templates/gates.json" "$PROJECT_ROOT/gates.json"
  echo "  [installed] gates.json (profile: standard, mode: signed)"
else
  echo "  [skip] gates.json (already exists)"
fi

# Signing keys (gitignored) — per-project OR shared (~/.config/agent-toolkit/gate/)
GATE_LOCAL="$PROJECT_ROOT/.gate"
mkdir -p "$GATE_LOCAL"
SHARED_KEY="$HOME/.config/agent-toolkit/gate/signing.key"
USE_SHARED=""
if [ -f "$PROJECT_ROOT/gates.json" ] && command -v jq &> /dev/null; then
  USE_SHARED=$(jq -r '.signing // "project"' "$PROJECT_ROOT/gates.json" 2>/dev/null)
fi
if [ "$USE_SHARED" = "shared" ] || [ -f "$SHARED_KEY" ]; then
  if [ -f "$SHARED_KEY" ]; then
    echo "  [skip] .gate/signing.key — using shared key ($SHARED_KEY)"
  else
    echo "  [note] gates.json signing=shared but no shared key — run: scripts/setup-shared-gate.sh --org YOUR_ORG"
  fi
elif [ ! -f "$GATE_LOCAL/signing.key" ]; then
  python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$AGENT_DIR')
from gate.keys import generate_signing_secret
generate_signing_secret(Path('$GATE_LOCAL/signing.key'))
print('  [installed] .gate/signing.key (HS256, per-repo)')
"
else
  echo "  [skip] .gate/signing.key (already exists)"
fi

# GitHub Actions workflow
WF_DIR="$PROJECT_ROOT/.github/workflows"
mkdir -p "$WF_DIR"
WF_FILE="$WF_DIR/agent-toolkit-gate.yml"
if [ ! -f "$WF_FILE" ]; then
  cp "$TOOLKIT_DIR/templates/github/workflows/agent-toolkit-gate.yml" "$WF_FILE"
  echo "  [installed] .github/workflows/agent-toolkit-gate.yml"
else
  echo "  [skip] .github/workflows/agent-toolkit-gate.yml (already exists)"
fi

# .gitignore entries
GITIGNORE="$PROJECT_ROOT/.gitignore"
append_ignore() {
  local line="$1"
  if [ -f "$GITIGNORE" ] && grep -qxF "$line" "$GITIGNORE" 2>/dev/null; then
    return
  fi
  echo "$line" >> "$GITIGNORE"
  echo "  [installed] .gitignore + $line"
}

if [ ! -f "$GITIGNORE" ]; then
  touch "$GITIGNORE"
fi
append_ignore ".gate/signing.key"
append_ignore ".gate/private.pem"
append_ignore ".gate/gate-token.jwt"
append_ignore ".gate/attestation.json"
append_ignore ".gates/"

# Upload signing secret to GitHub (per-repo key only; shared uses setup-shared-gate.sh once)
if [ "$USE_SHARED" = "shared" ] && [ -f "$SHARED_KEY" ]; then
  echo "  [skip] GitHub secret — use org/repo secret from setup-shared-gate.sh (one time for all apps)"
elif command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && [ -f "$GATE_LOCAL/signing.key" ]; then
  if gh secret set AGENT_TOOLKIT_GATE_SECRET < "$GATE_LOCAL/signing.key" 2>/dev/null; then
    echo "  [installed] GitHub secret AGENT_TOOLKIT_GATE_SECRET (this repo only)"
  else
    echo "  [warn] could not set GitHub secret — add manually or use setup-shared-gate.sh"
  fi
else
  echo "  [note] For all apps at once: scripts/setup-shared-gate.sh --org YOUR_ORG"
fi

echo "  Signed gates ready. CI will issue gate-token.jwt on push/PR."
echo "  Enable branch protection: require status check 'agent-toolkit-gate'."
