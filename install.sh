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
OLD_COMMANDS_SRC="$SCRIPT_DIR/commands"

SKILLS_DEST="$HOME/.claude/skills"
AGENTS_DEST="$HOME/.claude/agents"
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

# --- Install auto-update hook ---
echo ""
echo "Setting up auto-update hook..."

SETTINGS_FILE="$HOME/.claude/settings.json"

install_hook() {
    local toolkit_path="$SCRIPT_DIR"
    local hook_command="git -C $toolkit_path pull --ff-only 2>/dev/null || true"

    if [ ! -f "$SETTINGS_FILE" ]; then
        # Create settings file with just the hook
        cat > "$SETTINGS_FILE" << HOOKEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "$hook_command",
            "timeout": 10,
            "statusMessage": "Checking for toolkit updates..."
          }
        ]
      }
    ]
  }
}
HOOKEOF
        echo "  [installed] auto-update hook (created $SETTINGS_FILE)"
        return
    fi

    # Check if hook already exists
    if jq -e '.hooks.PreToolUse[]? | select(.matcher == "Skill") | .hooks[]? | select(.command | contains("agent-toolkit"))' "$SETTINGS_FILE" > /dev/null 2>&1; then
        # Update the path in case toolkit moved
        local tmp_file=$(mktemp)
        jq --arg cmd "$hook_command" '
            .hooks.PreToolUse = [.hooks.PreToolUse[]? | if .matcher == "Skill" then .hooks = [.hooks[]? | if (.command | contains("agent-toolkit")) then .command = $cmd else . end] else . end]
        ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
        echo "  [updated] auto-update hook (path refreshed)"
        return
    fi

    # Add hook to existing settings, merging with existing hooks
    local tmp_file=$(mktemp)
    jq --arg cmd "$hook_command" '
        .hooks //= {} |
        .hooks.PreToolUse //= [] |
        .hooks.PreToolUse += [
            {
                "matcher": "Skill",
                "hooks": [
                    {
                        "type": "command",
                        "command": $cmd,
                        "timeout": 10,
                        "statusMessage": "Checking for toolkit updates..."
                    }
                ]
            }
        ]
    ' "$SETTINGS_FILE" > "$tmp_file" && mv "$tmp_file" "$SETTINGS_FILE"
    echo "  [installed] auto-update hook"
}

# Only install if jq is available (needed for safe JSON merging)
if command -v jq &> /dev/null; then
    install_hook
else
    echo "  [skip] auto-update hook (jq not installed — install jq for auto-updates)"
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
