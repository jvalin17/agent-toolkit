#!/bin/bash
# Hook: Block writes outside the current working directory
# Triggered by PreToolUse on Write tool
# Part of agent-toolkit doc-guard feature (installed by default via install.sh)
#
# Policy: the agent should only write files within the project it's working on.
# Writes to ~/.claude/ (toolkit, memory, settings) are also allowed.
# Everything else requires user confirmation.

FILE_PATH=$(jq -r '.tool_input.file_path // empty')

# Nothing to check if no path provided
[ -z "$FILE_PATH" ] && exit 0

# Resolve to absolute paths for reliable comparison
# Only resolve if parent directory exists; otherwise use raw path
PARENT_DIR=$(dirname "$FILE_PATH" 2>/dev/null)
if [ -d "$PARENT_DIR" ]; then
    RESOLVED=$(cd "$PARENT_DIR" && pwd)/$(basename "$FILE_PATH")
else
    RESOLVED="$FILE_PATH"
fi

CWD=$(pwd)

# Allow: files within current working directory
echo "$RESOLVED" | grep -q "^$CWD/" && exit 0

# Allow: ~/.claude/ internal files (memory, plans, settings, hooks)
echo "$RESOLVED" | grep -q "^$HOME/.claude/" && exit 0

# Block: anything outside the project directory
echo "{\"decision\":\"block\",\"reason\":\"Write outside project directory: $FILE_PATH -- The agent is trying to write outside the current project ($CWD). Please confirm this is intended.\"}"
