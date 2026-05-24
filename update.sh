#!/usr/bin/env bash
# update.sh — Pull latest and sync install state (skills, hooks, project gates)
# Called automatically:
#   - SessionStart (session_init.py) when a session loads
#   - PreToolUse on Skill before every skill invocation
#
# Runs git pull (default on) then install.sh --sync-only.
# Disable pull: AGENT_TOOLKIT_AUTO_PULL=0

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Auto-pull latest toolkit (default on; set AGENT_TOOLKIT_AUTO_PULL=0 to disable)
if [ "${AGENT_TOOLKIT_AUTO_PULL:-1}" != "0" ] && \
   [ "${AGENT_TOOLKIT_AUTO_PULL:-1}" != "false" ] && \
   [ "${AGENT_TOOLKIT_AUTO_PULL:-1}" != "no" ]; then
    git -C "$SCRIPT_DIR" pull --ff-only 2>/dev/null || true
fi

# Full idempotent sync (symlinks + hooks + bootstrap + bin entrypoints)
bash "$SCRIPT_DIR/install.sh" --sync-only >/dev/null 2>&1 || true
