#!/bin/bash
# bootstrap-project-gates.sh — Gate layout for the current git project (legacy default).
# Called automatically from install.sh. Idempotent. No GitHub secret required.

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
echo "Configuring project gates in: $PROJECT_ROOT"

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
  "gate_mode": "legacy",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
echo "  [installed] .agent-toolkit/config.json"

# gates.json
if [ ! -f "$PROJECT_ROOT/gates.json" ]; then
  cp "$TOOLKIT_DIR/templates/gates.json" "$PROJECT_ROOT/gates.json"
  echo "  [installed] gates.json (from template: legacy, block, minimal — set gate_mode signed if needed)"
else
  # Add new top-level keys from template without overwriting user values
  if command -v jq >/dev/null 2>&1; then
    tmp_gates="$(mktemp)"
    if jq -s '
      .[0] as $cur | .[1] as $tpl |
      $cur + ($tpl | del(.profiles) | with_entries(select(.key as $k | ($cur | has($k) | not))))
    ' "$PROJECT_ROOT/gates.json" "$TOOLKIT_DIR/templates/gates.json" > "$tmp_gates" 2>/dev/null; then
      mv "$tmp_gates" "$PROJECT_ROOT/gates.json"
      echo "  [merged] gates.json (added missing keys from template)"
    else
      rm -f "$tmp_gates"
      echo "  [skip] gates.json (already exists)"
    fi
  else
    echo "  [skip] gates.json (already exists)"
  fi
fi

# Signing keys (gitignored)
GATE_LOCAL="$PROJECT_ROOT/.gate"
mkdir -p "$GATE_LOCAL"
if [ ! -f "$GATE_LOCAL/signing.key" ]; then
  (cd "$PROJECT_ROOT" && python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$AGENT_DIR')
from gate.keys import generate_signing_secret
gate = Path('.gate')
generate_signing_secret(gate / 'signing.key', gate / 'signing.meta.json')
print('  [installed] .gate/signing.key (HS256, stdlib only)')
")
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
append_ignore ".scratch/"

# Optional: upload signing key to GitHub (only when explicitly requested)
if [ "${AGENT_TOOLKIT_UPLOAD_GATE_SECRET:-}" = "1" ]; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh secret set AGENT_TOOLKIT_GATE_SECRET < "$GATE_LOCAL/signing.key" 2>/dev/null; then
      echo "  [optional] GitHub secret AGENT_TOOLKIT_GATE_SECRET set"
    else
      echo "  [optional] could not set GitHub secret — paste .gate/signing.key manually if needed"
    fi
  else
    echo "  [optional] gh not available — skip AGENT_TOOLKIT_GATE_SECRET upload"
  fi
fi

echo "  Gate layout ready (default: legacy + block). Signed mode and GitHub secret are optional."
