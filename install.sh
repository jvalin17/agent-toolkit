#!/bin/bash
# install.sh — Install agent-toolkit skills and agents into ~/.claude/ for global access
#
# Skills go to:  ~/.claude/skills/
# Agents go to:  ~/.claude/agents/
# Old commands:  ~/.claude/commands/ (cleaned up if migrated)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
AGENTS_SRC="$SCRIPT_DIR/agents"
SHARED_SRC="$SCRIPT_DIR/shared"
OLD_COMMANDS_SRC="$SCRIPT_DIR/commands"

SKILLS_DEST="$HOME/.claude/skills"
AGENTS_DEST="$HOME/.claude/agents"
SHARED_DEST="$HOME/.claude/shared"
OLD_COMMANDS_DEST="$HOME/.claude/commands"

installed=0
skipped=0
cleaned=0

# --- Helper ---
link_item() {
    local src="$1"
    local dest="$2"
    local name="$3"
    local type="$4"  # "file" or "dir"

    if [ "$type" = "dir" ]; then
        if [ -L "$dest" ]; then
            current="$(readlink "$dest")"
            if [ "$current" = "$src" ]; then
                echo "  [skip] $name (already linked)"
                skipped=$((skipped + 1))
                return
            fi
            rm "$dest"
        elif [ -d "$dest" ]; then
            echo "  [warn] $name exists as directory. Replace with symlink? (y/n)"
            read -r answer
            [ "$answer" != "y" ] && { skipped=$((skipped + 1)); return; }
            rm -rf "$dest"
        fi
        ln -s "$src" "$dest"
    else
        if [ -L "$dest" ]; then
            current="$(readlink "$dest")"
            if [ "$current" = "$src" ]; then
                echo "  [skip] $name (already linked)"
                skipped=$((skipped + 1))
                return
            fi
            rm "$dest"
        elif [ -f "$dest" ]; then
            echo "  [warn] $name exists as file. Replace? (y/n)"
            read -r answer
            [ "$answer" != "y" ] && { skipped=$((skipped + 1)); return; }
            mv "$dest" "${dest}.bak"
        fi
        ln -s "$src" "$dest"
    fi
    echo "  [installed] $name"
    installed=$((installed + 1))
}

# --- Install Skills ---
echo "Installing skills..."
mkdir -p "$SKILLS_DEST"

for skill_dir in "$SKILLS_SRC"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_name="$(basename "$skill_dir")"
    link_item "$skill_dir" "$SKILLS_DEST/$skill_name" "$skill_name" "dir"
done

# --- Install Agents ---
echo ""
echo "Installing agents..."
mkdir -p "$AGENTS_DEST"

for agent_file in "$AGENTS_SRC"/*.md; do
    [ -f "$agent_file" ] || continue
    filename="$(basename "$agent_file")"
    link_item "$agent_file" "$AGENTS_DEST/$filename" "$filename" "file"
done

# --- Install Shared Files ---
echo ""
echo "Installing shared files..."
mkdir -p "$SHARED_DEST"

for shared_file in "$SHARED_SRC"/*.md; do
    [ -f "$shared_file" ] || continue
    filename="$(basename "$shared_file")"
    link_item "$shared_file" "$SHARED_DEST/$filename" "$filename" "file"
done

# --- Clean up old commands that migrated to skills ---
echo ""
echo "Checking for old commands to clean up..."

if [ -L "$OLD_COMMANDS_DEST/requirements.md" ]; then
    old_target="$(readlink "$OLD_COMMANDS_DEST/requirements.md")"
    if echo "$old_target" | grep -q "agent-toolkit"; then
        rm "$OLD_COMMANDS_DEST/requirements.md"
        echo "  [cleaned] commands/requirements.md (migrated to skill)"
        cleaned=$((cleaned + 1))
    fi
fi

# --- Install hooks ---
echo ""
echo "Setting up hooks..."

SETTINGS_FILE="$HOME/.claude/settings.json"
HOOKS_SRC="$SCRIPT_DIR/hooks"

install_hooks() {
    local toolkit_path="$SCRIPT_DIR"
    local update_command="$toolkit_path/update.sh 2>/dev/null || true"
    local gate_cmd="$toolkit_path/hooks/gate.sh"
    local skill_passed_cmd="$toolkit_path/hooks/skill-passed.sh"
    local gate_cleanup_cmd="$toolkit_path/hooks/gate-cleanup.sh"

    if [ ! -f "$SETTINGS_FILE" ]; then
        cat > "$SETTINGS_FILE" << HOOKEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$update_command",
            "timeout": 10,
            "statusMessage": "Checking for toolkit updates..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$gate_cmd",
            "timeout": 5,
            "statusMessage": "Checking quality gates..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$skill_passed_cmd",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$gate_cleanup_cmd",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
HOOKEOF
        echo "  [installed] all hooks (created $SETTINGS_FILE)"
        return
    fi

    # Merge hooks into existing settings — remove old hooks, add new ones
    local tmp_file=$(mktemp)

    # Remove old single-skill hooks if present
    jq '
        .hooks.PreToolUse = [(.hooks.PreToolUse // [])[] | select(.hooks | all(.command | (contains("precommit-gate") | not)))] |
        .hooks.PostToolUse = [(.hooks.PostToolUse // [])[] | select(.hooks | all(.command | ((contains("precommit-passed") | not) and (contains("post-commit-cleanup") | not))))]
    ' "$SETTINGS_FILE" > "$tmp_file" 2>/dev/null && mv "$tmp_file" "$SETTINGS_FILE"

    # Add/update auto-update hook
    if jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("update.sh"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$update_command" '
            .hooks.PreToolUse = [.hooks.PreToolUse[]? | if (.hooks[]? | .command | contains("update.sh")) then .hooks = [.hooks[]? | if (.command | contains("update.sh")) then .command = $cmd else . end] else . end]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [updated] auto-update hook"
    else
        jq --arg cmd "$update_command" '
            .hooks //= {} | .hooks.PreToolUse //= [] |
            .hooks.PreToolUse += [{"matcher": "Skill", "hooks": [{"type": "command", "command": $cmd, "timeout": 10, "statusMessage": "Checking for toolkit updates..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] auto-update hook"
    fi

    # Add gate hook (replaces old precommit-gate)
    if ! jq -e '.hooks.PreToolUse[]? | select(.hooks[]? | .command | contains("gate.sh"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$gate_cmd" '
            .hooks.PreToolUse += [{"matcher": "Bash", "hooks": [{"type": "command", "command": $cmd, "timeout": 5, "statusMessage": "Checking quality gates..."}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] quality gate hook (blocks commit/push without required skills)"
    else
        echo "  [skip] quality gate hook (already installed)"
    fi

    # Add skill-passed hook (replaces old precommit-passed)
    if ! jq -e '.hooks.PostToolUse[]? | select(.hooks[]? | .command | contains("skill-passed.sh"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$skill_passed_cmd" '
            .hooks //= {} | .hooks.PostToolUse //= [] |
            .hooks.PostToolUse += [{"matcher": "Skill", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] skill-passed hook (tracks which skills have run)"
    else
        echo "  [skip] skill-passed hook (already installed)"
    fi

    # Add gate-cleanup hook (replaces old post-commit-cleanup)
    if ! jq -e '.hooks.PostToolUse[]? | select(.hooks[]? | .command | contains("gate-cleanup.sh"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        jq --arg cmd "$gate_cleanup_cmd" '
            .hooks.PostToolUse += [{"matcher": "Bash", "hooks": [{"type": "command", "command": $cmd, "timeout": 5}]}]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [installed] gate-cleanup hook (resets gates after commit)"
    else
        echo "  [skip] gate-cleanup hook (already installed)"
    fi
}

# Only install if jq is available (needed for safe JSON merging)
if command -v jq &> /dev/null; then
    install_hooks
else
    echo "  [skip] hooks (jq not installed — install jq for hook enforcement)"
fi

# --- Summary ---
echo ""
echo "Done. Installed: $installed, Skipped: $skipped, Cleaned: $cleaned"
echo ""
echo "Skills available as slash commands:"
for skill_dir in "$SKILLS_SRC"/*/; do
    [ -d "$skill_dir" ] || continue
    echo "  /$(basename "$skill_dir")"
done
echo ""
echo "Sub-agents available for skills to spawn:"
for agent_file in "$AGENTS_SRC"/*.md; do
    [ -f "$agent_file" ] || continue
    echo "  $(basename "$agent_file" .md)"
done
