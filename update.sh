#!/usr/bin/env bash
# update.sh — Pull latest and sync install state (skills, hooks, project gates)
# Called automatically:
#   - SessionStart (session_init.py) when a session loads
#   - PreToolUse on Skill before every skill invocation
#
# Runs install.sh --sync-only. Pulling from the network is OPT-IN:
#   AGENT_TOOLKIT_AUTO_PULL=1   also git pull --ff-only first (prints what changed)
# Default is no pull: a push to the upstream repo must not become code that
# runs as hooks on every machine at the next session without anyone looking.
#
# Exit 0 on success; exit 1 if pull or sync fails after retries.
# Callers that must not block the session should handle non-zero exit explicitly.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAX_RETRIES=2
RETRY_DELAY_SEC=2

PULL_OK=1
SYNC_OK=1

_log() {
  echo "update.sh: $*" >&2
}

_retry() {
  local label="$1"
  shift
  local attempt=1
  local output=""
  while [ "$attempt" -le "$MAX_RETRIES" ]; do
    if output="$("$@" 2>&1)"; then
      if [ -n "$output" ]; then
        _log "$label ok (attempt $attempt): $output"
      fi
      return 0
    fi
    _log "$label failed (attempt $attempt/$MAX_RETRIES): ${output:-unknown error}"
    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
      sleep "$RETRY_DELAY_SEC"
    fi
    attempt=$((attempt + 1))
  done
  _log "$label gave up after $MAX_RETRIES attempts"
  return 1
}

SYNC_VERBOSE="${AGENT_TOOLKIT_SYNC_VERBOSE:-}"

# Auto-pull latest toolkit — opt-in only (supply-chain: see header)
case "${AGENT_TOOLKIT_AUTO_PULL:-}" in
  1|true|yes)
    BEFORE="$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
    if _retry "git pull" git -C "$SCRIPT_DIR" pull --ff-only; then
      AFTER="$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
      if [ "$BEFORE" != "$AFTER" ]; then
        _log "toolkit updated $BEFORE -> $AFTER; changes:"
        git -C "$SCRIPT_DIR" log --oneline "$BEFORE..$AFTER" 2>/dev/null >&2 || true
      fi
    else
      PULL_OK=0
    fi
    ;;
  *)
    _log "skipping git pull (set AGENT_TOOLKIT_AUTO_PULL=1 to pull on session start, or run: git -C $SCRIPT_DIR pull)"
    ;;
esac

# Full idempotent sync (symlinks + hooks + bootstrap + bin entrypoints)
if [ "$SYNC_VERBOSE" = "1" ]; then
  if ! _retry "install sync" bash "$SCRIPT_DIR/install.sh" --sync-only; then
    SYNC_OK=0
  fi
else
  if ! _retry "install sync" bash "$SCRIPT_DIR/install.sh" --sync-only >/dev/null; then
    SYNC_OK=0
  fi
fi

if [ "$PULL_OK" -eq 0 ] || [ "$SYNC_OK" -eq 0 ]; then
  _log "update incomplete (pull_ok=$PULL_OK sync_ok=$SYNC_OK)"
  exit 1
fi

exit 0
