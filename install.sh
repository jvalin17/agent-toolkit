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
