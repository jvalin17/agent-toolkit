#!/bin/bash
# set-gate-mode.sh — Switch gates.json between legacy and signed (human or agent).
#
# Usage:
#   scripts/set-gate-mode.sh legacy              # back to default (block, minimal)
#   scripts/set-gate-mode.sh signed              # full signed setup (calls setup-signed-gates.sh)
#   scripts/set-gate-mode.sh status              # print current mode
#
# Safe for agents: non-interactive, prints what changed. Human should review gates.json.

set -e

TOOLKIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-}"
shift || true

usage() {
  cat <<EOF
Usage:
  $0 status
  $0 legacy [project-root]
  $0 signed [--upload-github-secret] [--profile NAME] [project-root]

Examples (you or your agent can run these from the project repo):
  $0 status
  $0 legacy
  $0 signed
  $0 signed --upload-github-secret

After switching, review gates.json. Signed mode needs attest + issue_token before git push.
EOF
  exit 0
}

PROJECT_ROOT=""
EXTRA_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --upload-github-secret|--warn|--profile)
      EXTRA_ARGS+=("$1")
      if [ "$1" = "--profile" ]; then
        EXTRA_ARGS+=("${2:?}")
        shift
      fi
      shift
      ;;
    *)
      PROJECT_ROOT="$1"
      shift
      ;;
  esac
done

if [ -z "$PROJECT_ROOT" ]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
  else
    echo "Error: pass project path or run inside a git repo." >&2
    exit 1
  fi
fi
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
GATES_FILE="$PROJECT_ROOT/gates.json"

show_status() {
  if [ ! -f "$GATES_FILE" ]; then
    echo "No gates.json in $PROJECT_ROOT (run ./install.sh first)."
    exit 0
  fi
  if command -v jq >/dev/null 2>&1; then
    echo "gates.json in $PROJECT_ROOT:"
    jq '{gate_mode, enforcement, profile, eval_threshold}' "$GATES_FILE"
  else
    cat "$GATES_FILE"
  fi
  if [ -f "$PROJECT_ROOT/.gate/gate-token.jwt" ]; then
    echo "Token file: .gate/gate-token.jwt (present)"
  fi
  if [ -d "$PROJECT_ROOT/.gates" ]; then
    echo "Legacy flags: $(ls "$PROJECT_ROOT/.gates" 2>/dev/null | tr '\n' ' ')"
  fi
}

apply_legacy() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq required. Or edit gates.json manually: gate_mode=legacy" >&2
    exit 1
  fi
  if [ ! -f "$GATES_FILE" ]; then
    cp "$TOOLKIT_DIR/templates/gates.json" "$GATES_FILE"
  fi
  TMP="$(mktemp)"
  jq '.gate_mode = "legacy" | .enforcement = "block" | .profile = "minimal"' \
    "$GATES_FILE" > "$TMP" && mv "$TMP" "$GATES_FILE"
  echo "Set gate_mode=legacy, enforcement=block, profile=minimal"
  echo "Hooks use .gates/*-passed files written by hooks/finalize_report.py."
  echo "JWT files are ignored until you switch back to signed."
  show_status
}

case "$MODE" in
  status|'')
    [ -z "$MODE" ] && usage
    show_status
    ;;
  legacy)
    apply_legacy
    ;;
  signed)
    exec bash "$TOOLKIT_DIR/scripts/setup-signed-gates.sh" "${EXTRA_ARGS[@]}" "$PROJECT_ROOT"
    ;;
  *)
    echo "Unknown mode: $MODE (use legacy, signed, or status)" >&2
    usage
    ;;
esac
