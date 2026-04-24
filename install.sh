#!/bin/bash
# install.sh — Symlink agent-toolkit commands to ~/.claude/commands/ for global access

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMANDS_SRC="$SCRIPT_DIR/commands"
COMMANDS_DEST="$HOME/.claude/commands"

# Create destination if it doesn't exist
mkdir -p "$COMMANDS_DEST"

echo "Installing agent-toolkit commands..."
echo "  Source: $COMMANDS_SRC"
echo "  Destination: $COMMANDS_DEST"
echo ""

# Track what we do
installed=0
skipped=0

for cmd_file in "$COMMANDS_SRC"/*.md; do
    [ -f "$cmd_file" ] || continue

    filename="$(basename "$cmd_file")"
    dest_path="$COMMANDS_DEST/$filename"

    # Check if destination already exists
    if [ -L "$dest_path" ]; then
        # It's a symlink — check if it points to us
        current_target="$(readlink "$dest_path")"
        if [ "$current_target" = "$cmd_file" ]; then
            echo "  [skip] $filename (already linked)"
            skipped=$((skipped + 1))
            continue
        else
            echo "  [warn] $filename exists, points to $current_target"
            echo "         Overwrite with agent-toolkit version? (y/n)"
            read -r answer
            if [ "$answer" != "y" ]; then
                echo "  [skip] $filename (kept existing)"
                skipped=$((skipped + 1))
                continue
            fi
            rm "$dest_path"
        fi
    elif [ -f "$dest_path" ]; then
        echo "  [warn] $filename exists as a regular file (not a symlink)"
        echo "         Back up to ${filename}.bak and replace? (y/n)"
        read -r answer
        if [ "$answer" != "y" ]; then
            echo "  [skip] $filename (kept existing)"
            skipped=$((skipped + 1))
            continue
        fi
        mv "$dest_path" "${dest_path}.bak"
        echo "  [backup] $filename → ${filename}.bak"
    fi

    ln -s "$cmd_file" "$dest_path"
    echo "  [installed] $filename"
    installed=$((installed + 1))
done

echo ""
echo "Done. Installed: $installed, Skipped: $skipped"
echo ""
echo "Commands are now available as slash commands in Claude Code:"
for cmd_file in "$COMMANDS_SRC"/*.md; do
    [ -f "$cmd_file" ] || continue
    filename="$(basename "$cmd_file" .md)"
    echo "  /$filename"
done
