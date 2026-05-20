#!/bin/bash
# setup-shared-gate.sh — ONE-TIME setup: one signing key for all your app repos.
#
# Creates ~/.config/agent-toolkit/gate/signing.key and uploads the same secret
# to GitHub (organization-wide or a list of repos). Use with gates.json:
#   "signing": "shared"
#
# Usage:
#   ./scripts/setup-shared-gate.sh --org my-github-org
#   ./scripts/setup-shared-gate.sh --repos owner/app1,owner/app2,owner/app3
#   ./scripts/setup-shared-gate.sh --org my-org --bootstrap ~/dev   # also install gates in each git repo under ~/dev

set -e

TOOLKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SHARED_DIR="$HOME/.config/agent-toolkit/gate"
SHARED_KEY="$SHARED_DIR/signing.key"
ORG=""
REPOS=""
BOOTSTRAP_DIR=""

usage() {
  echo "Usage: $0 --org ORG_NAME | --repos owner/r1,owner/r2 [--bootstrap DIR]"
  echo ""
  echo "  --org NAME       Set GitHub org secret (visible to all repos in org) — best for 5+ apps"
  echo "  --repos LIST     Set same secret on each repo (comma-separated)"
  echo "  --bootstrap DIR  Run install/bootstrap on every git repo under DIR (optional)"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG="$2"; shift 2 ;;
    --repos) REPOS="$2"; shift 2 ;;
    --bootstrap) BOOTSTRAP_DIR="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [ -z "$ORG" ] && [ -z "$REPOS" ]; then
  echo "Error: provide --org or --repos (or both)"
  usage
fi

mkdir -p "$SHARED_DIR"
if [ ! -f "$SHARED_KEY" ]; then
  python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '$TOOLKIT_DIR')
from gate.keys import generate_signing_secret, USER_SIGNING_KEY, USER_SIGNING_META
generate_signing_secret(USER_SIGNING_KEY, USER_SIGNING_META)
print('Created shared signing key')
"
  echo "  [created] $SHARED_KEY"
else
  echo "  [skip] $SHARED_KEY (already exists)"
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "  [warn] gh CLI not found — install GitHub CLI and run:"
  echo "         gh secret set AGENT_TOOLKIT_GATE_SECRET < $SHARED_KEY"
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "  [warn] gh not logged in — run: gh auth login"
  exit 0
fi

if [ -n "$ORG" ]; then
  if gh secret set AGENT_TOOLKIT_GATE_SECRET --org "$ORG" --visibility all < "$SHARED_KEY"; then
    echo "  [installed] org secret AGENT_TOOLKIT_GATE_SECRET on $ORG (all repos)"
  else
    echo "  [warn] could not set org secret — need org admin, or use --repos"
  fi
fi

if [ -n "$REPOS" ]; then
  IFS=',' read -ra REPO_LIST <<< "$REPOS"
  for repo in "${REPO_LIST[@]}"; do
    repo="$(echo "$repo" | xargs)"
    [ -z "$repo" ] && continue
    if gh secret set AGENT_TOOLKIT_GATE_SECRET -R "$repo" < "$SHARED_KEY"; then
      echo "  [installed] repo secret on $repo"
    else
      echo "  [warn] failed on $repo"
    fi
  done
fi

# Ensure each project uses shared signing in gates.json
patch_gates_json() {
  local root="$1"
  local gates="$root/gates.json"
  if [ ! -f "$gates" ]; then
    cp "$TOOLKIT_DIR/templates/gates.json" "$gates"
  fi
  if command -v jq >/dev/null 2>&1; then
    tmp="$(mktemp)"
    jq '.signing = "shared"' "$gates" > "$tmp" && mv "$tmp" "$gates"
    echo "  [installed] $gates signing=shared"
  elif ! grep -q '"signing"' "$gates" 2>/dev/null; then
    # minimal patch without jq
    sed -i.bak 's/"gate_mode"/"signing": "shared",\n  "gate_mode"/' "$gates" 2>/dev/null || true
    rm -f "$gates.bak"
  fi
}

if [ -n "$BOOTSTRAP_DIR" ] && [ -d "$BOOTSTRAP_DIR" ]; then
  echo ""
  echo "Bootstrapping git repos under $BOOTSTRAP_DIR ..."
  find "$BOOTSTRAP_DIR" -maxdepth 3 -type d -name .git 2>/dev/null | while read -r gitdir; do
    proj="$(dirname "$gitdir")"
    bash "$TOOLKIT_DIR/scripts/bootstrap-project-gates.sh" "$TOOLKIT_DIR" "$proj" || true
    patch_gates_json "$proj"
  done
fi

cat > "$SHARED_DIR/README.txt" << EOF
Shared gate signing key for all projects with gates.json "signing": "shared".
GitHub: org secret AGENT_TOOLKIT_GATE_SECRET (same value as this file).
Do not commit this directory.
EOF

echo ""
echo "Done. In each app repo, set gates.json: \"signing\": \"shared\" (or re-run install after template update)."
echo "Local issue_token / attest will use: $SHARED_KEY"
echo "CI uses GitHub secret AGENT_TOOLKIT_GATE_SECRET (no per-repo key file needed)."
